import json
from typing import Literal

from serena.tools import ReplaceContentTool, Tool


class WriteMemoryTool(Tool):
    """
    Writes a named memory (for future reference) to Serena's project-specific memory store.
    """

    def apply(self, memory_name: str, content: str, max_answer_chars: int = -1) -> str:
        """
        Write some information about this project that can be useful for future tasks to a memory in md format.
        The memory name should be meaningful.
        """
        if max_answer_chars == -1:
            max_answer_chars = self.agent.serena_config.default_max_tool_answer_chars
        if len(content) > max_answer_chars:
            raise ValueError(
                f"Content for {memory_name} is too long. Max length is {max_answer_chars} characters. " + "Please make the content shorter."
            )

        return self.memories_manager.save_memory(memory_name, content)


class ReadMemoryTool(Tool):
    """
    Reads the memory with the given name from Serena's project-specific memory store.
    """

    def apply(self, memory_file_name: str, max_answer_chars: int = -1) -> str:
        """
        Read the content of a memory file. This tool should only be used if the information
        is relevant to the current task. You can infer whether the information
        is relevant from the memory file name.
        You should not read the same memory file multiple times in the same conversation.
        """
        return self.memories_manager.load_memory(memory_file_name)


class ListMemoriesTool(Tool):
    """
    Lists memories in Serena's project-specific memory store with optional metadata.
    """

    def apply(self, include_metadata: bool = True, preview_lines: int = 3) -> str:
        """
        List available memories with metadata (default). Any memory can be read using the `read_memory` tool.

        Args:
            include_metadata: If True, include size, last_modified, preview, estimated_tokens, and lines (default: True).
                Use include_metadata=False for just names (rare - only when you don't need to decide which to read).
            preview_lines: Number of lines to include in preview (default: 3, only used if include_metadata=True)

        Returns:
            JSON string containing either:
            - List of dicts with metadata (if include_metadata=True, default):
              {
                "name": str,
                "size_kb": float,
                "last_modified": str (Unix timestamp),
                "preview": str (first N lines),
                "estimated_tokens": int,
                "lines": int
              }
            - Simple list of memory names (if include_metadata=False)

        Example with metadata (default):
            [
              {
                "name": "authentication_flow",
                "size_kb": 12.5,
                "last_modified": "1704396000",
                "preview": "# Authentication Flow\\n\\nThe system uses JWT tokens...\\n... (142 more lines)",
                "estimated_tokens": 3200,
                "lines": 145
              }
            ]

        Example without metadata (rare):
            ["authentication_flow", "error_handling", "database_schema"]

        Token Savings (metadata mode):
        - Metadata mode: Preview + metadata (~200 tokens vs ~3000 for reading all files)
        - Savings: ~60-80% when used to decide which memories to read
        - Without metadata: Just names (~50 tokens for 10 memories) - use only when you already know which to read
        """
        result = self.memories_manager.list_memories(
            include_metadata=include_metadata,
            preview_lines=preview_lines
        )

        # Add token savings metadata when returning metadata
        if include_metadata and isinstance(result, list) and len(result) > 0:
            # Calculate total tokens if all memories were read
            total_tokens_if_read_all = sum(mem.get("estimated_tokens", 0) for mem in result)
            # Estimate current output tokens (metadata + previews)
            current_output = json.dumps(result, indent=2)
            current_tokens = len(current_output) // 4

            # Calculate savings
            savings_pct = 0
            if total_tokens_if_read_all > 0:
                savings_pct = round((1 - current_tokens / total_tokens_if_read_all) * 100)

            # Wrap result with metadata
            output = {
                "memories": result,
                "_token_savings": {
                    "current_output": current_tokens,
                    "if_read_all_files": total_tokens_if_read_all,
                    "savings_pct": savings_pct,
                    "note": "Use previews to decide which memories to read with read_memory tool"
                }
            }
            return json.dumps(output, indent=2)

        return json.dumps(result, indent=2 if include_metadata else None)


class DeleteMemoryTool(Tool):
    """
    Deletes a memory from Serena's project-specific memory store.
    """

    def apply(self, memory_file_name: str) -> str:
        """
        Delete a memory file. Should only happen if a user asks for it explicitly,
        for example by saying that the information retrieved from a memory file is no longer correct
        or no longer relevant for the project.
        """
        return self.memories_manager.delete_memory(memory_file_name)


class EditMemoryTool(Tool):
    """
    Edits a memory by replacing content matching a pattern.
    """

    def apply(
        self,
        memory_file_name: str,
        needle: str,
        repl: str,
        mode: Literal["literal", "regex"],
    ) -> str:
        r"""
        Replaces content matching a regular expression in a memory.

        :param memory_file_name: the name of the memory
        :param needle: the string or regex pattern to search for.
            If `mode` is "literal", this string will be matched exactly.
            If `mode` is "regex", this string will be treated as a regular expression (syntax of Python's `re` module,
            with flags DOTALL and MULTILINE enabled).
        :param repl: the replacement string (verbatim).
        :param mode: either "literal" or "regex", specifying how the `needle` parameter is to be interpreted.
        """
        replace_content_tool = self.agent.get_tool(ReplaceContentTool)
        rel_path = self.memories_manager.get_memory_file_path(memory_file_name).relative_to(self.get_project_root())
        return replace_content_tool.replace_content(str(rel_path), needle, repl, mode=mode)
