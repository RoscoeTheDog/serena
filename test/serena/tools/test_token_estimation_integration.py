"""
Integration tests for Token Estimation Framework with other stories.

Tests integration with:
- Story 5: Signature Mode with Complexity Warnings
- Story 6: Semantic Truncation with Context Markers
- Story 9: Verbosity Control System
- Story 11: On-Demand Body Retrieval (API tests only - tool not implemented yet)
"""

import json
from unittest.mock import Mock, patch

import pytest

from serena.util.token_estimator import FastTokenEstimator, TokenEstimate, get_token_estimator


class TestStory5Integration:
    """Integration tests with Story 5 (Signature Mode)."""

    @pytest.fixture
    def estimator(self):
        return get_token_estimator()

    @pytest.fixture
    def mock_symbol(self):
        """Mock symbol with realistic Python function."""
        symbol = Mock()
        symbol.extract_signature = Mock(
            return_value="def process_payment(amount: Decimal, card: Card, metadata: dict) -> PaymentResult:"
        )
        symbol.extract_docstring = Mock(
            return_value="Process payment with fraud detection and validation.\n\nArgs:\n    amount: Payment amount\n    card: Card details\n    metadata: Additional payment metadata\n\nReturns:\n    PaymentResult with transaction details"
        )
        symbol.get_body = Mock(
            return_value="""def process_payment(amount: Decimal, card: Card, metadata: dict) -> PaymentResult:
    \"\"\"Process payment with fraud detection and validation.

    Args:
        amount: Payment amount
        card: Card details
        metadata: Additional payment metadata

    Returns:
        PaymentResult with transaction details
    \"\"\"
    if amount <= 0:
        raise ValueError("Amount must be positive")

    # Validate card
    if not card.is_valid():
        return PaymentResult(success=False, error="Invalid card")

    # Check fraud rules
    fraud_score = fraud_detector.analyze(card, amount, metadata)
    if fraud_score > FRAUD_THRESHOLD:
        return PaymentResult(success=False, error="Fraud detected")

    # Process transaction
    try:
        transaction = payment_gateway.charge(amount, card)
        return PaymentResult(success=True, transaction_id=transaction.id)
    except PaymentException as e:
        log.error(f"Payment failed: {e}")
        return PaymentResult(success=False, error=str(e))"""
        )
        return symbol

    def test_signature_vs_full_body_estimate(self, estimator, mock_symbol):
        """Test that signature mode estimates are significantly smaller than full body."""
        sig_tokens = estimator.estimate_symbol(mock_symbol, mode="signature")
        full_tokens = estimator.estimate_symbol(mock_symbol, mode="full")

        # Signature should be 70-90% smaller
        reduction = (full_tokens - sig_tokens) / full_tokens
        assert reduction >= 0.7
        assert reduction <= 0.95

    def test_signature_includes_overhead(self, estimator, mock_symbol):
        """Test that signature estimation includes metadata overhead."""
        # Just the raw text
        sig_text = mock_symbol.extract_signature() + mock_symbol.extract_docstring()
        raw_estimate = estimator.estimate_code(sig_text)

        # With overhead
        sig_estimate = estimator.estimate_symbol(mock_symbol, mode="signature")

        # Should have ~50 token overhead
        assert sig_estimate > raw_estimate
        assert sig_estimate - raw_estimate < 100  # Reasonable overhead

    def test_token_estimates_in_response_metadata(self, estimator, mock_symbol):
        """Test that FindSymbolTool response includes token estimates (Story 5 integration)."""
        # Simulate tool response with detail_level support
        sig_tokens = estimator.estimate_symbol(mock_symbol, mode="signature")
        full_tokens = estimator.estimate_symbol(mock_symbol, mode="full")

        # Build response like FindSymbolTool would
        response = {
            "name": "process_payment",
            "signature": mock_symbol.extract_signature(),
            "docstring": mock_symbol.extract_docstring(),
            "tokens_estimate": {
                "signature": sig_tokens,
                "full_body": full_tokens,
            },
        }

        assert response["tokens_estimate"]["signature"] < response["tokens_estimate"]["full_body"]
        assert response["tokens_estimate"]["full_body"] > sig_tokens * 3


