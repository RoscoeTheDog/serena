"""Tests for symbolic tool filtering when language server is not available."""

from serena.config.serena_config import ToolSet
from serena.tools import ToolRegistry
from serena.tools.symbol_tools import (
    FindReferencingSymbolsTool,
    FindSymbolTool,
    GetSymbolBodyTool,
    GetSymbolsOverviewTool,
    InsertAfterSymbolTool,
    InsertBeforeSymbolTool,
    ReplaceSymbolBodyTool,
)
from serena.tools.tools_base import (
    Tool,
    ToolMarkerSymbolicEdit,
    ToolMarkerSymbolicRead,
)


class TestIsSymbolic:
    """Test the is_symbolic() classmethod on Tool."""

    def test_symbolic_read_tools_are_symbolic(self):
        for tool_cls in [GetSymbolsOverviewTool, FindSymbolTool, FindReferencingSymbolsTool, GetSymbolBodyTool]:
            assert tool_cls.is_symbolic(), f"{tool_cls.__name__} should be symbolic"

    def test_symbolic_edit_tools_are_symbolic(self):
        for tool_cls in [ReplaceSymbolBodyTool, InsertAfterSymbolTool, InsertBeforeSymbolTool]:
            assert tool_cls.is_symbolic(), f"{tool_cls.__name__} should be symbolic"

    def test_non_symbolic_tools_are_not_symbolic(self):
        """Verify that tools not marked as symbolic return False."""
        registry = ToolRegistry()
        for tool_cls in registry.get_all_tool_classes():
            if not issubclass(tool_cls, (ToolMarkerSymbolicRead, ToolMarkerSymbolicEdit)):
                assert not tool_cls.is_symbolic(), f"{tool_cls.__name__} should not be symbolic"


class TestWithoutSymbolicTools:
    """Test ToolSet.without_symbolic_tools() method."""

    def test_removes_symbolic_tools(self):
        """Symbolic tools should be removed from the tool set."""
        tool_set = ToolSet.default()
        filtered = tool_set.without_symbolic_tools()
        filtered_names = filtered.get_tool_names()

        registry = ToolRegistry()
        for tool_cls in registry.get_all_tool_classes():
            name = tool_cls.get_name_from_cls()
            if tool_cls.is_symbolic() and name in tool_set.get_tool_names():
                assert name not in filtered_names, f"Symbolic tool {name} should have been removed"

    def test_keeps_non_symbolic_tools(self):
        """Non-symbolic tools should remain in the tool set."""
        tool_set = ToolSet.default()
        filtered = tool_set.without_symbolic_tools()
        filtered_names = filtered.get_tool_names()

        registry = ToolRegistry()
        for tool_cls in registry.get_all_tool_classes():
            name = tool_cls.get_name_from_cls()
            if not tool_cls.is_symbolic() and name in tool_set.get_tool_names():
                assert name in filtered_names, f"Non-symbolic tool {name} should be kept"

    def test_returns_new_toolset(self):
        """Should return a new ToolSet instance, not mutate the original."""
        tool_set = ToolSet.default()
        original_names = set(tool_set.get_tool_names())
        filtered = tool_set.without_symbolic_tools()
        assert tool_set.get_tool_names() == original_names, "Original ToolSet should not be mutated"
        assert filtered is not tool_set
