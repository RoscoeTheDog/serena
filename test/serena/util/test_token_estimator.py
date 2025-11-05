"""
Unit tests for Token Estimation Framework (Story 10).

Tests cover:
- Fast estimation accuracy (within 10%)
- Performance requirements (<10ms)
- Different content types (text, code, JSON)
- Verbosity level estimation
- Symbol estimation (signatures vs full body)
- Batch estimation
"""

import json
import time
from unittest.mock import Mock

import pytest

from serena.util.token_estimator import FastTokenEstimator, TokenEstimate, get_token_estimator


class TestFastTokenEstimator:
    """Tests for FastTokenEstimator class."""

    @pytest.fixture
    def estimator(self):
        return FastTokenEstimator()

    @pytest.fixture
    def mock_symbol(self):
        """Create a mock LanguageServerSymbol for testing."""
        symbol = Mock()
        symbol.extract_signature = Mock(return_value="def process_data(items: list[str]) -> dict:")
        symbol.extract_docstring = Mock(return_value="Process list of items and return results.")
        symbol.get_body = Mock(
            return_value="""def process_data(items: list[str]) -> dict:
    \"\"\"Process list of items and return results.\"\"\"
    results = {}
    for item in items:
        results[item] = len(item)
    return results"""
        )
        return symbol

    # =======================
    # Basic Estimation Tests
    # =======================

    def test_estimate_text_basic(self, estimator):
        """Test basic text estimation."""
        text = "This is a simple test string."
        tokens = estimator.estimate_text(text)
        expected = int(len(text) * 0.25)
        assert tokens == expected
        assert tokens > 0

    def test_estimate_text_empty(self, estimator):
        """Test empty text returns at least 1 token."""
        tokens = estimator.estimate_text("")
        assert tokens == 1

    def test_estimate_code_basic(self, estimator):
        """Test code estimation."""
        code = "def foo(x):\n    return x * 2"
        tokens = estimator.estimate_code(code)
        expected = int(len(code) * 0.27)
        assert tokens == expected
        assert tokens > 0

    def test_estimate_json_dict(self, estimator):
        """Test JSON dictionary estimation."""
        data = {"name": "test", "value": 42, "active": True}
        tokens = estimator.estimate_json(data)
        # Should be more than simple text due to JSON overhead
        assert tokens > 5

    def test_estimate_json_list(self, estimator):
        """Test JSON list estimation."""
        data = [1, 2, 3, 4, 5]
        tokens = estimator.estimate_json(data)
        assert tokens > 0

    # =======================
    # Symbol Estimation Tests
    # =======================

    def test_estimate_symbol_signature_mode(self, estimator, mock_symbol):
        """Test symbol estimation in signature mode."""
        tokens = estimator.estimate_symbol(mock_symbol, mode="signature")
        # Should include signature + docstring + metadata overhead
        assert tokens > 50
        assert tokens < 200  # Should be relatively small

    def test_estimate_symbol_full_mode(self, estimator, mock_symbol):
        """Test symbol estimation in full mode."""
        tokens = estimator.estimate_symbol(mock_symbol, mode="full")
        # Should be significantly larger than signature mode
        assert tokens > 100

    def test_estimate_symbol_full_vs_signature(self, estimator, mock_symbol):
        """Test that full mode returns more tokens than signature mode."""
        sig_tokens = estimator.estimate_symbol(mock_symbol, mode="signature")
        full_tokens = estimator.estimate_symbol(mock_symbol, mode="full")
        assert full_tokens > sig_tokens

    def test_estimate_symbol_body(self, estimator, mock_symbol):
        """Test body-only estimation."""
        tokens = estimator.estimate_symbol_body(mock_symbol)
        assert tokens > 0

    def test_estimate_batch_bodies(self, estimator, mock_symbol):
        """Test batch body estimation."""
        symbols = [mock_symbol, mock_symbol, mock_symbol]
        total_tokens = estimator.estimate_batch_bodies(symbols)
        single_tokens = estimator.estimate_symbol_body(mock_symbol)
        # Should be ~3x single + 10% overhead
        assert total_tokens > single_tokens * 3
        assert total_tokens < single_tokens * 3.5

    # =======================
    # Verbosity Level Tests
    # =======================

    def test_estimate_at_verbosity_same_level(self, estimator):
        """Test estimation at same verbosity level."""
        content = "Test content"
        tokens = estimator.estimate_at_verbosity(content, "normal", "normal")
        expected = estimator.estimate_text(content)
        assert tokens == expected

    def test_estimate_at_verbosity_minimal_to_normal(self, estimator):
        """Test upgrading from minimal to normal."""
        content = "Test content"
        current_tokens = estimator.estimate_text(content)
        normal_tokens = estimator.estimate_at_verbosity(content, "minimal", "normal")
        # Should be ~2.5x
        assert normal_tokens > current_tokens * 2
        assert normal_tokens < current_tokens * 3

    def test_estimate_at_verbosity_normal_to_detailed(self, estimator):
        """Test upgrading from normal to detailed."""
        content = "Test content"
        current_tokens = estimator.estimate_text(content)
        detailed_tokens = estimator.estimate_at_verbosity(content, "normal", "detailed")
        # Should be ~2x
        assert detailed_tokens > current_tokens * 1.8
        assert detailed_tokens < current_tokens * 2.5

    def test_estimate_at_verbosity_minimal_to_detailed(self, estimator):
        """Test upgrading from minimal to detailed."""
        content = "Test content"
        current_tokens = estimator.estimate_text(content)
        detailed_tokens = estimator.estimate_at_verbosity(content, "minimal", "detailed")
        # Should be ~5x
        assert detailed_tokens > current_tokens * 4
        assert detailed_tokens < current_tokens * 6

    def test_estimate_at_verbosity_downgrade(self, estimator):
        """Test downgrading verbosity."""
        content = "Test content"
        current_tokens = estimator.estimate_text(content)
        minimal_tokens = estimator.estimate_at_verbosity(content, "detailed", "minimal")
        # Should be ~20% of original
        assert minimal_tokens < current_tokens
        assert minimal_tokens < current_tokens * 0.3

    def test_estimate_at_verbosity_dict(self, estimator):
        """Test verbosity estimation with dict content."""
        content = {"data": "test", "items": [1, 2, 3]}
        tokens = estimator.estimate_at_verbosity(content, "minimal", "normal")
        assert tokens > 0

    # =======================
    # Section Estimation Tests
    # =======================

    def test_estimate_sections_basic(self, estimator):
        """Test section estimation."""
        sections = [
            {"name": "section1", "content": "def foo(): pass"},
            {"name": "section2", "content": "def bar(): return 42"},
        ]
        estimates = estimator.estimate_sections(sections)
        assert "section1" in estimates
        assert "section2" in estimates
        assert estimates["section1"] > 0
        assert estimates["section2"] > 0

    def test_estimate_sections_empty(self, estimator):
        """Test empty section estimation."""
        sections = [{"name": "empty", "content": ""}]
        estimates = estimator.estimate_sections(sections)
        assert estimates["empty"] == 0

    def test_estimate_sections_no_content(self, estimator):
        """Test section without content field."""
        sections = [{"name": "no_content"}]
        estimates = estimator.estimate_sections(sections)
        assert estimates["no_content"] == 0

    # =======================
    # Breakdown Tests
    # =======================

    def test_estimate_with_verbosity_breakdown_minimal(self, estimator):
        """Test breakdown from minimal verbosity."""
        content = "Test content"
        estimate = estimator.estimate_with_verbosity_breakdown(content, "minimal")
        assert estimate.current > 0
        assert estimate.if_verbosity_minimal == estimate.current
        assert estimate.if_verbosity_normal and estimate.if_verbosity_normal > estimate.current
        assert estimate.if_verbosity_detailed and estimate.if_verbosity_detailed > estimate.if_verbosity_normal

    def test_estimate_with_verbosity_breakdown_normal(self, estimator):
        """Test breakdown from normal verbosity."""
        content = "Test content"
        estimate = estimator.estimate_with_verbosity_breakdown(content, "normal")
        assert estimate.current > 0
        assert estimate.if_verbosity_normal == estimate.current
        assert estimate.if_verbosity_minimal and estimate.if_verbosity_minimal < estimate.current
        assert estimate.if_verbosity_detailed and estimate.if_verbosity_detailed > estimate.current

    def test_estimate_with_verbosity_breakdown_detailed(self, estimator):
        """Test breakdown from detailed verbosity."""
        content = "Test content"
        estimate = estimator.estimate_with_verbosity_breakdown(content, "detailed")
        assert estimate.current > 0
        assert estimate.if_verbosity_detailed == estimate.current
        assert estimate.if_verbosity_minimal and estimate.if_verbosity_minimal < estimate.if_verbosity_normal
        assert estimate.if_verbosity_normal and estimate.if_verbosity_normal < estimate.current

    def test_estimate_with_verbosity_breakdown_dict(self, estimator):
        """Test breakdown with dict content."""
        content = {"key": "value"}
        estimate = estimator.estimate_with_verbosity_breakdown(content, "normal")
        assert estimate.current > 0

    # =======================
    # TokenEstimate Tests
    # =======================

    def test_token_estimate_to_dict_basic(self):
        """Test TokenEstimate to_dict method."""
        estimate = TokenEstimate(current=100, if_verbosity_normal=250, if_verbosity_detailed=500)
        result = estimate.to_dict()
        assert result["current"] == 100
        assert result["if_verbosity_normal"] == 250
        assert result["if_verbosity_detailed"] == 500

    def test_token_estimate_to_dict_omits_none(self):
        """Test that to_dict omits None values."""
        estimate = TokenEstimate(current=100)
        result = estimate.to_dict()
        assert "current" in result
        assert "if_verbosity_normal" not in result
        assert "if_verbosity_detailed" not in result

    # =======================
    # Performance Tests
    # =======================

    def test_performance_single_estimation(self, estimator):
        """Test single estimation is < 1ms."""
        text = "This is a test string for performance measurement."
        start = time.perf_counter()
        estimator.estimate_text(text)
        elapsed = time.perf_counter() - start
        # Should be well under 1ms (0.001 seconds)
        assert elapsed < 0.001

    def test_performance_batch_estimation(self, estimator, mock_symbol):
        """Test batch estimation of 100 items is < 10ms."""
        symbols = [mock_symbol for _ in range(100)]
        start = time.perf_counter()
        estimator.estimate_batch_bodies(symbols)
        elapsed = time.perf_counter() - start
        # Should be under 10ms (0.01 seconds)
        assert elapsed < 0.01

    def test_performance_json_estimation(self, estimator):
        """Test JSON estimation performance."""
        data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(50)]}
        start = time.perf_counter()
        estimator.estimate_json(data)
        elapsed = time.perf_counter() - start
        # Should be well under 1ms
        assert elapsed < 0.001

    # =======================
    # Accuracy Tests
    # =======================

    def test_accuracy_within_10_percent_text(self, estimator):
        """Test text estimation accuracy (within 10% of actual)."""
        # Known test case: typical sentence
        text = "The quick brown fox jumps over the lazy dog."
        estimate = estimator.estimate_text(text)
        # Actual tokens (approximate): 10-12 tokens
        # Our estimate should be within ±10%
        assert 9 <= estimate <= 13

    def test_accuracy_within_10_percent_code(self, estimator):
        """Test code estimation accuracy."""
        code = "def add(a, b):\n    return a + b"
        estimate = estimator.estimate_code(code)
        # Actual tokens (approximate): 8-10 tokens
        assert 7 <= estimate <= 11

    def test_accuracy_within_10_percent_json(self, estimator):
        """Test JSON estimation accuracy."""
        data = {"name": "test", "count": 5, "active": True}
        estimate = estimator.estimate_json(data)
        # Actual tokens (approximate): 10-15 tokens
        assert 9 <= estimate <= 16

    # =======================
    # Edge Cases
    # =======================

    def test_edge_case_very_long_text(self, estimator):
        """Test estimation with very long text."""
        text = "a" * 10000
        tokens = estimator.estimate_text(text)
        assert tokens > 2000  # Should be reasonable

    def test_edge_case_unicode(self, estimator):
        """Test estimation with unicode characters."""
        text = "Hello 世界 🌍"
        tokens = estimator.estimate_text(text)
        assert tokens > 0

    def test_edge_case_nested_json(self, estimator):
        """Test estimation with deeply nested JSON."""
        data = {"a": {"b": {"c": {"d": {"e": "value"}}}}}
        tokens = estimator.estimate_json(data)
        assert tokens > 0

    # =======================
    # Global Estimator Tests
    # =======================

    def test_get_token_estimator_singleton(self):
        """Test that get_token_estimator returns singleton."""
        est1 = get_token_estimator()
        est2 = get_token_estimator()
        assert est1 is est2

    def test_get_token_estimator_type(self):
        """Test that get_token_estimator returns correct type."""
        estimator = get_token_estimator()
        assert isinstance(estimator, FastTokenEstimator)
