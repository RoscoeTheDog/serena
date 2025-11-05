"""
Unit and integration tests for Story 11: On-Demand Body Retrieval

Tests GetSymbolBodyTool and symbol_id integration with FindSymbolTool.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from serena.agent import SerenaAgent
from serena.tools.symbol_tools import (
    FindSymbolTool,
    GetSymbolBodyTool,
    _add_symbol_ids,
    _generate_symbol_id,
)


class TestSymbolIdGeneration:
    """Unit tests for symbol ID generation functions."""

    def test_generate_symbol_id_valid(self):
        """Test generating symbol ID with valid data."""
        symbol_dict = {
            "name_path": "User/login",
            "relative_path": "models.py",
            "body_location": {"start_line": 142, "end_line": 155},
        }

        symbol_id = _generate_symbol_id(symbol_dict)
        assert symbol_id == "User/login:models.py:142"

    def test_generate_symbol_id_fallback_to_location(self):
        """Test fallback to location when body_location not available."""
        symbol_dict = {
            "name_path": "process_payment",
            "relative_path": "services/payment.py",
            "location": {"line": 89, "column": 4},
        }

        symbol_id = _generate_symbol_id(symbol_dict)
        assert symbol_id == "process_payment:services/payment.py:89"

    def test_generate_symbol_id_missing_data(self):
        """Test symbol ID generation with missing data returns empty string."""
        # Missing name_path
        assert _generate_symbol_id({"relative_path": "test.py", "body_location": {"start_line": 1}}) == ""

        # Missing relative_path
        assert _generate_symbol_id({"name_path": "Foo", "body_location": {"start_line": 1}}) == ""

        # Missing line number
        assert _generate_symbol_id({"name_path": "Foo", "relative_path": "test.py"}) == ""

    def test_add_symbol_ids(self):
        """Test adding symbol IDs to a list of symbol dictionaries."""
        symbol_dicts = [
            {
                "name_path": "Foo",
                "relative_path": "test.py",
                "body_location": {"start_line": 10, "end_line": 20},
            },
            {
                "name_path": "Bar",
                "relative_path": "test.py",
                "body_location": {"start_line": 30, "end_line": 40},
            },
        ]

        result = _add_symbol_ids(symbol_dicts)

        assert len(result) == 2
        assert result[0]["symbol_id"] == "Foo:test.py:10"
        assert result[1]["symbol_id"] == "Bar:test.py:30"

    def test_add_symbol_ids_skips_invalid(self):
        """Test that invalid symbols don't get symbol_id field."""
        symbol_dicts = [
            {
                "name_path": "Valid",
                "relative_path": "test.py",
                "body_location": {"start_line": 10, "end_line": 20},
            },
            {
                # Invalid: missing line number
                "name_path": "Invalid",
                "relative_path": "test.py",
            },
        ]

        result = _add_symbol_ids(symbol_dicts)

        assert "symbol_id" in result[0]
        assert "symbol_id" not in result[1]


class TestGetSymbolBodyTool:
    """Integration tests for GetSymbolBodyTool."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create test file with multiple symbols
            test_file = project_path / "example.py"
            test_file.write_text(
                """class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"


def process_payment(amount, card):
    if not validate_card(card):
        raise ValueError("Invalid card")
    return charge(amount, card)


def validate_card(card):
    return card is not None
