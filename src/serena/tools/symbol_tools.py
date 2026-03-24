"""
Language server-related tools
"""

import dataclasses
import json
import os
from collections.abc import Sequence
from copy import copy
from typing import Any, Literal

from serena.text_utils import extract_usage_pattern
from serena.tools import (
    SUCCESS_RESULT,
    Tool,
    ToolMarkerSymbolicEdit,
    ToolMarkerSymbolicRead,
)
from serena.tools.tools_base import ToolMarkerOptional
from serena.util.complexity_analyzer import ComplexityAnalyzer
from serena.util.symbol_cache import get_global_cache
from solidlsp.ls_types import SymbolKind


def _sanitize_symbol_dict(symbol_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize a symbol dictionary inplace by removing unnecessary information.
    """
    # We replace the location entry, which repeats line information already included in body_location
    # and has unnecessary information on column, by just the relative path.
    symbol_dict = copy(symbol_dict)
    s_relative_path = symbol_dict.get("location", {}).get("relative_path")
    if s_relative_path is not None:
        symbol_dict["relative_path"] = s_relative_path
    symbol_dict.pop("location", None)
    # also remove name, name_path should be enough
    symbol_dict.pop("name")
    return symbol_dict


def _optimize_symbol_list(symbol_dicts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Optimize a list of symbol dictionaries by factoring out repeated values.
    
    Returns a structured dictionary with:
    - _schema: version marker
    - file or files: the file path(s) (factored out if all symbols are from same file)
    - symbols: list of symbols with redundant fields removed
    """
    if not symbol_dicts:
        return {"_schema": "structured_v1", "symbols": []}
    
    # Check if all symbols have the same relative_path
    relative_paths = {s.get("relative_path") for s in symbol_dicts if "relative_path" in s}
    
    if len(relative_paths) == 1:
        # Single file - factor out the path
        common_path = relative_paths.pop()
        optimized_symbols = []
        for s in symbol_dicts:
            optimized = {k: v for k, v in s.items() if k != "relative_path" and v is not None}
            optimized_symbols.append(optimized)
        
        return {
            "_schema": "structured_v1",
            "file": common_path,
            "symbols": optimized_symbols
        }
    else:
        # Multiple files - keep relative_path but remove null values
        optimized_symbols = []
        for s in symbol_dicts:
            optimized = {k: v for k, v in s.items() if v is not None}
            optimized_symbols.append(optimized)
        
        return {
            "_schema": "structured_v1", 
            "symbols": optimized_symbols
        }


def _generate_unified_diff(
    old_content: str,
    new_content: str,
    filepath: str,
    context_lines: int = 3
) -> str:
    """
    Generate a unified diff between old and new content.

    :param old_content: The original file content
    :param new_content: The modified file content
    :param filepath: The file path for the diff header
    :param context_lines: Number of context lines to show (default: 3)
    :return: Unified diff string
    """
    import difflib

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
        n=context_lines
    )

    return "".join(diff)


def _generate_symbol_id(symbol_dict: dict[str, Any]) -> str:
    """
    Generate a stable symbol ID for retrieval.

    Format: {name_path}:{relative_path}:{line_number}
    Example: "User/login:models.py:142"

    :param symbol_dict: Symbol dictionary with name_path, relative_path, and body_location
    :return: Symbol ID string
    """
    name_path = symbol_dict.get("name_path", "")
    relative_path = symbol_dict.get("relative_path", "")

    # Get line number from body_location
    body_location = symbol_dict.get("body_location", {})
    line = body_location.get("start_line") if isinstance(body_location, dict) else None

    if not line:
        # Fallback: try to get from location if body_location not available
        location = symbol_dict.get("location", {})
        line = location.get("line") if isinstance(location, dict) else None

    if name_path and relative_path and line:
        return f"{name_path}:{relative_path}:{line}"
    return ""


