"""
File and file system-related tools, specifically for
  * listing directory contents
  * reading files
  * creating files
  * editing at the file level
"""

import json
import os
import re
from collections import defaultdict
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path

from typing import Literal

from serena.text_utils import search_files
from serena.tools import SUCCESS_RESULT, EditedFileContext, Tool, ToolMarkerCanEdit, ToolMarkerOptional
from serena.util.file_system import scan_directory


class ReadFileTool(Tool):
    """
    Reads a file within the project directory.
    """

    def apply(self, relative_path: str, start_line: int = 0, end_line: int | None = None, max_answer_chars: int = -1) -> str:
        """
        Reads the given file or a chunk of it. Generally, symbolic operations
        like find_symbol or find_referencing_symbols should be preferred if you know which symbols you are looking for.

        :param relative_path: the relative path to the file to read
        :param start_line: the 0-based index of the first line to be retrieved.
        :param end_line: the 0-based index of the last line to be retrieved (inclusive). If None, read until the end of the file.
        :param max_answer_chars: if the file (chunk) is longer than this number of characters,
            no content will be returned. Don't adjust unless there is really no other way to get the content
            required for the task.
        :return: the full text of the file at the given relative path
        """
        self.project.validate_relative_path(relative_path)

        result = self.project.read_file(relative_path)
        result_lines = result.splitlines()
        if end_line is None:
            result_lines = result_lines[start_line:]
        else:
            self.lines_read.add_lines_read(relative_path, (start_line, end_line))
            result_lines = result_lines[start_line : end_line + 1]
        result = "\n".join(result_lines)

        return self._limit_length(result, max_answer_chars)


class CreateTextFileTool(Tool, ToolMarkerCanEdit):
    """
    Creates/overwrites a file in the project directory.
    """

    def apply(self, relative_path: str, content: str) -> str:
        """
        Write a new file or overwrite an existing file.

        :param relative_path: the relative path to the file to create
        :param content: the (utf-8-encoded) content to write to the file
        :return: a message indicating success or failure
        """
        project_root = self.get_project_root()
        abs_path = (Path(project_root) / relative_path).resolve()
        will_overwrite_existing = abs_path.exists()

        if will_overwrite_existing:
            self.project.validate_relative_path(relative_path)
        else:
            assert abs_path.is_relative_to(
                self.get_project_root()
            ), f"Cannot create file outside of the project directory, got {relative_path=}"

        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        answer = f"File created: {relative_path}."
        if will_overwrite_existing:
            answer += " Overwrote existing file."
        return json.dumps(answer)


def _build_tree_format(dirs: list[str], files: list[str], base_path: str) -> str:
    """
    Build a collapsed tree format showing directories with file counts.

    :param dirs: list of directory paths (relative)
    :param files: list of file paths (relative)
    :param base_path: the base path for relative display
    :return: formatted tree string
    """
    # Build directory structure with file counts
    dir_counts = defaultdict(int)
    dir_files = defaultdict(list)

    # Count files in each directory
    for file_path in files:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            dir_counts[dir_path] += 1
            dir_files[dir_path].append(os.path.basename(file_path))
        else:
            # Files in root
            dir_counts["."] += 1
            dir_files["."].append(file_path)

    # Build tree structure
    # Group directories by depth and parent
    root_items = []
    
    # Separate immediate children from nested directories
    immediate_dirs = set()
    immediate_files = []
    
    for dir_path in sorted(dirs):
        if "/" not in dir_path.replace("\\", "/"):
            # Immediate subdirectory
            immediate_dirs.add(dir_path)
    
    for file_path in sorted(files):
        if "/" not in file_path.replace("\\", "/") and "\\" not in file_path:
            # Immediate file
            immediate_files.append(file_path)
    
    # Build output
    lines = []
    
    # Show immediate directories with counts
    for dir_path in sorted(immediate_dirs):
        # Normalize path separators
        normalized = dir_path.replace("\\", "/")
        
        # Count total files in this directory tree (including subdirectories)
        count = sum(1 for f in files if f.replace("\\", "/").startswith(normalized + "/"))
        
        if count > 0:
            lines.append(f"{dir_path}/ ({count} files)")
        else:
            lines.append(f"{dir_path}/ (empty)")
    
    # Show immediate files
    if immediate_files:
        for file in immediate_files:
            lines.append(file)
    
    # Add instructions
    if immediate_dirs:
        lines.append("")
        example_dir = next(iter(sorted(immediate_dirs)))
        lines.append(f"Expand with: list_dir(\"{example_dir}\", recursive=false)")
    
    return "\n".join(lines)