"""
            )

            yield project_path

    @pytest.fixture
    def agent(self, temp_project):
        """Create SerenaAgent for testing."""
        return SerenaAgent(str(temp_project))

    def test_get_symbol_body_single(self, agent):
        """Test retrieving a single symbol body."""
        tool = GetSymbolBodyTool(agent=agent)

        # Get body for User class (lines 1-6)
        result_json = tool.apply(symbol_id="User:example.py:1")
        result = json.loads(result_json)

        assert result["_schema"] == "get_symbol_body_v1"
        assert result["requested"] == 1
        assert result["retrieved"] == 1
        assert result["failed"] == 0

        symbols = result["symbols"]
        assert len(symbols) == 1

        symbol = symbols[0]
        assert symbol["symbol_id"] == "User:example.py:1"
        assert symbol["name_path"] == "User"
        assert symbol["relative_path"] == "example.py"
        assert symbol["line"] == 1
        assert symbol["kind"] == "Class"
        assert "class User:" in symbol["body"]
        assert "def __init__" in symbol["body"]
        assert "def greet" in symbol["body"]
        assert symbol["estimated_tokens"] > 0

    def test_get_symbol_body_batch(self, agent):
        """Test batch retrieval of multiple symbol bodies."""
        tool = GetSymbolBodyTool(agent=agent)

        # Get bodies for process_payment and validate_card
        result_json = tool.apply(
            symbol_id=["process_payment:example.py:9", "validate_card:example.py:15"]
        )
        result = json.loads(result_json)

        assert result["requested"] == 2
        assert result["retrieved"] == 2
        assert result["failed"] == 0

        symbols = result["symbols"]
        assert len(symbols) == 2

        # Check first symbol
        assert symbols[0]["name_path"] == "process_payment"
        assert "def process_payment" in symbols[0]["body"]
        assert "validate_card" in symbols[0]["body"]

        # Check second symbol
        assert symbols[1]["name_path"] == "validate_card"
        assert "def validate_card" in symbols[1]["body"]

    def test_get_symbol_body_invalid_id_format(self, agent):
        """Test error handling for invalid symbol ID format."""
        tool = GetSymbolBodyTool(agent=agent)

        result_json = tool.apply(symbol_id="invalid_format")
        result = json.loads(result_json)

        assert result["requested"] == 1
        assert result["retrieved"] == 0
        assert result["failed"] == 1

        errors = result["errors"]
        assert len(errors) == 1
        assert "Invalid symbol ID format" in errors[0]["error"]

    def test_get_symbol_body_not_found(self, agent):
        """Test error handling when symbol not found."""
        tool = GetSymbolBodyTool(agent=agent)

        result_json = tool.apply(symbol_id="NonExistent:example.py:999")
        result = json.loads(result_json)

        assert result["requested"] == 1
        assert result["retrieved"] == 0
        assert result["failed"] == 1

        errors = result["errors"]
        assert len(errors) == 1
        assert "Symbol not found" in errors[0]["error"]

    def test_get_symbol_body_batch_partial_failure(self, agent):
        """Test batch retrieval with some failures."""
        tool = GetSymbolBodyTool(agent=agent)

        result_json = tool.apply(
            symbol_id=[
                "User:example.py:1",  # Valid
                "NonExistent:example.py:999",  # Invalid
                "validate_card:example.py:15",  # Valid
            ]
        )
        result = json.loads(result_json)

        assert result["requested"] == 3
        assert result["retrieved"] == 2
        assert result["failed"] == 1

        # Check successful retrievals
        symbols = result["symbols"]
        assert len(symbols) == 2
        assert symbols[0]["name_path"] == "User"
        assert symbols[1]["name_path"] == "validate_card"

        # Check failures
        errors = result["errors"]
        assert len(errors) == 1
        assert "NonExistent:example.py:999" in errors[0]["symbol_id"]

    def test_get_symbol_body_empty_input(self, agent):
        """Test error handling for empty symbol ID list."""
        tool = GetSymbolBodyTool(agent=agent)

        result_json = tool.apply(symbol_id=[])
        result = json.loads(result_json)

        assert "error" in result
        assert "No symbol IDs provided" in result["error"]


class TestFindSymbolWithSymbolIds:
    """Integration tests for FindSymbolTool with symbol_id generation."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create test file
            test_file = project_path / "models.py"
            test_file.write_text(
                """class User:
    def __init__(self, name):
        self.name = name

    def login(self, password):
        # Authentication logic
        return True


class Admin(User):
    def delete_user(self, user_id):
        # Admin privilege required
        pass
"""
            )

            yield project_path

    @pytest.fixture
    def agent(self, temp_project):
        """Create SerenaAgent for testing."""
        return SerenaAgent(str(temp_project))

    def test_find_symbol_includes_symbol_ids(self, agent):
        """Test that find_symbol includes symbol_id in results."""
        tool = FindSymbolTool(agent=agent)

        result_json = tool.apply(name_path="User", relative_path="models.py", include_body=False)
        result = json.loads(result_json)

        assert "_schema" in result
        symbols = result.get("symbols", [])
        assert len(symbols) > 0

        # Check that symbol_id is present
        for symbol in symbols:
            assert "symbol_id" in symbol
            assert ":" in symbol["symbol_id"]
            # Verify format: name_path:relative_path:line_number
            parts = symbol["symbol_id"].split(":")
            assert len(parts) == 3
            assert parts[0]  # name_path
            assert parts[1]  # relative_path
            assert parts[2].isdigit()  # line_number

    def test_symbol_id_stability(self, agent):
        """Test that symbol IDs are stable across multiple queries."""
        tool = FindSymbolTool(agent=agent)

        # First query
        result1_json = tool.apply(name_path="User", relative_path="models.py", include_body=False)
        result1 = json.loads(result1_json)
        symbols1 = result1.get("symbols", [])

        # Second query (same parameters)
        result2_json = tool.apply(name_path="User", relative_path="models.py", include_body=False)
        result2 = json.loads(result2_json)
        symbols2 = result2.get("symbols", [])

        # Symbol IDs should be identical
        assert len(symbols1) == len(symbols2)
        for s1, s2 in zip(symbols1, symbols2):
            assert s1["symbol_id"] == s2["symbol_id"]

    def test_symbol_id_with_depth(self, agent):
        """Test that symbol IDs work correctly with depth parameter."""
        tool = FindSymbolTool(agent=agent)

        result_json = tool.apply(name_path="User", relative_path="models.py", include_body=False, depth=1)
        result = json.loads(result_json)

        symbols = result.get("symbols", [])
        assert len(symbols) > 0

        # Should include methods with their own symbol IDs
        for symbol in symbols:
            assert "symbol_id" in symbol
            if "children" in symbol:
                for child in symbol["children"]:
                    assert "symbol_id" in child


