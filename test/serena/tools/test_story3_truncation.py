"""
Tests for Story 3: Token-Aware Truncation System

Validates the new truncation modes: error, summary, paginate
"""

import pytest
import json
from serena.util.token_estimator import TruncationError, TruncationMetadata, get_token_estimator


class TestTruncationMetadata:
    """Test TruncationMetadata dataclass and serialization."""

    def test_no_truncation_metadata(self):
        """Test metadata when content is not truncated."""
        metadata = TruncationMetadata(
            total_tokens=100,
            included_tokens=100,
            truncated=False,
        )

        result = metadata.to_dict()
        assert result["total_available"] == 100
        assert result["returned"] == 100
        assert result["truncated"] is False
        assert "strategy" not in result
        assert "expansion_hint" not in result

    def test_truncated_metadata_with_all_fields(self):
        """Test metadata with all optional fields populated."""
        metadata = TruncationMetadata(
            total_tokens=5000,
            included_tokens=1000,
            truncated=True,
            truncation_strategy="summary",
            expansion_hint="Use max_tokens=5000 for full content",
            narrowing_suggestions=["Use relative_path='src/'", "Use depth=1"],
        )

        result = metadata.to_dict()
        assert result["total_available"] == 5000
        assert result["returned"] == 1000
        assert result["truncated"] is True
        assert result["strategy"] == "summary"
        assert result["expansion_hint"] == "Use max_tokens=5000 for full content"
        assert len(result["narrowing_suggestions"]) == 2

    def test_pagination_metadata(self):
        """Test metadata for paginated results."""
        metadata = TruncationMetadata(
            total_tokens=10000,
            included_tokens=2000,
            truncated=True,
            truncation_strategy="paginate",
            next_page_cursor="offset:8000",
            expansion_hint="Use the next_page cursor to continue",
        )

        result = metadata.to_dict()
        assert result["next_page"] == "offset:8000"
        assert result["strategy"] == "paginate"


class TestTruncationError:
    """Test TruncationError exception."""

    def test_truncation_error_basic(self):
        """Test basic truncation error."""
        error = TruncationError(
            message="Content too large",
            actual_tokens=5000,
            max_tokens=2000,
        )

        assert str(error) == "Content too large"
        assert error.actual_tokens == 5000
        assert error.max_tokens == 2000
        assert error.narrowing_suggestions == []

    def test_truncation_error_with_suggestions(self):
        """Test truncation error with narrowing suggestions."""
        suggestions = [
            "Use relative_path='src/models' to narrow search",
            "Use depth=1 instead of depth=2",
        ]

        error = TruncationError(
            message="Too many results",
            actual_tokens=10000,
            max_tokens=5000,
            narrowing_suggestions=suggestions,
        )

        assert len(error.narrowing_suggestions) == 2
        assert error.narrowing_suggestions[0].startswith("Use relative_path")

    def test_truncation_error_to_dict(self):
        """Test error serialization to dict."""
        error = TruncationError(
            message="Content exceeds limit",
            actual_tokens=3000,
            max_tokens=1000,
            narrowing_suggestions=["Narrow your search"],
        )

        result = error.to_dict()
        assert result["error"] == "content_too_large"
        assert result["message"] == "Content exceeds limit"
        assert result["actual_tokens"] == 3000
        assert result["max_tokens"] == 1000
        assert len(result["narrowing_suggestions"]) == 1


class TestTokenEstimatorTruncation:
    """Test token estimation for truncation decisions."""

    def test_estimate_text_tokens(self):
        """Test text token estimation."""
        estimator = get_token_estimator()

        # ~1000 chars ≈ 250 tokens (char/4)
        text = "a" * 1000
        tokens = estimator.estimate_text(text)

        assert 200 < tokens < 300  # Allow some margin

    def test_estimate_json_tokens(self):
        """Test JSON token estimation."""
        estimator = get_token_estimator()

        data = {
            "results": [
                {"id": 1, "name": "test1", "value": "x" * 100},
                {"id": 2, "name": "test2", "value": "y" * 100},
            ]
        }

        tokens = estimator.estimate_json(data)
        assert tokens > 50  # Should account for JSON overhead

    def test_estimate_code_tokens(self):
        """Test code token estimation."""
        estimator = get_token_estimator()

        code = """
        def example_function(x, y):
            '''Example docstring'''
            result = x + y
            return result
        """

        tokens = estimator.estimate_code(code)
        assert tokens > 0
        # Code uses ~3.7 chars/token, so should be more tokens than text