class ListDirTool(Tool):
    """
    Lists files and directories in the given directory (optionally with recursion).
    """

    def apply(self, relative_path: str, recursive: bool, format: str = "list", exclude_generated: bool | None = None, search_scope: Literal["all", "source", "custom"] = "source", max_answer_chars: int = -1) -> str:
        """
        Lists all non-gitignored files and directories in the given directory (optionally with recursion).

        :param relative_path: the relative path to the directory to list; pass "." to scan the project root
        :param recursive: whether to scan subdirectories recursively
        :param format: output format - "list" (default, full listing) or "tree" (collapsed tree with file counts)
        :param search_scope: Controls which files to list. Options:
            - "source" (default): Exclude common generated/vendor patterns (node_modules, __pycache__, migrations,
              dist, build, .venv, venv, target, .next, .nuxt, vendor, .git, .pytest_cache, .mypy_cache,
              coverage, htmlcov, wheelhouse, *.egg-info)
            - "all": Include all files (no exclusions)
            - "custom": Use custom patterns from config (future feature)

            Default is "source" which is what agents want 95% of the time. Use "all" to explicitly list everything.
            When files are excluded, response includes exclusion metadata showing what was filtered.
        :param exclude_generated: [DEPRECATED] Use search_scope instead. If provided, overrides search_scope.
            This parameter will be removed in version 2.0.0.
            - exclude_generated=True maps to search_scope="source"
            - exclude_generated=False maps to search_scope="all"
        :param max_answer_chars: if the output is longer than this number of characters,
            no content will be returned. -1 means the default value from the config will be used.
            Don't adjust unless there is really no other way to get the content required for the task.
        :return: a JSON object with the names of directories and files within the given directory (format="list"),
                 or a tree-formatted string showing collapsed directories with file counts (format="tree")
        """
        # Check if the directory exists before validation
        if not self.project.relative_path_exists(relative_path):
            error_info = {
                "error": f"Directory not found: {relative_path}",
                "project_root": self.get_project_root(),
                "hint": "Check if the path is correct relative to the project root",
            }
            return json.dumps(error_info)

        self.project.validate_relative_path(relative_path)

        # Handle parameter deprecation
        deprecation_warnings = []
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

        dirs, files = scan_directory(
            os.path.join(self.get_project_root(), relative_path),
            relative_to=self.get_project_root(),
            recursive=recursive,
            is_ignored_dir=self.project.is_ignored_path,
            is_ignored_file=self.project.is_ignored_path,
        )

        # Apply search scope filtering
        exclusion_metadata = None
        if effective_search_scope == "source":
            from serena.util.file_system import exclude_generated_code

            exclusion_result = exclude_generated_code(dirs, files, self.get_project_root())
            dirs = exclusion_result.included_dirs
            files = exclusion_result.included_files

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

        # Format output based on requested format
        if format == "tree" and recursive:
            # Tree format: collapsed directories with file counts
            tree_output = _build_tree_format(dirs, files, relative_path)
            result_dict = {
                "_schema": "tree_v1",
                "format": "tree",
                "base_path": relative_path,
                "tree": tree_output,
                "total_dirs": len(dirs),
                "total_files": len(files)
            }
            if exclusion_metadata:
                result_dict["_excluded"] = exclusion_metadata
            if deprecation_warnings:
                result_dict["_deprecated"] = deprecation_warnings
            result = json.dumps(result_dict)
        else:
            # List format (default): full listing
            result_dict = {"dirs": dirs, "files": files}
            if exclusion_metadata:
                result_dict["_excluded"] = exclusion_metadata
            if deprecation_warnings:
                result_dict["_deprecated"] = deprecation_warnings
            result = json.dumps(result_dict)

        return self._limit_length(result, max_answer_chars)


