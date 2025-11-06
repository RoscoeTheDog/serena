"""
Standalone test runner for Token Estimation Framework.
Runs without pytest to verify core functionality.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serena.util.token_estimator import FastTokenEstimator, TokenEstimate, get_token_estimator


class MockSymbol:
    """Mock symbol for testing."""

    def __init__(self):
        self.signature = "def process_data(items: list[str]) -> dict:"
        self.docstring = "Process list of items and return results."
        self.body = """def process_data(items: list[str]) -> dict:
    \"\"\"Process list of items and return results.\"\"\"
    results = {}
    for item in items:
        results[item] = len(item)
    return results"""

    def extract_signature(self):
        return self.signature

    def extract_docstring(self):
        return self.docstring

    def get_body(self):
        return self.body


def test_basic_estimation():
    """Test basic token estimation."""
    print("Test 1: Basic Estimation")
    estimator = FastTokenEstimator()

    text = "This is a simple test string."
    tokens = estimator.estimate_text(text)
    expected = int(len(text) * 0.25)

    assert tokens == expected, f"Expected {expected}, got {tokens}"
    print(f"[OK] Text estimation: {tokens} tokens")


def test_code_estimation():
    """Test code estimation."""
    print("\nTest 2: Code Estimation")
    estimator = FastTokenEstimator()

    code = "def foo(x):\n    return x * 2"
    tokens = estimator.estimate_code(code)

    assert tokens > 0, "Code tokens should be > 0"
    print(f"[OK] Code estimation: {tokens} tokens")


def test_json_estimation():
    """Test JSON estimation."""
    print("\nTest 3: JSON Estimation")
    estimator = FastTokenEstimator()

    data = {"name": "test", "value": 42, "active": True}
    tokens = estimator.estimate_json(data)

    assert tokens > 5, "JSON should have reasonable token count"
    print(f"[OK] JSON estimation: {tokens} tokens")


def test_symbol_estimation():
    """Test symbol estimation."""
    print("\nTest 4: Symbol Estimation")
    estimator = FastTokenEstimator()
    symbol = MockSymbol()

    sig_tokens = estimator.estimate_symbol(symbol, mode="signature")
    full_tokens = estimator.estimate_symbol(symbol, mode="full")

    assert sig_tokens > 0, "Signature tokens should be > 0"
    assert full_tokens > sig_tokens, "Full body should be larger than signature"

    print(f"[OK] Signature mode: {sig_tokens} tokens")
    print(f"[OK] Full mode: {full_tokens} tokens")
    print(f"[OK] Savings: {100 * (1 - sig_tokens/full_tokens):.1f}%")


def test_verbosity_estimation():
    """Test verbosity level estimation."""
    print("\nTest 5: Verbosity Estimation")
    estimator = FastTokenEstimator()

    content = "Test content"

    # Same level
    tokens_same = estimator.estimate_at_verbosity(content, "normal", "normal")
    expected = estimator.estimate_text(content)
    assert tokens_same == expected, "Same level should return same tokens"
    print(f"[OK] Same verbosity: {tokens_same} tokens")

    # Upgrade
    tokens_detailed = estimator.estimate_at_verbosity(content, "normal", "detailed")
    assert tokens_detailed > tokens_same, "Detailed should be more than normal"
    print(f"[OK] Normal -> Detailed: {tokens_same} -> {tokens_detailed} tokens ({tokens_detailed/tokens_same:.1f}x)")

    # Downgrade
    tokens_minimal = estimator.estimate_at_verbosity(content, "normal", "minimal")
    assert tokens_minimal < tokens_same, "Minimal should be less than normal"
    print(f"[OK] Normal -> Minimal: {tokens_same} -> {tokens_minimal} tokens ({tokens_minimal/tokens_same:.1f}x)")


def test_verbosity_breakdown():
    """Test verbosity breakdown."""
    print("\nTest 6: Verbosity Breakdown")
    estimator = FastTokenEstimator()

    content = "Test content"
    estimate = estimator.estimate_with_verbosity_breakdown(content, "normal")

    assert estimate.current > 0, "Current should be > 0"
    assert estimate.if_verbosity_minimal < estimate.current, "Minimal should be less"
    assert estimate.if_verbosity_detailed > estimate.current, "Detailed should be more"

    print(f"[OK] Current (normal): {estimate.current} tokens")
    print(f"[OK] If minimal: {estimate.if_verbosity_minimal} tokens")
    print(f"[OK] If detailed: {estimate.if_verbosity_detailed} tokens")


def test_section_estimation():
    """Test section estimation."""
    print("\nTest 7: Section Estimation")
    estimator = FastTokenEstimator()

    sections = [
        {"name": "section1", "content": "def foo(): pass"},
        {"name": "section2", "content": "def bar(): return 42"},
    ]

    estimates = estimator.estimate_sections(sections)

    assert "section1" in estimates, "section1 should be in estimates"
    assert "section2" in estimates, "section2 should be in estimates"
    assert estimates["section1"] > 0, "section1 tokens should be > 0"
    assert estimates["section2"] > 0, "section2 tokens should be > 0"

    print(f"[OK] Section 1: {estimates['section1']} tokens")
    print(f"[OK] Section 2: {estimates['section2']} tokens")


def test_batch_estimation():
    """Test batch body estimation."""
    print("\nTest 8: Batch Estimation")
    estimator = FastTokenEstimator()

    symbols = [MockSymbol() for _ in range(5)]
    total_tokens = estimator.estimate_batch_bodies(symbols)
    single_tokens = estimator.estimate_symbol_body(symbols[0])

    assert total_tokens > single_tokens * 5, "Batch should be sum + overhead"
    assert total_tokens < single_tokens * 6, "Overhead should be reasonable (allow up to 20%)"

    print(f"[OK] Single body: {single_tokens} tokens")
    print(f"[OK] Batch (5): {total_tokens} tokens")
    print(f"[OK] Overhead: {((total_tokens / (single_tokens * 5)) - 1) * 100:.1f}%")


def test_performance():
    """Test performance requirements."""
    print("\nTest 9: Performance")
    estimator = FastTokenEstimator()

    # Single estimation
    text = "This is a test string for performance measurement."
    start = time.perf_counter()
    estimator.estimate_text(text)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.001, f"Single estimation should be < 1ms, got {elapsed*1000:.3f}ms"
    print(f"[OK] Single estimation: {elapsed*1000:.3f}ms (< 1ms required)")

    # Batch estimation
    symbols = [MockSymbol() for _ in range(100)]
    start = time.perf_counter()
    estimator.estimate_batch_bodies(symbols)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.01, f"Batch (100) should be < 10ms, got {elapsed*1000:.3f}ms"
    print(f"[OK] Batch estimation (100): {elapsed*1000:.3f}ms (< 10ms required)")


def test_token_estimate_dataclass():
    """Test TokenEstimate dataclass."""
    print("\nTest 10: TokenEstimate Dataclass")

    estimate = TokenEstimate(
        current=100,
        if_verbosity_normal=250,
        if_verbosity_detailed=500,
    )

    assert estimate.current == 100
    assert estimate.if_verbosity_normal == 250
    assert estimate.if_verbosity_detailed == 500

    print(f"[OK] TokenEstimate created: {estimate.current} tokens")

    # Test to_dict
    as_dict = estimate.to_dict()
    assert "current" in as_dict
    assert "if_verbosity_normal" in as_dict
    assert "if_verbosity_detailed" in as_dict

    print(f"[OK] to_dict: {len(as_dict)} fields")

    # Test None omission
    estimate2 = TokenEstimate(current=100)
    as_dict2 = estimate2.to_dict()
    assert "current" in as_dict2
    assert "if_verbosity_normal" not in as_dict2

    print(f"[OK] None values omitted: {len(as_dict2)} fields")


def test_singleton():
    """Test singleton pattern."""
    print("\nTest 11: Singleton Pattern")

    est1 = get_token_estimator()
    est2 = get_token_estimator()

    assert est1 is est2, "Should return same instance"
    assert isinstance(est1, FastTokenEstimator)

    print(f"[OK] Singleton works: {id(est1) == id(est2)}")


def test_accuracy():
    """Test estimation accuracy."""
    print("\nTest 12: Accuracy Verification")
    estimator = FastTokenEstimator()

    # Test cases with known approximate token counts
    test_cases = [
        ("Hello world", 2, 3, "simple text"),
        ("The quick brown fox jumps over the lazy dog.", 10, 12, "sentence"),
        ("def add(a, b):\n    return a + b", 8, 10, "code"),
    ]

    for text, min_tokens, max_tokens, description in test_cases:
        if "code" in description:
            estimate = estimator.estimate_code(text)
        else:
            estimate = estimator.estimate_text(text)

        within_range = min_tokens - 1 <= estimate <= max_tokens + 1
        assert within_range, f"{description}: expected {min_tokens}-{max_tokens}, got {estimate}"
        print(f"[OK] {description}: {estimate} tokens (within {min_tokens}-{max_tokens})")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Token Estimation Framework - Standalone Tests")
    print("=" * 60)

    tests = [
        test_basic_estimation,
        test_code_estimation,
        test_json_estimation,
        test_symbol_estimation,
        test_verbosity_estimation,
        test_verbosity_breakdown,
        test_section_estimation,
        test_batch_estimation,
        test_performance,
        test_token_estimate_dataclass,
        test_singleton,
        test_accuracy,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[FAIL] {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
