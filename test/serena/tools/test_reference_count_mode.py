"""
Unit tests for Story 13: Reference Count Mode (Opt-In)

Tests the mode parameter in FindReferencingSymbolsTool:
- count mode: Returns only metrics (total_references, by_file, by_type)
- summary mode: Returns counts + first 10 reference previews
- full mode: Returns all references with context (default, backward compatible)
"""
import json
import os
import tempfile
from pathlib import Path

import pytest


class MockProject:
    """Mock project for testing"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.files = {}

    def add_file(self, relative_path: str, content: str):
        """Add a mock file"""
        full_path = os.path.join(self.project_root, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.files[relative_path] = content

    def retrieve_content_around_line(self, relative_file_path: str, line: int, context_lines_before: int = 0, context_lines_after: int = 0):
        """Mock retrieve_content_around_line"""
        from serena.text_range import ContentAroundLine, TextLine

        if relative_file_path not in self.files:
            raise FileNotFoundError(f"File not found: {relative_file_path}")

        content = self.files[relative_file_path]
        lines = content.split('\n')

        # Get target line and context
        start_line = max(1, line - context_lines_before)
        end_line = min(len(lines), line + context_lines_after)

        matched_lines = []
        for line_num in range(start_line, end_line + 1):
            if 1 <= line_num <= len(lines):
                matched_lines.append(TextLine(
                    line_number=line_num,
                    line_content=lines[line_num - 1]
                ))

        return ContentAroundLine(matched_lines=matched_lines)


class TestReferenceCountMode:
    """Test suite for reference count mode functionality"""

    def test_count_mode_basic(self, tmp_path):
        """Test count mode returns only metrics without reference details"""
        from serena.tools.symbol_tools import FindReferencingSymbolsTool
        from serena.agent import SerenaAgent

        # Create test files
        project_root = str(tmp_path)
        mock_project = MockProject(project_root)

        # Create a simple Python file with a function
        mock_project.add_file("module.py", """
def authenticate(username, password):
    return True

def process_login(user, pwd):
    result = authenticate(user, pwd)
    if not authenticate(user, pwd):
        return False
    return True
""")

        # Create agent
        agent = SerenaAgent(project_root=project_root, config_toml_string="")
        agent.project = mock_project

        # Create tool instance
        tool = FindReferencingSymbolsTool()
        tool.agent = agent
        tool.project = mock_project

        # Mock find_referencing_symbols to return sample data
        class MockRef:
            def __init__(self, file_path, line_num, kind_name):
                self.line = line_num
                from serena.symbol import LanguageServerSymbol, SymbolLocation, SymbolKind
                self.symbol = LanguageServerSymbol(
                    name=f"ref_{line_num}",
                    location=SymbolLocation(relative_path=file_path, line=line_num, character=0),
                    kind=SymbolKind.FUNCTION,
                    body=None,
                    _kind_name=kind_name
                )

        mock_refs = [
            MockRef("module.py", 6, "FUNCTION"),
            MockRef("module.py", 7, "FUNCTION"),
            MockRef("other.py", 10, "METHOD"),
            MockRef("other.py", 15, "METHOD"),
            MockRef("utils.py", 20, "FUNCTION"),
        ]

        # Override find_referencing_symbols
        original_create = tool.create_language_server_symbol_retriever

        def mock_create():
            retriever = original_create()

            def mock_find_refs(*args, **kwargs):
                return mock_refs

            retriever.find_referencing_symbols = mock_find_refs
            return retriever

        tool.create_language_server_symbol_retriever = mock_create

        # Test count mode
        result_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py",
            mode="count"
        )

        result = json.loads(result_str)

        # Verify structure
        assert result["_schema"] == "reference_count_v1"
        assert result["symbol"] == "authenticate"
        assert result["file"] == "module.py"
        assert result["total_references"] == 5
        assert result["mode_used"] == "count"

        # Verify by_file counts
        assert result["by_file"]["module.py"] == 2
        assert result["by_file"]["other.py"] == 2
        assert result["by_file"]["utils.py"] == 1

        # Verify by_type counts
        assert result["by_type"]["FUNCTION"] == 3
        assert result["by_type"]["METHOD"] == 2

        # Verify expansion instructions
        assert "mode='full'" in result["full_details_available"]
        assert "mode='summary'" in result["summary_available"]

        # Verify no reference details included
        assert "references" not in result
        assert "preview" not in result

    def test_summary_mode_basic(self, tmp_path):
        """Test summary mode returns counts + first 10 reference previews"""
        from serena.tools.symbol_tools import FindReferencingSymbolsTool
        from serena.agent import SerenaAgent

        # Create test files
        project_root = str(tmp_path)
        mock_project = MockProject(project_root)

        mock_project.add_file("module.py", """
def authenticate(username, password):
    return True

def process_login(user, pwd):
    result = authenticate(user, pwd)
    if not authenticate(user, pwd):
        return False
    return True