class FindFileTool(Tool):
    """
    Finds files in the given relative paths
    """

    def apply(self, file_mask: str, relative_path: str) -> str:
        """
        Finds non-gitignored files matching the given file mask within the given relative path

        :param file_mask: the filename or file mask (using the wildcards * or ?) to search for
        :param relative_path: the relative path to the directory to search in; pass "." to scan the project root
        :return: a JSON object with the list of matching files
        """
        self.project.validate_relative_path(relative_path)

        dir_to_scan = os.path.join(self.get_project_root(), relative_path)

        # find the files by ignoring everything that doesn't match
        def is_ignored_file(abs_path: str) -> bool:
            if self.project.is_ignored_path(abs_path):
                return True
            filename = os.path.basename(abs_path)
            return not fnmatch(filename, file_mask)

        dirs, files = scan_directory(
            path=dir_to_scan,
            recursive=True,
            is_ignored_dir=self.project.is_ignored_path,
            is_ignored_file=is_ignored_file,
            relative_to=self.get_project_root(),
        )

        result = json.dumps({"files": files})
        return result


class ReplaceContentTool(Tool, ToolMarkerCanEdit):
    """
    Replaces content in a file (optionally using regular expressions).
    """

    def apply(
        self,
        relative_path: str,
        needle: str,
        repl: str,
        mode: Literal["literal", "regex"],
        allow_multiple_occurrences: bool = False,
    ) -> str:
        r"""
        Replaces one or more occurrences of a given pattern in a file with new content.

        This is the preferred way to replace content in a file whenever the symbol-level
        tools are not appropriate.

        VERY IMPORTANT: The "regex" mode allows very large sections of code to be replaced without fully quoting them!
        Use a regex of the form "beginning.*?end-of-text-to-be-replaced" to be faster and more economical!
        ALWAYS try to use wildcards to avoid specifying the exact content to be replaced,
        especially if it spans several lines. Note that you cannot make mistakes, because if the regex should match
        multiple occurrences while you disabled `allow_multiple_occurrences`, an error will be returned, and you can retry
        with a revised regex.
        Therefore, using regex mode with suitable wildcards is usually the best choice!

        :param relative_path: the relative path to the file
        :param needle: the string or regex pattern to search for.
            If `mode` is "literal", this string will be matched exactly.
            If `mode` is "regex", this string will be treated as a regular expression (syntax of Python's `re` module,
            with flags DOTALL and MULTILINE enabled).
        :param repl: the replacement string (verbatim).
            If mode is "regex", the string can contain backreferences to matched groups in the needle regex,
            specified using the syntax $!1, $!2, etc. for groups 1, 2, etc.
        :param mode: either "literal" or "regex", specifying how the `needle` parameter is to be interpreted.
        :param allow_multiple_occurrences: if True, the regex may match multiple occurrences in the file
            and all of them will be replaced.
            If this is set to False and the regex matches multiple occurrences, an error will be returned
            (and you may retry with a revised, more specific regex).
        """
        return self.replace_content(
            relative_path, needle, repl, mode=mode, allow_multiple_occurrences=allow_multiple_occurrences
        )

    @staticmethod
    def _create_replacement_function(regex_pattern: str, repl_template: str, regex_flags: int) -> Callable[[re.Match], str]:
        """
        Creates a replacement function that validates for ambiguity and handles backreferences.

        :param regex_pattern: The regex pattern being used for matching
        :param repl_template: The replacement template with $!1, $!2, etc. for backreferences
        :param regex_flags: The flags to use when searching (e.g., re.DOTALL | re.MULTILINE)
        :return: A function suitable for use with re.sub() or re.subn()
        """

        def validate_and_replace(match: re.Match) -> str:
            matched_text = match.group(0)

            # For multi-line match, check if the same pattern matches again within the already-matched text,
            # rendering the match ambiguous. Typical pattern in the code:
            #    <start><other-stuff><start><stuff><end>
            # When matching
            #    <start>.*?<end>
            # this will match the entire span above, while only the suffix may have been intended.
            # (See test case for a practical example.)
            # To detect this, we check if the same pattern matches again within the matched text,
            if "\n" in matched_text and re.search(regex_pattern, matched_text[1:], flags=regex_flags):
                raise ValueError(
                    "Match is ambiguous: the search pattern matches multiple overlapping occurrences. "
                    "Please revise the search pattern to be more specific to avoid ambiguity."
                )

            # Handle backreferences: replace $!1, $!2, etc. with actual matched groups
            def expand_backreference(m: re.Match) -> str:
                group_num = int(m.group(1))
                group_value = match.group(group_num)
                return group_value if group_value is not None else m.group(0)

            result = re.sub(r"\$!(\d+)", expand_backreference, repl_template)
            return result

        return validate_and_replace

    def replace_content(
        self,
        relative_path: str,
        needle: str,
        repl: str,
        mode: Literal["literal", "regex"],
        allow_multiple_occurrences: bool = False,
    ) -> str:
        """
        Performs the replacement, with additional options not exposed in the tool.
        This function can be used internally by other tools.
        """
        self.project.validate_relative_path(relative_path)
        with EditedFileContext(relative_path, self.agent) as context:
            original_content = context.get_original_content()

            if mode == "literal":
                regex = re.escape(needle)
            elif mode == "regex":
                regex = needle
            else:
                raise ValueError(f"Invalid mode: '{mode}', expected 'literal' or 'regex'.")

            regex_flags = re.DOTALL | re.MULTILINE

            # create replacement function with validation and backreference handling
            repl_fn = self._create_replacement_function(regex, repl, regex_flags=regex_flags)

            # perform replacement
            updated_content, n = re.subn(regex, repl_fn, original_content, flags=regex_flags)

            if n == 0:
                raise ValueError(f"Error: No matches of search expression found in file '{relative_path}'.")
            if not allow_multiple_occurrences and n > 1:
                raise ValueError(
                    f"Expression matches {n} occurrences in file '{relative_path}'. "
                    "Please revise the expression to be more specific or enable allow_multiple_occurrences if this is expected."
                )
            context.set_updated_content(updated_content)

        return SUCCESS_RESULT