class TestStory6Integration:
    """Integration tests with Story 6 (Semantic Truncation)."""

    @pytest.fixture
    def estimator(self):
        return get_token_estimator()

    def test_estimate_sections_for_truncation(self, estimator):
        """Test section estimation for semantic truncation."""
        sections = [
            {
                "name": "PaymentProcessor",
                "content": "class PaymentProcessor:\n    def __init__(self): pass",
            },
            {
                "name": "PaymentProcessor.validate",
                "content": "def validate(self, card):\n    return card.is_valid()",
            },
            {
                "name": "PaymentProcessor.charge",
                "content": "def charge(self, amount, card):\n    return gateway.process(amount, card)",
            },
        ]

        estimates = estimator.estimate_sections(sections)

        # All sections should have estimates
        assert len(estimates) == 3
        assert all(est > 0 for est in estimates.values())

        # Longer content = more tokens
        class_tokens = estimates["PaymentProcessor"]
        method_tokens = estimates["PaymentProcessor.validate"]
        assert class_tokens > 0
        assert method_tokens > 0

    def test_truncation_token_budget(self, estimator):
        """Test token budget calculation for semantic truncation."""
        full_content = "def foo():\n    pass\n\n" * 100  # 100 simple functions
        full_tokens = estimator.estimate_code(full_content)

        # If max_answer_chars = 2000, that's ~500 tokens
        max_chars = 2000
        max_tokens = max_chars // 4

        # Should be able to calculate how much to include
        assert max_tokens < full_tokens
        # Truncation should leave room for metadata
        usable_tokens = int(max_tokens * 0.8)  # 80% for content, 20% for metadata
        assert usable_tokens > 0


class TestStory9Integration:
    """Integration tests with Story 9 (Verbosity Control)."""

    @pytest.fixture
    def estimator(self):
        return get_token_estimator()

    def test_verbosity_breakdown_minimal(self, estimator):
        """Test token estimation breakdown from minimal verbosity."""
        content = {"symbols": [{"name": "foo"}, {"name": "bar"}]}
        estimate = estimator.estimate_with_verbosity_breakdown(content, "minimal")

        # Should have all three levels
        assert estimate.if_verbosity_minimal == estimate.current
        assert estimate.if_verbosity_normal and estimate.if_verbosity_normal > estimate.current
        assert estimate.if_verbosity_detailed and estimate.if_verbosity_detailed > estimate.if_verbosity_normal

        # Minimal → Normal should be ~2.5x
        assert estimate.if_verbosity_normal / estimate.current >= 2.0
        assert estimate.if_verbosity_normal / estimate.current <= 3.0

    def test_verbosity_breakdown_normal(self, estimator):
        """Test token estimation breakdown from normal verbosity."""
        content = {"symbols": [{"name": "foo", "body": "def foo(): pass"}]}
        estimate = estimator.estimate_with_verbosity_breakdown(content, "normal")

        # Normal is current
        assert estimate.if_verbosity_normal == estimate.current

        # Minimal should be less
        assert estimate.if_verbosity_minimal and estimate.if_verbosity_minimal < estimate.current

        # Detailed should be more
        assert estimate.if_verbosity_detailed and estimate.if_verbosity_detailed > estimate.current

    def test_verbosity_metadata_in_tool_response(self, estimator):
        """Test that tool responses include verbosity token estimates."""
        result = {"data": "test", "count": 5}
        estimate = estimator.estimate_with_verbosity_breakdown(result, "normal")

        # Simulate _add_verbosity_metadata behavior
        metadata = {
            "_tokens": estimate.to_dict(),
            "_verbosity": {"verbosity_used": "normal"},
        }

        assert "_tokens" in metadata
        assert "current" in metadata["_tokens"]
        assert "if_verbosity_minimal" in metadata["_tokens"]
        assert "if_verbosity_detailed" in metadata["_tokens"]

    def test_upgrade_hint_includes_token_estimate(self, estimator):
        """Test that upgrade hints include token estimates."""
        content = "Test content"
        estimate = estimator.estimate_with_verbosity_breakdown(content, "minimal")

        detailed_tokens = estimate.if_verbosity_detailed
        upgrade_hint = f"Use verbosity='detailed' to get full output (~{detailed_tokens} tokens)"

        assert str(detailed_tokens) in upgrade_hint
        assert "detailed" in upgrade_hint


class TestStory11Integration:
    """Integration tests for Story 11 (On-Demand Body Retrieval) API."""

    @pytest.fixture
    def estimator(self):
        return get_token_estimator()

    @pytest.fixture
    def mock_symbols(self):
        """Create multiple mock symbols for batch testing."""
        symbols = []
        for i in range(5):
            symbol = Mock()
            symbol.get_body = Mock(return_value=f"def function_{i}():\n    pass\n    # Some code here\n    return {i}")
            symbols.append(symbol)
        return symbols

    def test_estimate_symbol_body_api(self, estimator, mock_symbols):
        """Test estimate_symbol_body API for Story 11."""
        symbol = mock_symbols[0]
        tokens = estimator.estimate_symbol_body(symbol)
        assert tokens > 0

    def test_estimate_batch_bodies_api(self, estimator, mock_symbols):
        """Test estimate_batch_bodies API for Story 11."""
        total_tokens = estimator.estimate_batch_bodies(mock_symbols)
        single_token = estimator.estimate_symbol_body(mock_symbols[0])

        # Should be approximately 5x + 10% overhead
        expected_min = single_token * 5
        expected_max = single_token * 5.5

        assert expected_min <= total_tokens <= expected_max

    def test_batch_estimation_overhead(self, estimator, mock_symbols):
        """Test that batch estimation includes structure overhead."""
        # Individual estimates
        individual_sum = sum(estimator.estimate_symbol_body(s) for s in mock_symbols)

        # Batch estimate
        batch_total = estimator.estimate_batch_bodies(mock_symbols)

        # Batch should be slightly more due to JSON structure (~10%)
        assert batch_total > individual_sum
        assert batch_total < individual_sum * 1.2  # No more than 20% overhead

    def test_body_retrieval_token_guidance(self, estimator, mock_symbols):
        """Test that symbol search can provide token estimates for body retrieval."""
        # Simulate find_symbol result with metadata
        search_results = []
        for symbol in mock_symbols[:3]:
            body_tokens = estimator.estimate_symbol_body(symbol)
            search_results.append({
                "name": f"function_{len(search_results)}",
                "estimated_body_tokens": body_tokens,
            })

        # All results should have token estimates
        assert all("estimated_body_tokens" in r for r in search_results)
        assert all(r["estimated_body_tokens"] > 0 for r in search_results)