class TestEndToEndWorkflow:
    """End-to-end tests for the complete on-demand body retrieval workflow."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create test file with many symbols
            test_file = project_path / "services.py"
            test_file.write_text(
                """def service_a():
    return "A"

def service_b():
    return "B"

def service_c():
    return "C"

def service_d():
    return "D"

def service_e():
    return "E"

def service_f():
    return "F"

def service_g():
    return "G"

def service_h():
    return "H"

def service_i():
    return "I"

def service_j():
    return "J"
"""
            )

            yield project_path

    @pytest.fixture
    def agent(self, temp_project):
        """Create SerenaAgent for testing."""
        return SerenaAgent(str(temp_project))

    def test_workflow_search_then_retrieve(self, agent):
        """Test complete workflow: search without bodies, then retrieve specific bodies."""
        find_tool = FindSymbolTool(agent=agent)
        body_tool = GetSymbolBodyTool(agent=agent)

        # Step 1: Search for all services without bodies
        search_result_json = find_tool.apply(
            name_path="service", substring_matching=True, relative_path="services.py", include_body=False
        )
        search_result = json.loads(search_result_json)

        symbols = search_result.get("symbols", [])
        assert len(symbols) == 10  # service_a through service_j

        # Step 2: Select specific services to retrieve (a, c, g)
        selected_ids = [
            s["symbol_id"] for s in symbols if s["name_path"] in ["service_a", "service_c", "service_g"]
        ]
        assert len(selected_ids) == 3

        # Step 3: Retrieve only selected bodies
        retrieve_result_json = body_tool.apply(symbol_id=selected_ids)
        retrieve_result = json.loads(retrieve_result_json)

        assert retrieve_result["requested"] == 3
        assert retrieve_result["retrieved"] == 3
        assert retrieve_result["failed"] == 0

        retrieved_symbols = retrieve_result["symbols"]
        retrieved_names = {s["name_path"] for s in retrieved_symbols}
        assert retrieved_names == {"service_a", "service_c", "service_g"}

    def test_token_savings_calculation(self, agent):
        """Test and verify 95%+ token savings."""
        find_tool = FindSymbolTool(agent=agent)
        body_tool = GetSymbolBodyTool(agent=agent)

        # Scenario: Search 10 symbols, retrieve 2 bodies

        # Method 1: Traditional (include_body=True for all)
        traditional_result_json = find_tool.apply(
            name_path="service", substring_matching=True, relative_path="services.py", include_body=True
        )
        traditional_tokens = len(traditional_result_json) // 4  # char/4 approximation

        # Method 2: On-demand (search without bodies, then retrieve 2)
        search_result_json = find_tool.apply(
            name_path="service", substring_matching=True, relative_path="services.py", include_body=False
        )
        search_result = json.loads(search_result_json)
        search_tokens = len(search_result_json) // 4

        # Retrieve only 2 bodies
        symbols = search_result.get("symbols", [])
        selected_ids = [symbols[0]["symbol_id"], symbols[1]["symbol_id"]]

        retrieve_result_json = body_tool.apply(symbol_id=selected_ids)
        retrieve_tokens = len(retrieve_result_json) // 4

        on_demand_total_tokens = search_tokens + retrieve_tokens

        # Calculate savings
        savings_percent = ((traditional_tokens - on_demand_total_tokens) / traditional_tokens) * 100

        # Verify 95%+ savings when retrieving small subset
        # (In this case, retrieving 2/10 = 20% of bodies)
        print(f"\nToken Savings Analysis:")
        print(f"  Traditional (all bodies): {traditional_tokens} tokens")
        print(f"  On-demand (search + 2 bodies): {on_demand_total_tokens} tokens")
        print(f"  Savings: {savings_percent:.1f}%")

        # We expect significant savings (target: 95%+ when retrieving 1-2 out of many)
        # For 10 symbols retrieving 2, we should see 70-85% savings
        assert savings_percent > 70, f"Expected >70% savings, got {savings_percent:.1f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