class DeleteLinesTool(Tool, ToolMarkerCanEdit, ToolMarkerOptional):
    """
    Deletes a range of lines within a file.
    """

    def apply(
        self,
        relative_path: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """
        Deletes the given lines in the file.
        Requires that the same range of lines was previously read using the `read_file` tool to verify correctness
        of the operation.

        :param relative_path: the relative path to the file
        :param start_line: the 0-based index of the first line to be deleted
        :param end_line: the 0-based index of the last line to be deleted
        """
        if not self.lines_read.were_lines_read(relative_path, (start_line, end_line)):
            read_lines_tool = self.agent.get_tool(ReadFileTool)
            return f"Error: Must call `{read_lines_tool.get_name_from_cls()}` first to read exactly the affected lines."
        code_editor = self.create_code_editor()
        code_editor.delete_lines(relative_path, start_line, end_line)
        return SUCCESS_RESULT


class ReplaceLinesTool(Tool, ToolMarkerCanEdit, ToolMarkerOptional):
    """
    Replaces a range of lines within a file with new content.
    """

    def apply(
        self,
        relative_path: str,
        start_line: int,
        end_line: int,
        content: str,
    ) -> str:
        """
        Replaces the given range of lines in the given file.
        Requires that the same range of lines was previously read using the `read_file` tool to verify correctness
        of the operation.

        :param relative_path: the relative path to the file
        :param start_line: the 0-based index of the first line to be deleted
        :param end_line: the 0-based index of the last line to be deleted
        :param content: the content to insert
        """
        if not content.endswith("\n"):
            content += "\n"
        result = self.agent.get_tool(DeleteLinesTool).apply(relative_path, start_line, end_line)
        if result != SUCCESS_RESULT:
            return result
        self.agent.get_tool(InsertAtLineTool).apply(relative_path, start_line, content)
        return SUCCESS_RESULT


class InsertAtLineTool(Tool, ToolMarkerCanEdit, ToolMarkerOptional):
    """
    Inserts content at a given line in a file.
    """

    def apply(
        self,
        relative_path: str,
        line: int,
        content: str,
    ) -> str:
        """
        Inserts the given content at the given line in the file, pushing existing content of the line down.
        In general, symbolic insert operations like insert_after_symbol or insert_before_symbol should be preferred if you know which
        symbol you are looking for.
        However, this can also be useful for small targeted edits of the body of a longer symbol (without replacing the entire body).

        :param relative_path: the relative path to the file
        :param line: the 0-based index of the line to insert content at
        :param content: the content to be inserted
        """
        if not content.endswith("\n"):
            content += "\n"
        code_editor = self.create_code_editor()
        code_editor.insert_at_line(relative_path, line, content)
        return SUCCESS_RESULT


class SearchForPatternTool(Tool):
    """
    Performs a search for a pattern in the project.
    """

    def apply(
        self,
        substring_pattern: str,
        context_lines_before: int = 0,
        context_lines_after: int = 0,
        paths_include_glob: str = "",
        paths_exclude_glob: str = "",
        relative_path: str = "",
        restrict_search_to_code_files: bool = False,
        exclude_generated: bool | None = None,  # DEPRECATED - use search_scope
        search_scope: Literal["all", "source", "custom"] = "source",
        max_answer_chars: int = -1,
        result_format: Literal["summary", "detailed"] | None = None,
        output_mode: str | None = None,
    ) -> str:
        """
        Offers a flexible search for arbitrary patterns in the codebase, including the
        possibility to search in non-code files.
        Generally, symbolic operations like find_symbol or find_referencing_symbols
        should be preferred if you know which symbols you are looking for.

        Pattern Matching Logic:
            For each match, the returned result will contain the full lines where the
            substring pattern is found, as well as optionally some lines before and after it. The pattern will be compiled with
            DOTALL, meaning that the dot will match all characters including newlines.
            This also means that it never makes sense to have .* at the beginning or end of the pattern,
            but it may make sense to have it in the middle for complex patterns.
            If a pattern matches multiple lines, all those lines will be part of the match.
            Be careful to not use greedy quantifiers unnecessarily, it is usually better to use non-greedy quantifiers like .*? to avoid
            matching too much content.

        File Selection Logic:
            The files in which the search is performed can be restricted very flexibly.
            Using `restrict_search_to_code_files` is useful if you are only interested in code symbols (i.e., those
            symbols that can be manipulated with symbolic tools like find_symbol).
            You can also restrict the search to a specific file or directory,
            and provide glob patterns to include or exclude certain files on top of that.
            The globs are matched against relative file paths from the project root (not to the `relative_path` parameter that
            is used to further restrict the search).
            Smartly combining the various restrictions allows you to perform very targeted searches.


        :param substring_pattern: Regular expression for a substring pattern to search for
        :param context_lines_before: Number of lines of context to include before each match
        :param context_lines_after: Number of lines of context to include after each match
        :param paths_include_glob: optional glob pattern specifying files to include in the search.
            Matches against relative file paths from the project root (e.g., "*.py", "src/**/*.ts").
            Only matches files, not directories. If left empty, all non-ignored files will be included.
        :param paths_exclude_glob: optional glob pattern specifying files to exclude from the search.
            Matches against relative file paths from the project root (e.g., "*test*", "**/*_generated.py").
            Takes precedence over paths_include_glob. Only matches files, not directories. If left empty, no files are excluded.
        :param relative_path: only subpaths of this path (relative to the repo root) will be analyzed. If a path to a single
            file is passed, only that will be searched. The path must exist, otherwise a `FileNotFoundError` is raised.
        :param max_answer_chars: if the output is longer than this number of characters,
            no content will be returned.
            -1 means the default value from the config will be used.
            Don't adjust unless there is really no other way to get the content
            required for the task. Instead, if the output is too long, you should
            make a stricter query.
        :param restrict_search_to_code_files: whether to restrict the search to only those files where
            analyzed code symbols can be found. Otherwise, will search all non-ignored files.
            Set this to True if your search is only meant to discover code that can be manipulated with symbolic tools.
            For example, for finding classes or methods from a name pattern.
            Setting to False is a better choice if you also want to search in non-code files, like in html or yaml files,
            which is why it is the default.
        :param search_scope: Controls which files to search. Options:
            - "source" (default): Exclude common generated/vendor patterns (node_modules, __pycache__, migrations,
              dist, build, .venv, venv, target, .next, .nuxt, vendor, .git, .pytest_cache, .mypy_cache,
              coverage, htmlcov, wheelhouse, *.egg-info)
            - "all": Include all files (no exclusions)
            - "custom": Use custom patterns from config (future feature)

            Default is "source" which is what agents want 95% of the time. Use "all" to explicitly search everything.
            When files are excluded, response includes exclusion metadata showing what was filtered.
        :param exclude_generated: [DEPRECATED] Use search_scope instead. If provided, overrides search_scope.
            This parameter will be removed in version 2.0.0.
            - exclude_generated=True maps to search_scope="source"
            - exclude_generated=False maps to search_scope="all"
        :param result_format: Controls the level of detail in the output. Options:
            - "summary": Returns counts by file and first 10 matches (60-80% token savings, DEFAULT)
            - "detailed": Returns all matches with full context (explicit opt-in for complete results)
            Default is "summary" for optimal token efficiency. Use "detailed" when you need full match context.
        :param output_mode: DEPRECATED. Use result_format instead. This parameter is maintained for backward
            compatibility but will be removed in v2.0.0. If provided, shows deprecation warning.
        :return: A mapping of file paths to lists of matched consecutive lines (detailed mode),
                 or a JSON summary with counts and preview (summary mode).
        """
        abs_path = os.path.join(self.get_project_root(), relative_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Relative path {relative_path} does not exist.")

        # Handle parameter deprecation and resolution
        deprecation_warnings = []
        actual_result_format = result_format

        # Priority: result_format > output_mode > default
        if result_format is not None:
            # New parameter takes precedence
            actual_result_format = result_format
        elif output_mode is not None:
            # Deprecated parameter provided
            actual_result_format = output_mode  # type: ignore
            deprecation_warnings.append({
                "parameter": "output_mode",
                "replacement": "result_format",
                "removal_version": "2.0.0",
                "migration": f"Use result_format='{output_mode}' instead of output_mode='{output_mode}'"
            })
        else:
            # Use new default: "summary"
            actual_result_format = "summary"

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

        if restrict_search_to_code_files:
            matches = self.project.search_source_files_for_pattern(
                pattern=substring_pattern,
                relative_path=relative_path,
                context_lines_before=context_lines_before,
                context_lines_after=context_lines_after,
                paths_include_glob=paths_include_glob.strip(),
                paths_exclude_glob=paths_exclude_glob.strip(),
            )
        else:
            if os.path.isfile(abs_path):
                rel_paths_to_search = [relative_path]
            else:
                dirs, rel_paths_to_search = scan_directory(
                    path=abs_path,
                    recursive=True,
                    is_ignored_dir=self.project.is_ignored_path,
                    is_ignored_file=self.project.is_ignored_path,
                    relative_to=self.get_project_root(),
                )
            # TODO (maybe): not super efficient to walk through the files again and filter if glob patterns are provided
            #   but it probably never matters and this version required no further refactoring
            matches = search_files(
                rel_paths_to_search,
                substring_pattern,
                root_path=self.get_project_root(),
                paths_include_glob=paths_include_glob,
                paths_exclude_glob=paths_exclude_glob,
            )
        
        # Group matches by file
        file_to_matches: dict[str, list[str]] = defaultdict(list)
        for match in matches:
            assert match.source_file_path is not None
            file_to_matches[match.source_file_path].append(match.to_display_string())

        # Apply search scope filtering
        exclusion_metadata = None
        if effective_search_scope == "source":
            from serena.util.file_system import exclude_generated_code

            file_paths = list(file_to_matches.keys())
            exclusion_result = exclude_generated_code([], file_paths, self.get_project_root())
            included_files_set = set(exclusion_result.included_files)

            # Filter matches - only keep those from included files
            filtered_matches = {
                file_path: match_list
                for file_path, match_list in file_to_matches.items()
                if file_path in included_files_set
            }
            file_to_matches = filtered_matches

            # Prepare exclusion metadata
            if exclusion_result.excluded_counts:
                exclusion_metadata = {
                    "excluded_files": exclusion_result.excluded_counts,
                    "excluded_patterns": exclusion_result.excluded_patterns,
                    "total_excluded": sum(exclusion_result.excluded_counts.values()),
                    "include_excluded_instruction": "Use search_scope='all' to include all files"
                }

        # Handle result format
        if actual_result_format == "summary":
            summary = self._generate_summary_output(file_to_matches, substring_pattern, max_answer_chars)
            summary_dict = json.loads(summary)

            # Add exclusion metadata if present
            if exclusion_metadata:
                summary_dict["_excluded"] = exclusion_metadata

            # Add deprecation warnings if any deprecated parameters were used
            if deprecation_warnings:
                summary_dict["_deprecated"] = deprecation_warnings

            return json.dumps(summary_dict, indent=2)
        else:
            # Detailed mode
            result_dict = file_to_matches.copy()

            # Add exclusion metadata if present
            if exclusion_metadata:
                result_dict["_excluded"] = exclusion_metadata

            # Add deprecation warnings if any deprecated parameters were used
            if deprecation_warnings:
                result_dict["_deprecated"] = deprecation_warnings

            result = json.dumps(result_dict)
            return self._limit_length(result, max_answer_chars)
    
    def _generate_summary_output(
        self, 
        file_to_matches: dict[str, list[str]], 
        pattern: str,
        max_answer_chars: int
    ) -> str:
        """
        Generate a summary view of search results with counts and preview.
        
        Returns:
        - Total match count
        - Counts by file
        - Preview of first 10 matches
        - Instructions for getting full results
        """
        # Count total matches
        total_matches = sum(len(matches) for matches in file_to_matches.values())
        
        # Count matches per file
        by_file = {file: len(matches) for file, matches in file_to_matches.items()}
        
        # Sort files by match count (descending)
        sorted_files = sorted(by_file.items(), key=lambda x: x[1], reverse=True)
        
        # Take preview of first 10 matches
        preview = []
        match_count = 0
        for file_path, matches in file_to_matches.items():
            for match_str in matches:
                if match_count >= 10:
                    break
                # Extract first line of match for preview
                first_line = match_str.split('\n')[0] if '\n' in match_str else match_str
                preview.append({
                    "file": file_path,
                    "snippet": first_line[:150]  # Limit snippet length
                })
                match_count += 1
            if match_count >= 10:
                break
        
        # Build summary output
        summary = {
            "_schema": "search_summary_v1",
            "pattern": pattern,
            "total_matches": total_matches,
            "by_file": dict(sorted_files[:20]),  # Limit to top 20 files
            "preview": preview,
            "result_format": "summary"
        }
        
        # Add hint if there are more files
        if len(sorted_files) > 20:
            remaining_files = len(sorted_files) - 20
            remaining_matches = sum(count for _, count in sorted_files[20:])
            summary["additional_files"] = {
                "count": remaining_files,
                "matches": remaining_matches
            }
        
        # Add expansion hint if there are more results available
        if total_matches > 10:
            summary["_expansion_hint"] = (
                f"Use result_format='detailed' to see all {total_matches} matches with full context"
            )

        # Add token estimates
        # Estimate: preview is ~10 matches, detailed would be all matches
        # Rough estimate: each match in preview ~100 chars, detailed ~300 chars per match
        preview_tokens = min(10, total_matches) * 25  # ~100 chars / 4 = 25 tokens
        detailed_tokens = total_matches * 75  # ~300 chars / 4 = 75 tokens
        summary["_token_estimate"] = {
            "current": preview_tokens,
            "detailed": detailed_tokens,
            "savings_pct": int((1 - preview_tokens / max(detailed_tokens, 1)) * 100) if detailed_tokens > 0 else 0
        }

        result = json.dumps(summary, indent=2)
        return self._limit_length(result, max_answer_chars)
