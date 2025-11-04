"""
Language server-related tools
"""

import dataclasses
import json
import os
from collections.abc import Sequence
from copy import copy
from typing import Any, Literal

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

    def apply(self, relative_path: str, max_answer_chars: int = -1) -> str:
        """
        Use this tool to get a high-level understanding of the code symbols in a file.
        This should be the first tool to call when you want to understand a new file, unless you already know
        what you are looking for.

        :param relative_path: the relative path to the file to get the overview of
        :param max_answer_chars: if the overview is longer than this number of characters,
            no content will be returned. -1 means the default value from the config will be used.
            Don't adjust unless there is really no other way to get the content required for the task.
        :return: a JSON object containing info about top-level symbols in the file
        """
        # Use cache for symbol overview
        cache = get_global_cache(self.project.project_root)
        query_params = {"tool": "get_symbols_overview"}
        
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
        result = symbol_retriever.get_symbol_overview(relative_path)[relative_path]
        # Optimize: since all symbols are from the same file, use structured format
        symbol_list = [dataclasses.asdict(i) for i in result]
        optimized_result = {
            "_schema": "structured_v1",
            "file": relative_path,
            "symbols": symbol_list
        }
        
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
        include_body: bool = False,
        detail_level: Literal["full", "signature", "auto"] = "full",
        include_kinds: list[int] = [],  # noqa: B006
        exclude_kinds: list[int] = [],  # noqa: B006
        substring_matching: bool = False,
        max_answer_chars: int = -1,
    ) -> str:
        """
        Retrieves information on all symbols/code entities (classes, methods, etc.) based on the given `name_path`,
        which represents a pattern for the symbol's path within the symbol tree of a single file.
        The returned symbol location can be used for edits or further queries.
        Specify `depth > 0` to retrieve children (e.g., methods of a class).

        The matching behavior is determined by the structure of `name_path`, which can
        either be a simple name (e.g. "method") or a name path like "class/method" (relative name path)
        or "/class/method" (absolute name path). Note that the name path is not a path in the file system
        but rather a path in the symbol tree **within a single file**. Thus, file or directory names should never
        be included in the `name_path`. For restricting the search to a single file or directory,
        the `within_relative_path` parameter should be used instead. The retrieved symbols' `name_path` attribute
        will always be composed of symbol names, never file or directory names.

        Key aspects of the name path matching behavior:
        - Trailing slashes in `name_path` play no role and are ignored.
        - The name of the retrieved symbols will match (either exactly or as a substring)
          the last segment of `name_path`, while other segments will restrict the search to symbols that
          have a desired sequence of ancestors.
        - If there is no starting or intermediate slash in `name_path`, there is no
          restriction on the ancestor symbols. For example, passing `method` will match
          against symbols with name paths like `method`, `class/method`, `class/nested_class/method`, etc.
        - If `name_path` contains a `/` but doesn't start with a `/`, the matching is restricted to symbols
          with the same ancestors as the last segment of `name_path`. For example, passing `class/method` will match against
          `class/method` as well as `nested_class/class/method` but not `method`.
        - If `name_path` starts with a `/`, it will be treated as an absolute name path pattern, meaning
          that the first segment of it must match the first segment of the symbol's name path.
          For example, passing `/class` will match only against top-level symbols like `class` but not against `nested_class/class`.
          Passing `/class/method` will match against `class/method` but not `nested_class/class/method` or `method`.


        :param name_path: The name path pattern to search for, see above for details.
        :param depth: Depth to retrieve descendants (e.g., 1 for class methods/attributes).
        :param relative_path: Optional. Restrict search to this file or directory. If None, searches entire codebase.
            If a directory is passed, the search will be restricted to the files in that directory.
            If a file is passed, the search will be restricted to that file.
            If you have some knowledge about the codebase, you should use this parameter, as it will significantly
            speed up the search as well as reduce the number of results.
        :param include_body: If True, include the symbol's source code. Use judiciously.
        :param detail_level: Level of detail to return. Options:
            - "full" (default): Return complete symbol information including body if include_body=True
            - "signature": Return signature + docstring only with complexity analysis and warnings
            - "auto": Automatically decide based on complexity (not yet implemented, defaults to "full")
        :param include_kinds: Optional. List of LSP symbol kind integers to include. (e.g., 5 for Class, 12 for Function).
            Valid kinds: 1=file, 2=module, 3=namespace, 4=package, 5=class, 6=method, 7=property, 8=field, 9=constructor, 10=enum,
            11=interface, 12=function, 13=variable, 14=constant, 15=string, 16=number, 17=boolean, 18=array, 19=object,
            20=key, 21=null, 22=enum member, 23=struct, 24=event, 25=operator, 26=type parameter.
            If not provided, all kinds are included.
        :param exclude_kinds: Optional. List of LSP symbol kind integers to exclude. Takes precedence over `include_kinds`.
            If not provided, no kinds are excluded.
        :param substring_matching: If True, use substring matching for the last segment of `name`.
        :param max_answer_chars: Max characters for the JSON result. If exceeded, no content is returned.
            -1 means the default value from the config will be used.
        :return: a list of symbols (with locations) matching the name.
        """
        # Only use cache for single-file queries (not directory/global searches)
        cache = get_global_cache(self.project.project_root)
        use_cache = relative_path and os.path.isfile(os.path.join(self.project.project_root, relative_path))

        if use_cache:
            # Build query params for cache key
            query_params = {
                "name_path": name_path,
                "depth": depth,
                "include_body": include_body,
                "detail_level": detail_level,
                "include_kinds": include_kinds,
                "exclude_kinds": exclude_kinds,
                "substring_matching": substring_matching,
                "tool": "find_symbol"
            }

            # Try cache first
            cache_hit, cached_data, cache_metadata = cache.get(relative_path, query_params)
            if cache_hit:
                # Return cached result with metadata
                result = json.loads(cached_data)
                result["_cache"] = cache_metadata
                return self._limit_length(json.dumps(result), max_answer_chars)

        # Cache miss or not cacheable - perform query
        parsed_include_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in include_kinds] if include_kinds else None
        parsed_exclude_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in exclude_kinds] if exclude_kinds else None
        symbol_retriever = self.create_language_server_symbol_retriever()
        symbols = symbol_retriever.find_by_name(
            name_path,
            include_body=include_body,
            include_kinds=parsed_include_kinds,
            exclude_kinds=parsed_exclude_kinds,
            substring_matching=substring_matching,
            within_relative_path=relative_path,
        )
        # Handle detail_level - auto defaults to full for now
        effective_detail_level = detail_level if detail_level != "auto" else "full"

        # For signature mode, we need to fetch the body to perform analysis
        need_body_for_analysis = effective_detail_level == "signature"
        actual_include_body = include_body or need_body_for_analysis

        # Re-fetch with body if we didn't include it initially but need it for signature mode
        if need_body_for_analysis and not include_body:
            symbols = symbol_retriever.find_by_name(
                name_path,
                include_body=True,  # Need body for complexity analysis
                include_kinds=parsed_include_kinds,
                exclude_kinds=parsed_exclude_kinds,
                substring_matching=substring_matching,
                within_relative_path=relative_path,
            )

        # Apply detail_level and add complexity analysis if needed
        if effective_detail_level == "signature":
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
        else:
            # Full mode - return complete symbol information
            symbol_dicts = [_sanitize_symbol_dict(s.to_dict(kind=True, location=True, depth=depth, include_body=include_body)) for s in symbols]

        optimized_result = _optimize_symbol_list(symbol_dicts)

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
        max_answer_chars: int = -1,
    ) -> str:
        """
        Finds references to the symbol at the given `name_path`. The result will contain metadata about the referencing symbols
        as well as a short code snippet around the reference.

        :param name_path: for finding the symbol to find references for, same logic as in the `find_symbol` tool.
        :param relative_path: the relative path to the file containing the symbol for which to find references.
            Note that here you can't pass a directory but must pass a file.
        :param include_kinds: same as in the `find_symbol` tool.
        :param exclude_kinds: same as in the `find_symbol` tool.
        :param max_answer_chars: same as in the `find_symbol` tool.
        :return: a list of JSON objects with the symbols referencing the requested symbol
        """
        include_body = False  # It is probably never a good idea to include the body of the referencing symbols
        parsed_include_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in include_kinds] if include_kinds else None
        parsed_exclude_kinds: Sequence[SymbolKind] | None = [SymbolKind(k) for k in exclude_kinds] if exclude_kinds else None
        symbol_retriever = self.create_language_server_symbol_retriever()
        references_in_symbols = symbol_retriever.find_referencing_symbols(
            name_path,
            relative_file_path=relative_path,
            include_body=include_body,
            include_kinds=parsed_include_kinds,
            exclude_kinds=parsed_exclude_kinds,
        )
        reference_dicts = []
        for ref in references_in_symbols:
            ref_dict = ref.symbol.to_dict(kind=True, location=True, depth=0, include_body=include_body)
            ref_dict = _sanitize_symbol_dict(ref_dict)
            if not include_body:
                ref_relative_path = ref.symbol.location.relative_path
                assert ref_relative_path is not None, f"Referencing symbol {ref.symbol.name} has no relative path, this is likely a bug."
                content_around_ref = self.project.retrieve_content_around_line(
                    relative_file_path=ref_relative_path, line=ref.line, context_lines_before=1, context_lines_after=1
                )
                ref_dict["content_around_reference"] = content_around_ref.to_display_string()
            reference_dicts.append(ref_dict)
        optimized_result = _optimize_symbol_list(reference_dicts)
        result = json.dumps(optimized_result)
        return self._limit_length(result, max_answer_chars)


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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
        Inserts the given body/content after the end of the definition of the given symbol (via the symbol's location).
        A typical use case is to insert a new class, function, method, field or variable assignment.

        :param name_path: name path of the symbol after which to insert content (definitions in the `find_symbol` tool apply)
        :param relative_path: the relative path to the file containing the symbol
        :param body: the body/content to be inserted. The inserted code shall begin with the next line after
            the symbol.
        :param response_format: output format - "diff" (default, concise unified diff), 
            "summary" (brief confirmation), or "full" (complete file content)
        """
        import os
        
        # Read old content if diff or full format requested
        if response_format in ("diff", "full"):
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
        Inserts the given content before the beginning of the definition of the given symbol (via the symbol's location).
        A typical use case is to insert a new class, function, method, field or variable assignment; or
        a new import statement before the first symbol in the file.

        :param name_path: name path of the symbol before which to insert content (definitions in the `find_symbol` tool apply)
        :param relative_path: the relative path to the file containing the symbol
        :param body: the body/content to be inserted before the line in which the referenced symbol is defined
        :param response_format: output format - "diff" (default, concise unified diff), 
            "summary" (brief confirmation), or "full" (complete file content)
        """
        import os
        
        # Read old content if diff or full format requested
        if response_format in ("diff", "full"):
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
            full_path = os.path.join(self.agent.project_root, relative_path)
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