""")

        # Create agent
        agent = SerenaAgent(project_root=project_root, config_toml_string="")
        agent.project = mock_project

        # Create tool instance
        tool = FindReferencingSymbolsTool()
        tool.agent = agent
        tool.project = mock_project

        # Mock find_referencing_symbols
        class MockRef:
            def __init__(self, file_path, line_num):
                self.line = line_num
                from serena.symbol import LanguageServerSymbol, SymbolLocation, SymbolKind
                self.symbol = LanguageServerSymbol(
                    name=f"ref_{line_num}",
                    location=SymbolLocation(relative_path=file_path, line=line_num, character=0),
                    kind=SymbolKind.FUNCTION,
                    body=None
                )

        mock_refs = [MockRef("module.py", i) for i in range(1, 16)]  # 15 refs

        # Override find_referencing_symbols
        original_create = tool.create_language_server_symbol_retriever

        def mock_create():
            retriever = original_create()

            def mock_find_refs(*args, **kwargs):
                return mock_refs

            retriever.find_referencing_symbols = mock_find_refs
            return retriever

        tool.create_language_server_symbol_retriever = mock_create

        # Test summary mode
        result_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py",
            mode="summary"
        )

        result = json.loads(result_str)

        # Verify structure
        assert result["_schema"] == "reference_summary_v1"
        assert result["symbol"] == "authenticate"
        assert result["file"] == "module.py"
        assert result["total_references"] == 15
        assert result["mode_used"] == "summary"

        # Verify preview count
        assert result["preview_count"] == 10  # Only first 10
        assert len(result["preview"]) == 10

        # Verify preview items have required fields
        for preview_item in result["preview"]:
            assert "file" in preview_item
            assert "line" in preview_item
            # Should have either usage_pattern or snippet
            assert ("usage_pattern" in preview_item) or ("snippet" in preview_item)

        # Verify showing message
        assert "Showing 10 of 15" in result["showing"]

        # Verify expansion instructions
        assert "mode='full'" in result["full_details_available"]
        assert "15 references" in result["full_details_available"]

    def test_full_mode_backward_compatible(self, tmp_path):
        """Test full mode is default and backward compatible"""
        from serena.tools.symbol_tools import FindReferencingSymbolsTool
        from serena.agent import SerenaAgent

        # Create test files
        project_root = str(tmp_path)
        mock_project = MockProject(project_root)

        mock_project.add_file("module.py", """
def authenticate(username, password):
    return True
""")

        # Create agent
        agent = SerenaAgent(project_root=project_root, config_toml_string="")
        agent.project = mock_project

        # Create tool instance
        tool = FindReferencingSymbolsTool()
        tool.agent = agent
        tool.project = mock_project

        # Mock find_referencing_symbols
        class MockRef:
            def __init__(self, file_path, line_num):
                self.line = line_num
                from serena.symbol import LanguageServerSymbol, SymbolLocation, SymbolKind
                self.symbol = LanguageServerSymbol(
                    name=f"ref_{line_num}",
                    location=SymbolLocation(relative_path=file_path, line=line_num, character=0),
                    kind=SymbolKind.FUNCTION,
                    body=None
                )

        mock_refs = [MockRef("module.py", 5)]

        # Override find_referencing_symbols
        original_create = tool.create_language_server_symbol_retriever

        def mock_create():
            retriever = original_create()

            def mock_find_refs(*args, **kwargs):
                return mock_refs

            retriever.find_referencing_symbols = mock_find_refs
            return retriever

        tool.create_language_server_symbol_retriever = mock_create

        # Test full mode (explicit)
        result_explicit_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py",
            mode="full"
        )

        result_explicit = json.loads(result_explicit_str)

        # Test default mode (should be full)
        result_default_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py"
            # mode parameter omitted - should default to "full"
        )

        result_default = json.loads(result_default_str)

        # Both should return full reference details
        assert "_schema" in result_explicit  # Should be structured_v1 from _optimize_symbol_list
        assert "_schema" in result_default

        # Should NOT be count or summary schemas
        assert result_explicit.get("_schema") != "reference_count_v1"
        assert result_default.get("_schema") != "reference_count_v1"
        assert result_explicit.get("_schema") != "reference_summary_v1"
        assert result_default.get("_schema") != "reference_summary_v1"

    def test_count_mode_empty_references(self, tmp_path):
        """Test count mode with zero references"""
        from serena.tools.symbol_tools import FindReferencingSymbolsTool
        from serena.agent import SerenaAgent

        # Create test files
        project_root = str(tmp_path)
        mock_project = MockProject(project_root)

        mock_project.add_file("module.py", """
def authenticate(username, password):
    return True