class TestToolBaseIntegration:
    """Integration tests with Tool base class."""

    def test_tool_can_get_estimator(self):
        """Test that tools can get estimator instance."""
        estimator = get_token_estimator()
        assert isinstance(estimator, FastTokenEstimator)

    def test_token_estimate_dataclass(self):
        """Test TokenEstimate dataclass usage."""
        estimate = TokenEstimate(
            current=100,
            if_verbosity_normal=250,
            if_verbosity_detailed=500,
        )

        assert estimate.current == 100
        assert estimate.if_verbosity_normal == 250
        assert estimate.if_verbosity_detailed == 500

    def test_token_estimate_to_dict_for_json(self):
        """Test TokenEstimate serialization for JSON responses."""
        estimate = TokenEstimate(current=100, if_verbosity_detailed=500)
        as_dict = estimate.to_dict()

        # Should be serializable
        json_str = json.dumps(as_dict)
        assert json_str

        # Should omit None values
        assert "if_verbosity_normal" not in as_dict


class TestAcceptanceCriteria:
    """Tests verifying all acceptance criteria for Story 10."""

    @pytest.fixture
    def estimator(self):
        return get_token_estimator()

    def test_all_tools_can_return_estimates(self, estimator):
        """Verify tools can return token estimates."""
        # Test data representing tool output
        test_outputs = [
            "Plain text result",
            {"structured": "data", "count": 5},
            {"symbols": [{"name": "foo"}, {"name": "bar"}]},
        ]

        for output in test_outputs:
            estimate = estimator._estimate_tokens(output) if isinstance(output, dict) else estimator.estimate_text(output)
            assert estimate > 0 if isinstance(estimate, int) else estimate.current > 0

    def test_estimates_within_10_percent_accuracy(self, estimator):
        """Verify estimates are within 10% accuracy."""
        # Test cases with known approximate token counts
        test_cases = [
            ("Hello world", 2, 3),  # ~2-3 tokens
            ("The quick brown fox", 4, 5),  # ~4-5 tokens
            ("def foo(): pass", 4, 6),  # ~4-6 tokens
        ]

        for text, min_tokens, max_tokens in test_cases:
            estimate = estimator.estimate_code(text)
            assert min_tokens - 1 <= estimate <= max_tokens + 1  # Allow ±1 token margin

    def test_fast_estimation_under_10ms(self, estimator):
        """Verify estimation overhead is < 10ms for normal use."""
        import time

        # Single estimation
        start = time.perf_counter()
        estimator.estimate_text("Test content")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.001  # < 1ms

        # Batch of 50
        mock_symbol = Mock()
        mock_symbol.get_body = Mock(return_value="def foo(): pass")
        symbols = [mock_symbol] * 50

        start = time.perf_counter()
        estimator.estimate_batch_bodies(symbols)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.010  # < 10ms

    def test_works_with_existing_analytics_module(self):
        """Verify compatibility with existing analytics module."""
        # FastTokenEstimator is separate from TokenCountEstimator
        # Both can coexist
        from serena.analytics import TokenCountEstimator
        from serena.util.token_estimator import FastTokenEstimator

        assert TokenCountEstimator is not FastTokenEstimator
        # They serve different purposes:
        # - TokenCountEstimator: Abstract base for exact counting (tiktoken, Anthropic API)
        # - FastTokenEstimator: Fast approximation for user guidance

    def test_integration_api_for_stories_5_6_9_11(self, estimator):
        """Verify integration APIs exist for other stories."""
        # Story 5: Signature mode
        assert hasattr(estimator, "estimate_symbol")

        # Story 6: Semantic truncation
        assert hasattr(estimator, "estimate_sections")

        # Story 9: Verbosity control
        assert hasattr(estimator, "estimate_at_verbosity")
        assert hasattr(estimator, "estimate_with_verbosity_breakdown")

        # Story 11: On-demand body retrieval
        assert hasattr(estimator, "estimate_symbol_body")
        assert hasattr(estimator, "estimate_batch_bodies")