def _add_symbol_ids(symbol_dicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add symbol_id field to each symbol dictionary.

    :param symbol_dicts: List of symbol dictionaries
    :return: Modified list with symbol_id added to each dict
    """
    for s_dict in symbol_dicts:
        symbol_id = _generate_symbol_id(s_dict)
        if symbol_id:
            s_dict["symbol_id"] = symbol_id
    return symbol_dicts


class RestartLanguageServerTool(Tool, ToolMarkerOptional):
    """Restarts the language server, may be necessary when edits not through Serena happen."""

    def apply(self) -> str:
        """Use this tool only on explicit user request or after confirmation.
        It may be necessary to restart the language server if it hangs.
        """
        self.agent.reset_language_server()
        return SUCCESS_RESULT


class GetSymbolsOverviewTool(Tool, ToolMarkerSymbolicRead):
    """
    Gets an overview of the top-level symbols defined in a given file.
    """

    def apply(self, relative_path: str, depth: int = 0, max_results: int = -1, page_cursor: str | None = None, max_answer_chars: int = -1) -> str:
        """
        High-level overview of code symbols in a file. Call first when exploring a new file.

        :param relative_path: Relative path to the file.
        :param depth: Descendant depth (e.g. 1 for class methods). Default 0.
        :param max_results: -1=config default, 0=unlimited. Paginate via page_cursor.
        :param page_cursor: From previous _pagination.next_cursor.
        :param max_answer_chars: Char limit. -1=config default.
        :return: JSON with top-level symbols in the file.
        """
        # Use cache for symbol overview
        cache = get_global_cache(self.project.project_root)
        query_params = {"tool": "get_symbols_overview", "depth": depth}

        # Try cache first
        cache_hit, cached_data, cache_metadata = cache.get(relative_path, query_params)
        if cache_hit:
            # Return cached result with metadata
            result = json.loads(cached_data)
            result["_cache"] = cache_metadata
            return self._limit_length(json.dumps(result), max_answer_chars)

        # Cache miss - perform query
        symbol_retriever = self.create_language_server_symbol_retriever()
        file_path = os.path.join(self.project.project_root, relative_path)

        # The symbol overview is capable of working with both files and directories,
        # but we want to ensure that the user provides a file path.
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File or directory {relative_path} does not exist in the project.")
        if os.path.isdir(file_path):
            raise ValueError(f"Expected a file path, but got a directory path: {relative_path}. ")
        result = symbol_retriever.get_symbol_overview(relative_path, depth=depth)[relative_path]
        # Optimize: since all symbols are from the same file, use structured format
        symbol_list = [dataclasses.asdict(i) for i in result]

        # Apply result limiting / pagination
        symbol_list, pagination_meta = self._apply_result_limit(symbol_list, max_results, page_cursor)

        optimized_result = {
            "_schema": "structured_v1",
            "file": relative_path,
            "symbols": symbol_list
        }

        if pagination_meta:
            optimized_result["_pagination"] = pagination_meta

        # Cache the result
        cache_metadata = cache.put(relative_path, json.dumps(optimized_result), query_params)
        optimized_result["_cache"] = cache_metadata

        result_json_str = json.dumps(optimized_result)
        return self._limit_length(result_json_str, max_answer_chars)


class FindSymbolTool(Tool, ToolMarkerSymbolicRead):
    """
    Performs a global (or local) search for symbols with/containing a given name/substring (optionally filtered by type).
    """

    def apply(
        self,
        name_path: str,
        depth: int = 0,
        relative_path: str = "",
        include_body: bool | None = None,  # DEPRECATED - use output_format
        detail_level: Literal["full", "signature", "auto"] | None = None,  # DEPRECATED - use output_format
        output_format: Literal["metadata", "signature", "body"] = "metadata",
        include_kinds: list[int] = [],  # noqa: B006
        exclude_kinds: list[int] = [],  # noqa: B006
        substring_matching: bool | None = None,  # DEPRECATED - use match_mode
        match_mode: Literal["exact", "substring", "glob", "regex"] = "exact",
        exclude_generated: bool | None = None,  # DEPRECATED - use search_scope
        search_scope: Literal["all", "source", "custom"] = "source",
        max_results: int = -1,
        page_cursor: str | None = None,
        max_answer_chars: int = -1,
    ) -> str:
        """
        Finds symbols by name_path pattern within the file's symbol tree. Returns locations usable for edits/queries.
        Specify depth > 0 to retrieve children (e.g. methods of a class).

        name_path matching: "method" matches anywhere in tree; "class/method" requires ancestor;
        "/class/method" is absolute (must start at top-level). Trailing slashes ignored.
        name_path is NOT a filesystem path -- use relative_path to restrict to a file/directory.

        :param name_path: Pattern to match. Simple: "method"; relative: "class/method"; absolute: "/class/method".
        :param depth: Descendant depth (e.g. 1 for class methods).
        :param relative_path: Restrict to file/directory. Speeds up search.
        :param output_format: metadata (default, locations only) | signature (API + docstring) | body (full source).
        :param include_body: [DEPRECATED] Use output_format instead.
        :param detail_level: [DEPRECATED] Use output_format instead.
        :param include_kinds: LSP symbol kind ints to include (5=class, 6=method, 12=function, etc.).
        :param exclude_kinds: LSP symbol kind ints to exclude. Takes precedence over include_kinds.
        :param match_mode: exact (default) | substring | glob | regex -- applied to final name_path segment.
        :param substring_matching: [DEPRECATED] Use match_mode instead.
        :param search_scope: source (default, excludes generated/vendor) | all.
        :param exclude_generated: [DEPRECATED] Use search_scope instead.
        :param max_results: -1=config default, 0=unlimited. Paginate via page_cursor.
        :param page_cursor: From previous _pagination.next_cursor.
        :param max_answer_chars: Char limit for JSON result. -1=config default.
        :return: List of matching symbols with locations.
        """
        # Handle deprecated parameters and build deprecation warnings
        deprecation_warnings = []

        # Map deprecated parameters to new output_format
        effective_output_format = output_format

        if include_body is not None:
            # include_body takes precedence for backward compatibility
            effective_output_format = "body" if include_body else "metadata"
            deprecation_warnings.append({
                "parameter": "include_body",
                "value": include_body,
                "replacement": "output_format",
                "migration": f"Use output_format='body' instead of include_body=True" if include_body else "Use output_format='metadata' (default) instead of include_body=False",
                "removal_version": "2.0.0"
            })

        if detail_level is not None:
            # detail_level also takes precedence
            if detail_level == "signature":
                effective_output_format = "signature"
            elif detail_level == "full":
                effective_output_format = "body" if include_body else "metadata"
            elif detail_level == "auto":
                # Auto mode - for now, treat as metadata
                effective_output_format = "metadata"

            deprecation_warnings.append({
                "parameter": "detail_level",
                "value": detail_level,
                "replacement": "output_format",
                "migration": {
                    "full": "Use output_format='body' or output_format='metadata' (depending on whether you need the body)",
                    "signature": "Use output_format='signature'",
                    "auto": "Use output_format='metadata' (recommended default)"
                }.get(detail_level, "Use output_format parameter"),
                "removal_version": "2.0.0"
            })

        # Map deprecated substring_matching to new match_mode
        effective_match_mode = match_mode

        if substring_matching is not None:
            # substring_matching takes precedence for backward compatibility
            effective_match_mode = "substring" if substring_matching else "exact"
            deprecation_warnings.append({
                "parameter": "substring_matching",
                "value": substring_matching,
                "replacement": "match_mode",
                "migration": "Use match_mode='substring' instead of substring_matching=True" if substring_matching else "Use match_mode='exact' (default) instead of substring_matching=False",
                "removal_version": "2.0.0"
            })

        # Validate regex patterns early if regex mode is used
        if effective_match_mode == "regex":
            import re
            try:
                re.compile(name_path.split("/")[-1])  # Validate only the last segment
            except re.error as e:
                return json.dumps({
                    "error": "Invalid regex pattern",
                    "pattern": name_path.split("/")[-1],
                    "details": str(e),
                    "suggestion": "Use a valid regex pattern or switch to match_mode='glob' for simple wildcards"
                })

        # Map deprecated exclude_generated to new search_scope
        effective_search_scope = search_scope

        if exclude_generated is not None:
            # exclude_generated takes precedence for backward compatibility
            effective_search_scope = "source" if exclude_generated else "all"
            deprecation_warnings.append({
                "parameter": "exclude_generated",
                "value": exclude_generated,
                "replacement": "search_scope",
                "migration": f"Use search_scope='source' instead of exclude_generated=True" if exclude_generated else "Use search_scope='all' instead of exclude_generated=False (or omit for new default 'source')",
                "removal_version": "2.0.0"
            })

        # Only use cache for single-file queries (not directory/global searches)
        cache = get_global_cache(self.project.project_root)
        use_cache = relative_path and os.path.isfile(os.path.join(self.project.project_root, relative_path))

        if use_cache:
            # Build query params for cache key
            query_params = {
                "name_path": name_path,
                "depth": depth,
                "output_format": effective_output_format,
                "include_kinds": include_kinds,
                "exclude_kinds": exclude_kinds,
                "match_mode": effective_match_mode,
                "search_scope": effective_search_scope,
                "tool": "find_symbol"
            }

            # Try cache first
            cache_hit, cached_data, cache_metadata = cache.get(relative_path, query_params)
            if cache_hit:
                # Return cached result with metadata
                result = json.loads(cached_data)
                result["_cache"] = cache_metadata
                
                # Add deprecation warnings if any deprecated params were used
                if deprecation_warnings:
                    result["_deprecated"] = deprecation_warnings
                
                return self._limit_length(json.dumps(result), max_answer_chars)

        # Cache miss or not cacheable - perform query
        parsed_include_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in include_kinds] if include_kinds else None
        parsed_exclude_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in exclude_kinds] if exclude_kinds else None
        symbol_retriever = self.create_language_server_symbol_retriever()
        
        # Determine if we need body based on output_format
        need_body = effective_output_format in ("signature", "body")
        
        symbols = symbol_retriever.find_by_name(
            name_path,
            include_body=need_body,
            include_kinds=parsed_include_kinds,
            exclude_kinds=parsed_exclude_kinds,
            match_mode=effective_match_mode,
            within_relative_path=relative_path,
        )

        # Apply output_format to control what we return
        if effective_output_format == "signature":
            from serena.analytics import TokenCountEstimator

            symbol_dicts = []
            for s in symbols:
                # Get symbol dict without body first
                s_dict = _sanitize_symbol_dict(s.to_dict(kind=True, location=True, depth=depth, include_body=False))

                # Add signature and docstring
                signature = s.extract_signature()
                docstring = s.extract_docstring()

                if signature:
                    s_dict["signature"] = signature
                if docstring:
                    s_dict["docstring"] = docstring

                # Add complexity analysis if body is available
                if s.body:
                    try:
                        # Determine language from file extension
                        file_ext = s.relative_path.split('.')[-1] if s.relative_path else "py"
                        language = "python" if file_ext == "py" else file_ext

                        metrics = ComplexityAnalyzer.analyze(s.body, language)
                        s_dict["complexity"] = metrics.to_dict()
                        s_dict["recommendation"] = ComplexityAnalyzer.get_recommendation(metrics)

                        # Add token estimates
                        estimator = TokenCountEstimator()
                        sig_doc_text = (signature or "") + "\n" + (docstring or "")
                        signature_tokens = estimator.estimate_token_count(sig_doc_text)
                        full_body_tokens = estimator.estimate_token_count(s.body)

                        s_dict["tokens_estimate"] = {
                            "signature_plus_docstring": signature_tokens,
                            "full_body": full_body_tokens,
                            "savings": full_body_tokens - signature_tokens
                        }
                    except Exception as e:
                        # If complexity analysis fails, continue without it
                        import logging
                        log = logging.getLogger(__name__)
                        log.warning(f"Failed to analyze complexity for symbol {s.name}: {e}")
                        s_dict["complexity"] = {"error": str(e)}
                        s_dict["recommendation"] = "complexity_analysis_failed"

                symbol_dicts.append(s_dict)
        elif effective_output_format == "body":
            # Body mode - return complete symbol information with body
            symbol_dicts = [_sanitize_symbol_dict(s.to_dict(kind=True, location=True, depth=depth, include_body=True)) for s in symbols]
        else:
            # Metadata mode (default) - return symbol information without body
            symbol_dicts = [_sanitize_symbol_dict(s.to_dict(kind=True, location=True, depth=depth, include_body=False)) for s in symbols]

        # Add symbol IDs for on-demand body retrieval
        symbol_dicts = _add_symbol_ids(symbol_dicts)

        # Apply search scope filtering
        exclusion_metadata = None
        if effective_search_scope == "source":
            from serena.util.file_system import exclude_generated_code

            # Extract file paths from symbol_dicts
            included_symbols = []
            all_file_paths = []
            for symbol_dict in symbol_dicts:
                rel_path = symbol_dict.get("relative_path")
                if rel_path:
                    all_file_paths.append(rel_path)

            # Get unique file paths
            unique_paths = list(set(all_file_paths))

            # Filter using exclusion logic
            exclusion_result = exclude_generated_code([], unique_paths, self.project.project_root)
            included_files_set = set(exclusion_result.included_files)

            # Filter symbols - only keep those from included files
            for symbol_dict in symbol_dicts:
                rel_path = symbol_dict.get("relative_path")
                if rel_path and rel_path in included_files_set:
                    included_symbols.append(symbol_dict)
                elif not rel_path:
                    # Keep symbols without a path (shouldn't normally happen)
                    included_symbols.append(symbol_dict)

            symbol_dicts = included_symbols

            # Prepare exclusion metadata
            if exclusion_result.excluded_counts:
                exclusion_metadata = {
                    "excluded_files": exclusion_result.excluded_counts,
                    "excluded_patterns": exclusion_result.excluded_patterns,
                    "total_excluded": sum(exclusion_result.excluded_counts.values()),
                    "include_excluded_instruction": "Use search_scope='all' to include all files"
                }
        elif effective_search_scope == "custom":
            # Future feature - for now, treat as "source"
            # TODO: Load custom patterns from config
            pass

        # Apply result limiting / pagination
        symbol_dicts, pagination_meta = self._apply_result_limit(symbol_dicts, max_results, page_cursor)

        optimized_result = _optimize_symbol_list(symbol_dicts)

        # Add pagination metadata if results were capped
        if pagination_meta:
            optimized_result["_pagination"] = pagination_meta

        # Add exclusion metadata if present
        if exclusion_metadata:
            optimized_result["_excluded"] = exclusion_metadata

        # Add deprecation warnings if any deprecated params were used
        if deprecation_warnings:
            optimized_result["_deprecated"] = deprecation_warnings

        # Cache the result if single-file query
        if use_cache:
            cache_metadata = cache.put(relative_path, json.dumps(optimized_result), query_params)
            optimized_result["_cache"] = cache_metadata

        result = json.dumps(optimized_result)
        return self._limit_length(result, max_answer_chars)


class FindReferencingSymbolsTool(Tool, ToolMarkerSymbolicRead):
    """
    Finds symbols that reference the symbol at the given location (optionally filtered by type).
    """

    def apply(
        self,
        name_path: str,
        relative_path: str,
        include_kinds: list[int] = [],  # noqa: B006
        exclude_kinds: list[int] = [],  # noqa: B006
        context_lines: int = 1,
        extract_pattern: bool = True,
        mode: Literal["count", "summary", "full"] = "summary",
        max_results: int = -1,
        page_cursor: str | None = None,
        max_answer_chars: int = -1,
    ) -> str:
        """
        Finds references to the symbol at name_path. Returns referencing symbol metadata and code snippets.

        :param name_path: Same as find_symbol.
        :param relative_path: File containing the target symbol (must be a file, not directory).
        :param include_kinds: Same as find_symbol.
        :param exclude_kinds: Same as find_symbol.
        :param context_lines: Lines of context before/after each reference (default: 1).
        :param extract_pattern: Extract usage pattern from reference line for concise output (default: True).
        :param mode: count | summary (default, counts + first 10) | full (all with context).
        :param max_results: -1=config default, 0=unlimited. Paginate via page_cursor.
        :param page_cursor: From previous _pagination.next_cursor.
        :param max_answer_chars: Char limit. -1=config default.
        :return: Referencing symbols with snippets.
        """
        include_body = False  # It is probably never a good idea to include the body of the referencing symbols
        parsed_include_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in include_kinds] if include_kinds else None
        parsed_exclude_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in exclude_kinds] if exclude_kinds else None
        symbol_retriever = self.create_language_server_symbol_retriever()
        
        # First, find the symbol to get its name for pattern extraction
        target_symbol_name = name_path.split('/')[-1]  # Get the last component of the name path
        
        references_in_symbols = symbol_retriever.find_referencing_symbols(
            name_path,
            relative_file_path=relative_path,
            include_body=include_body,
            include_kinds=parsed_include_kinds,
            exclude_kinds=parsed_exclude_kinds,
        )

        # Count mode: Return only counts and metadata
        if mode == "count":
            return self._generate_count_output(references_in_symbols, name_path, relative_path)

        # Process references for summary and full modes
        reference_dicts = []
        for ref in references_in_symbols:
            ref_dict = ref.symbol.to_dict(kind=True, location=True, depth=0, include_body=include_body)
            ref_dict = _sanitize_symbol_dict(ref_dict)
            if not include_body:
                ref_relative_path = ref.symbol.location.relative_path
                assert ref_relative_path is not None, f"Referencing symbol {ref.symbol.name} has no relative path, this is likely a bug."
                content_around_ref = self.project.retrieve_content_around_line(
                    relative_file_path=ref_relative_path,
                    line=ref.line,
                    context_lines_before=context_lines,
                    context_lines_after=context_lines
                )

                # Extract the reference line for pattern extraction
                reference_line = None
                for text_line in content_around_ref.matched_lines:
                    if text_line.line_number == ref.line:
                        reference_line = text_line.line_content
                        break

                if extract_pattern and reference_line:
                    # Extract usage pattern from the reference line
                    usage_pattern = extract_usage_pattern(reference_line, target_symbol_name)
                    if usage_pattern:
                        ref_dict["usage_pattern"] = usage_pattern
                    ref_dict["full_line"] = reference_line
                    ref_dict["reference_line"] = ref.line
                else:
                    # Fall back to full context
                    ref_dict["content_around_reference"] = content_around_ref.to_display_string()

                # Add metadata about context
                ref_dict["context_lines"] = context_lines
                if extract_pattern:
                    ref_dict["pattern_extracted"] = True
                    ref_dict["expand_context_hint"] = f"Use context_lines={context_lines + 2} for more surrounding code"

            reference_dicts.append(ref_dict)

        # Summary mode: Return counts + preview of first 10 references
        if mode == "summary":
            return self._generate_summary_output(reference_dicts, name_path, relative_path)

        # Full mode: Return all references (default)
        # Apply result limiting / pagination
        reference_dicts, pagination_meta = self._apply_result_limit(reference_dicts, max_results, page_cursor)

        optimized_result = _optimize_symbol_list(reference_dicts)

        if pagination_meta:
            optimized_result["_pagination"] = pagination_meta

        result = json.dumps(optimized_result)
        return self._limit_length(result, max_answer_chars)

    def _generate_count_output(self, references_in_symbols, name_path: str, relative_path: str) -> str:
        """
        Generate count-only output for reference queries.
        Returns total_references, by_file counts, and by_type counts.
        """
        total_references = len(references_in_symbols)

        # Count by file
        by_file = {}
        by_type = {}

        for ref in references_in_symbols:
            # Count by file
            file_path = ref.symbol.location.relative_path or "unknown"
            by_file[file_path] = by_file.get(file_path, 0) + 1

            # Count by symbol kind/type
            symbol_kind = ref.symbol.kind.name if ref.symbol.kind else "unknown"
            by_type[symbol_kind] = by_type.get(symbol_kind, 0) + 1

        # Sort by count (descending)
        by_file_sorted = dict(sorted(by_file.items(), key=lambda x: x[1], reverse=True))
        by_type_sorted = dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True))

        result = {
            "_schema": "reference_count_v1",
            "symbol": name_path,
            "file": relative_path,
            "total_references": total_references,
            "by_file": by_file_sorted,
            "by_type": by_type_sorted,
            "mode_used": "count",
            "full_details_available": "Use mode='full' to see all references with context",
            "summary_available": "Use mode='summary' to see counts + first 10 matches"
        }

        return json.dumps(result, indent=2)

    def _generate_summary_output(self, reference_dicts: list, name_path: str, relative_path: str) -> str:
        """
        Generate summary output with counts + preview of first 10 references.
        """
        total_references = len(reference_dicts)

        # Count by file
        by_file = {}
        for ref_dict in reference_dicts:
            file_path = ref_dict.get("relative_path", "unknown")
            by_file[file_path] = by_file.get(file_path, 0) + 1

        # Sort by count (descending)
        by_file_sorted = dict(sorted(by_file.items(), key=lambda x: x[1], reverse=True))

        # Take first 10 references for preview
        preview_limit = 10
        preview_refs = reference_dicts[:preview_limit]

        # Create lightweight preview (just file, line, usage pattern)
        preview = []
        for ref in preview_refs:
            preview_item = {
                "file": ref.get("relative_path", "unknown"),
                "line": ref.get("reference_line") or ref.get("line", 0),
            }

            # Add usage pattern if available
            if "usage_pattern" in ref:
                preview_item["usage_pattern"] = ref["usage_pattern"]
            elif "full_line" in ref:
                # Truncate full line to 100 chars
                full_line = ref["full_line"].strip()
                preview_item["snippet"] = full_line[:100] + ("..." if len(full_line) > 100 else "")

            preview.append(preview_item)

        result = {
            "_schema": "reference_summary_v1",
            "symbol": name_path,
            "file": relative_path,
            "total_references": total_references,
            "by_file": by_file_sorted,
            "preview": preview,
            "preview_count": len(preview),
            "mode_used": "summary",
            "showing": f"Showing {len(preview)} of {total_references} references",
            "full_details_available": f"Use mode='full' to see all {total_references} references with full context"
        }

        return json.dumps(result, indent=2)


class ReplaceSymbolBodyTool(Tool, ToolMarkerSymbolicEdit):
    """
    Replaces the full definition of a symbol.
    """

    def apply(
        self,
        name_path: str,
        relative_path: str,
        body: str,
        response_format: str = "diff",
    ) -> str:
        r"""
        Replaces the body of the symbol with the given `name_path`.

        :param name_path: for finding the symbol to replace, same logic as in the `find_symbol` tool.
        :param relative_path: the relative path to the file containing the symbol
        :param body: the new symbol body. Important: Begin directly with the symbol definition and provide no
            leading indentation for the first line (but do indent the rest of the body according to the context).
        :param response_format: output format - "diff" (default, concise unified diff), 
            "summary" (brief confirmation), or "full" (complete file content)
        """
        import os
        
        # Read old content if diff or full format requested
        if response_format in ("diff", "full"):
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        
        # Perform the edit
        code_editor = self.create_code_editor()
        code_editor.replace_body(
            name_path,
            relative_file_path=relative_path,
            body=body,
        )
        
        # Invalidate cache for the edited file
        cache = get_global_cache(self.project.project_root)
        invalidated_count = cache.invalidate_file(relative_path)
        
        # Generate response based on format
        if response_format == "summary":
            return json.dumps({
                "status": "success",
                "operation": "replace_symbol_body",
                "file": relative_path,
                "symbol": name_path,
                "message": f"Successfully replaced body of '{name_path}' in {relative_path}",
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        elif response_format == "full":
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            return json.dumps({
                "status": "success",
                "operation": "replace_symbol_body",
                "file": relative_path,
                "symbol": name_path,
                "new_content": new_content,
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        else:  # diff (default)
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            
            diff_output = _generate_unified_diff(old_content, new_content, relative_path)
            
            if not diff_output:
                # No changes detected
                return json.dumps({
                    "status": "success",
                    "operation": "replace_symbol_body",
                    "file": relative_path,
                    "symbol": name_path,
                    "message": "No changes detected (content identical)",
                    "_cache_invalidated": invalidated_count
                }, indent=2)
            
            return json.dumps({
                "status": "success",
                "operation": "replace_symbol_body",
                "file": relative_path,
                "symbol": name_path,
                "diff": diff_output,
                "hint": "Use response_format='full' to see complete file content",
                "_cache_invalidated": invalidated_count
            }, indent=2)


class InsertAfterSymbolTool(Tool, ToolMarkerSymbolicEdit):
    """
    Inserts content after the end of the definition of a given symbol.
    """

    def apply(
        self,
        name_path: str,
        relative_path: str,
        body: str,
        response_format: str = "diff",
    ) -> str:
        """
        Inserts content after the symbol's definition. Typical use: add a new class, function, or method.

        :param name_path: Target symbol (find_symbol rules apply).
        :param relative_path: File containing the symbol.
        :param body: Content to insert after the symbol's definition.
        :param response_format: diff (default) | summary | full.
        """
        import os
        
        # Read old content if diff or full format requested
        if response_format in ("diff", "full"):
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        
        # Perform the edit
        code_editor = self.create_code_editor()
        code_editor.insert_after_symbol(name_path, relative_file_path=relative_path, body=body)
        
        # Invalidate cache for the edited file
        cache = get_global_cache(self.project.project_root)
        invalidated_count = cache.invalidate_file(relative_path)
        
        # Generate response based on format
        if response_format == "summary":
            return json.dumps({
                "status": "success",
                "operation": "insert_after_symbol",
                "file": relative_path,
                "symbol": name_path,
                "message": f"Successfully inserted content after '{name_path}' in {relative_path}",
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        elif response_format == "full":
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            return json.dumps({
                "status": "success",
                "operation": "insert_after_symbol",
                "file": relative_path,
                "symbol": name_path,
                "new_content": new_content,
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        else:  # diff (default)
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            
            diff_output = _generate_unified_diff(old_content, new_content, relative_path)
            
            return json.dumps({
                "status": "success",
                "operation": "insert_after_symbol",
                "file": relative_path,
                "symbol": name_path,
                "diff": diff_output,
                "hint": "Use response_format='full' to see complete file content",
                "_cache_invalidated": invalidated_count
            }, indent=2)


class InsertBeforeSymbolTool(Tool, ToolMarkerSymbolicEdit):
    """
    Inserts content before the beginning of the definition of a given symbol.
    """

    def apply(
        self,
        name_path: str,
        relative_path: str,
        body: str,
        response_format: str = "diff",
    ) -> str:
        """
        Inserts content before the symbol's definition. Typical use: add imports or new symbols above existing ones.

        :param name_path: Target symbol (find_symbol rules apply).
        :param relative_path: File containing the symbol.
        :param body: Content to insert before the symbol's definition.
        :param response_format: diff (default) | summary | full.
        """
        import os
        
        # Read old content if diff or full format requested
        if response_format in ("diff", "full"):
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        
        # Perform the edit
        code_editor = self.create_code_editor()
        code_editor.insert_before_symbol(name_path, relative_file_path=relative_path, body=body)
        
        # Invalidate cache for the edited file
        cache = get_global_cache(self.project.project_root)
        invalidated_count = cache.invalidate_file(relative_path)
        
        # Generate response based on format
        if response_format == "summary":
            return json.dumps({
                "status": "success",
                "operation": "insert_before_symbol",
                "file": relative_path,
                "symbol": name_path,
                "message": f"Successfully inserted content before '{name_path}' in {relative_path}",
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        elif response_format == "full":
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            return json.dumps({
                "status": "success",
                "operation": "insert_before_symbol",
                "file": relative_path,
                "symbol": name_path,
                "new_content": new_content,
                "_cache_invalidated": invalidated_count
            }, indent=2)
        
        else:  # diff (default)
            full_path = os.path.join(self.agent.get_project_root(), relative_path)
            with open(full_path, "r", encoding="utf-8") as f:
                new_content = f.read()
            
            diff_output = _generate_unified_diff(old_content, new_content, relative_path)
            
            return json.dumps({
                "status": "success",
                "operation": "insert_before_symbol",
                "file": relative_path,
                "symbol": name_path,
                "diff": diff_output,
                "hint": "Use response_format='full' to see complete file content",
                "_cache_invalidated": invalidated_count
            }, indent=2)


class GetSymbolBodyTool(Tool, ToolMarkerSymbolicRead):
    """
    Retrieves the body/source code for specific symbols by their symbol IDs.
    Enables massive token savings by separating search from body retrieval.
    """

    def apply(
        self,
        symbol_id: str | list[str],
        max_answer_chars: int = -1,
    ) -> str:
        """
        Retrieve source code for symbols by ID. Symbol ID format: name_path:relative_path:line_number.

        :param symbol_id: Single symbol ID or list. IDs come from find_symbol's "symbol_id" field.
        :param max_answer_chars: Char limit. -1=config default.
        :return: JSON with symbol bodies.
        """
        # Handle both single and batch retrieval
        symbol_ids = [symbol_id] if isinstance(symbol_id, str) else symbol_id

        if not symbol_ids:
            return json.dumps({"error": "No symbol IDs provided"}, indent=2)

        results = []
        errors = []

        for sid in symbol_ids:
            try:
                # Parse symbol ID: name_path:relative_path:line_number
                parts = sid.split(":", 2)
                if len(parts) != 3:
                    errors.append({
                        "symbol_id": sid,
                        "error": "Invalid symbol ID format. Expected 'name_path:relative_path:line_number'"
                    })
                    continue

                name_path, relative_path, line_str = parts

                try:
                    line_number = int(line_str)
                except ValueError:
                    errors.append({
                        "symbol_id": sid,
                        "error": f"Invalid line number: {line_str}"
                    })
                    continue

                # Find the symbol using the retriever
                symbol_retriever = self.create_language_server_symbol_retriever()
                symbols = symbol_retriever.find_by_name(
                    name_path,
                    include_body=True,
                    substring_matching=False,
                    within_relative_path=relative_path,
                )

                # Find the exact symbol by line number
                matching_symbol = None
                for s in symbols:
                    if s.line == line_number:
                        matching_symbol = s
                        break

                if not matching_symbol:
                    errors.append({
                        "symbol_id": sid,
                        "error": f"Symbol not found at line {line_number} in {relative_path}"
                    })
                    continue

                # Get the body
                body = matching_symbol.body
                if not body:
                    errors.append({
                        "symbol_id": sid,
                        "error": "Symbol found but body is empty"
                    })
                    continue

                # Get token estimate
                from serena.util.token_estimator import get_token_estimator
                estimator = get_token_estimator()
                token_estimate = estimator.estimate_code(body)

                results.append({
                    "symbol_id": sid,
                    "name_path": name_path,
                    "relative_path": relative_path,
                    "line": line_number,
                    "kind": matching_symbol.kind,
                    "body": body,
                    "body_lines": f"{matching_symbol.get_body_start_position()[0]}-{matching_symbol.get_body_end_position()[0]}",
                    "estimated_tokens": token_estimate
                })

            except Exception as e:
                import logging
                log = logging.getLogger(__name__)
                log.warning(f"Error retrieving body for symbol_id {sid}: {e}")
                errors.append({
                    "symbol_id": sid,
                    "error": f"Unexpected error: {str(e)}"
                })

        # Build response
        response = {
            "_schema": "get_symbol_body_v1",
            "requested": len(symbol_ids),
            "retrieved": len(results),
            "failed": len(errors)
        }

        if results:
            response["symbols"] = results

        if errors:
            response["errors"] = errors

        result_json = json.dumps(response, indent=2)
        return self._limit_length(result_json, max_answer_chars)