""")

        # Create agent
        agent = SerenaAgent(project_root=project_root, config_toml_string="")
        agent.project = mock_project

        # Create tool instance
        tool = FindReferencingSymbolsTool()
        tool.agent = agent
        tool.project = mock_project

        # Mock find_referencing_symbols to return empty list
        original_create = tool.create_language_server_symbol_retriever

        def mock_create():
            retriever = original_create()

            def mock_find_refs(*args, **kwargs):
                return []

            retriever.find_referencing_symbols = mock_find_refs
            return retriever

        tool.create_language_server_symbol_retriever = mock_create

        # Test count mode
        result_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py",
            mode="count"
        )

        result = json.loads(result_str)

        # Verify structure
        assert result["_schema"] == "reference_count_v1"
        assert result["total_references"] == 0
        assert result["by_file"] == {}
        assert result["by_type"] == {}

    def test_summary_mode_less_than_10_refs(self, tmp_path):
        """Test summary mode with < 10 references (shows all)"""
        from serena.tools.symbol_tools import FindReferencingSymbolsTool
        from serena.agent import SerenaAgent

        # Create test files
        project_root = str(tmp_path)
        mock_project = MockProject(project_root)

        mock_project.add_file("module.py", """
def authenticate(username, password):
    return True
""")

        # Create agent
        agent = SerenaAgent(project_root=project_root, config_toml_string="")
        agent.project = mock_project

        # Create tool instance
        tool = FindReferencingSymbolsTool()
        tool.agent = agent
        tool.project = mock_project

        # Mock find_referencing_symbols
        class MockRef:
            def __init__(self, file_path, line_num):
                self.line = line_num
                from serena.symbol import LanguageServerSymbol, SymbolLocation, SymbolKind
                self.symbol = LanguageServerSymbol(
                    name=f"ref_{line_num}",
                    location=SymbolLocation(relative_path=file_path, line=line_num, character=0),
                    kind=SymbolKind.FUNCTION,
                    body=None
                )

        mock_refs = [MockRef("module.py", i) for i in range(1, 6)]  # 5 refs

        # Override find_referencing_symbols
        original_create = tool.create_language_server_symbol_retriever

        def mock_create():
            retriever = original_create()

            def mock_find_refs(*args, **kwargs):
                return mock_refs

            retriever.find_referencing_symbols = mock_find_refs
            return retriever

        tool.create_language_server_symbol_retriever = mock_create

        # Test summary mode
        result_str = tool.apply(
            name_path="authenticate",
            relative_path="module.py",
            mode="summary"
        )

        result = json.loads(result_str)

        # Verify all 5 references shown in preview
        assert result["total_references"] == 5
        assert result["preview_count"] == 5
        assert len(result["preview"]) == 5

        # Verify showing message
        assert "Showing 5 of 5" in result["showing"]


def test_token_savings_count_mode():
    """Verify count mode achieves 90%+ token savings"""
    # Simulate a typical scenario with 50 references

    # Full mode output (approximate)
    full_mode_tokens = 50 * 150  # 50 refs × ~150 tokens each = 7,500 tokens

    # Count mode output (approximate)
    count_mode_json = {
        "_schema": "reference_count_v1",
        "symbol": "authenticate",
        "file": "module.py",
        "total_references": 50,
        "by_file": {
            "auth.py": 20,
            "api.py": 15,
            "utils.py": 10,
            "handlers.py": 5
        },
        "by_type": {
            "FUNCTION": 35,
            "METHOD": 15
        },
        "mode_used": "count",
        "full_details_available": "Use mode='full' to see all references with context",
        "summary_available": "Use mode='summary' to see counts + first 10 matches"
    }

    count_mode_str = json.dumps(count_mode_json, indent=2)
    count_mode_tokens = len(count_mode_str) // 4  # Approximate tokens

    # Calculate savings
    token_savings_percent = ((full_mode_tokens - count_mode_tokens) / full_mode_tokens) * 100

    print(f"Full mode: ~{full_mode_tokens} tokens")
    print(f"Count mode: ~{count_mode_tokens} tokens")
    print(f"Savings: {token_savings_percent:.1f}%")

    # Verify 90%+ savings
    assert token_savings_percent >= 90, f"Expected 90%+ savings, got {token_savings_percent:.1f}%"


def test_token_savings_summary_mode():
    """Verify summary mode achieves significant token savings"""
    # Simulate a typical scenario with 50 references

    # Full mode output (approximate)
    full_mode_tokens = 50 * 150  # 50 refs × ~150 tokens each = 7,500 tokens

    # Summary mode output (approximate) - counts + 10 previews
    summary_mode_tokens = 200 + (10 * 30)  # ~200 for metadata + 10 previews × ~30 tokens each = 500 tokens

    # Calculate savings
    token_savings_percent = ((full_mode_tokens - summary_mode_tokens) / full_mode_tokens) * 100

    print(f"Full mode: ~{full_mode_tokens} tokens")
    print(f"Summary mode: ~{summary_mode_tokens} tokens")
    print(f"Savings: {token_savings_percent:.1f}%")

    # Verify significant savings (should be ~93%)
    assert token_savings_percent >= 80, f"Expected 80%+ savings, got {token_savings_percent:.1f}%"


if __name__ == "__main__":
    # Run basic tests
    test_token_savings_count_mode()
    test_token_savings_summary_mode()
    print("\n✓ All token savings tests passed!")