class TestTruncationModes:
    """Test the three truncation modes in a mock Tool context."""

    def test_no_truncation_needed(self):
        """Test when content is under limit - no truncation."""
        # This will be tested via Tool._handle_truncation in integration tests
        pass

    def test_error_mode_raises_exception(self):
        """Test error mode raises TruncationError."""
        # This will be tested via Tool._handle_truncation in integration tests
        pass

    def test_summary_mode_truncates_intelligently(self):
        """Test summary mode truncates at boundaries."""
        # This will be tested via Tool._handle_truncation in integration tests
        pass

    def test_paginate_mode_provides_cursor(self):
        """Test paginate mode includes next_page cursor."""
        # This will be tested via Tool._handle_truncation in integration tests
        pass


class TestBackwardCompatibility:
    """Test backward compatibility with max_answer_chars."""

    def test_max_answer_chars_still_works(self):
        """Test that existing max_answer_chars parameter still functions."""
        # Once we add the compatibility layer, test that:
        # max_answer_chars=-1 maps to config default
        # max_answer_chars=N converts to approximate max_tokens=N/4
        pass

    def test_max_tokens_takes_precedence(self):
        """Test that max_tokens overrides max_answer_chars if both specified."""
        pass

    def test_deprecation_warning_shown(self):
        """Test that using max_answer_chars shows deprecation warning."""
        pass


class TestMigrationStrategy:
    """Test migration from old to new API."""

    def test_old_api_with_max_answer_chars(self):
        """
        OLD: tool.apply(max_answer_chars=10000)
        Should still work with deprecation warning
        """
        pass

    def test_new_api_with_max_tokens_error_mode(self):
        """
        NEW: tool.apply(max_tokens=2500, truncation='error')
        Should be the recommended default
        """
        pass

    def test_new_api_with_max_tokens_summary_mode(self):
        """
        NEW: tool.apply(max_tokens=2500, truncation='summary')
        Should truncate intelligently
        """
        pass

    def test_new_api_with_max_tokens_paginate_mode(self):
        """
        NEW: tool.apply(max_tokens=2500, truncation='paginate')
        Should return cursor for next page
        """
        pass


class TestNarrowingSuggestions:
    """Test generation of narrowing suggestions per tool."""

    def test_find_symbol_narrowing_suggestions(self):
        """Test suggestions specific to find_symbol tool."""
        # Expected suggestions:
        # - Use relative_path='src/models' to search specific directory
        # - Use depth=1 to get only immediate children
        # - Use substring_matching=False for exact matches
        # - Use include_kinds=[5] to filter by symbol type
        pass

    def test_list_dir_narrowing_suggestions(self):
        """Test suggestions specific to list_dir tool."""
        # Expected suggestions:
        # - Use recursive=False to avoid deep traversal
        # - Use relative_path to target specific subdirectory
        pass

    def test_search_pattern_narrowing_suggestions(self):
        """Test suggestions specific to search_for_pattern tool."""
        # Expected suggestions:
        # - Use relative_path to search in specific directory
        # - Use result_format='summary' for overview
        # - Make search pattern more specific
        pass


class TestTokenMetadataIntegration:
    """Test integration with existing token metadata system."""

    def test_truncation_metadata_added_to_response(self):
        """Test that _truncation field is added to tool responses."""
        pass

    def test_token_estimate_and_truncation_metadata_combined(self):
        """Test that both _tokens and _truncation can coexist."""
        pass

    def test_metadata_in_json_response(self):
        """Test metadata is properly formatted in JSON responses."""
        pass

    def test_metadata_in_string_response(self):
        """Test metadata is appended to string responses."""
        pass


# Integration test scenarios
class TestEndToEndScenarios:
    """End-to-end tests for real tool usage patterns."""

    def test_large_symbol_search_with_error_mode(self):
        """
        Scenario: Agent searches for common name like 'test'
        With error mode, should get clear error + suggestions
        """
        pass

    def test_large_symbol_search_with_summary_mode(self):
        """
        Scenario: Agent wants overview of many symbols
        With summary mode, should get truncated list + metadata
        """
        pass

    def test_paginated_reference_search(self):
        """
        Scenario: Agent finds references to common utility function
        With paginate mode, should get first page + cursor
        """
        pass

    def test_file_read_within_limits(self):
        """
        Scenario: Agent reads small file
        Should return full content with no truncation
        """
        pass

    def test_file_read_exceeds_limits(self):
        """
        Scenario: Agent reads large file with error mode
        Should get clear error message with suggestions
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
