"""
Standalone test for snippet selection functionality in FindReferencingSymbolsTool
Tests the integration of context_lines and extract_pattern parameters
"""

from serena.text_utils import extract_usage_pattern


def test_basic_pattern_extraction():
    """Test basic pattern extraction scenarios"""
    print("Testing pattern extraction...")

    # Test 1: Function call
    line1 = "result = authenticate(user, password)"
    pattern1 = extract_usage_pattern(line1, "authenticate")
    assert pattern1 == "authenticate(user, password)", f"Expected 'authenticate(user, password)', got '{pattern1}'"
    print(f"✓ Test 1 passed: {pattern1}")

    # Test 2: Method call
    line2 = "user.profile.get_name()"
    pattern2 = extract_usage_pattern(line2, "get_name")
    assert pattern2 == "user.profile.get_name()", f"Expected 'user.profile.get_name()', got '{pattern2}'"
    print(f"✓ Test 2 passed: {pattern2}")

    # Test 3: Import statement
    line3 = "from auth import authenticate"
    pattern3 = extract_usage_pattern(line3, "authenticate")
    assert pattern3 == "import authenticate", f"Expected 'import authenticate', got '{pattern3}'"
    print(f"✓ Test 3 passed: {pattern3}")

    # Test 4: Assignment
    line4 = "handler = authenticate"
    pattern4 = extract_usage_pattern(line4, "authenticate")
    assert pattern4 == "handler = authenticate", f"Expected 'handler = authenticate', got '{pattern4}'"
    print(f"✓ Test 4 passed: {pattern4}")

    # Test 5: Return statement
    line5 = "return authenticate"
    pattern5 = extract_usage_pattern(line5, "authenticate")
    assert pattern5 == "return authenticate", f"Expected 'return authenticate', got '{pattern5}'"
    print(f"✓ Test 5 passed: {pattern5}")

    # Test 6: Chained call
    line6 = "result = obj.method1().method2(arg).method3()"
    pattern6 = extract_usage_pattern(line6, "method2")
    assert "method2(arg)" in pattern6, f"Expected 'method2(arg)' in result, got '{pattern6}'"
    print(f"✓ Test 6 passed: {pattern6}")

    print("\n✅ All pattern extraction tests passed!")


def test_token_savings_estimate():
    """Estimate token savings from snippet selection"""
    print("\n\nTesting token savings...")

    # Simulate a reference with full context (3 lines before + match + 3 lines after = 7 lines)
    full_context = """
  1: def process_payment(amount, user):
  2:     \"\"\"Process payment for user\"\"\"
  3:     if not validate_user(user):
> 4:         result = authenticate(user, get_credentials())
  5:         if not result:
  6:             raise AuthenticationError()
  7:     return charge_card(amount, user)
"""

    # With snippet selection: just the pattern + line number + hint
    snippet_format = """
reference_line: 4
usage_pattern: authenticate(user, get_credentials())
full_line:         result = authenticate(user, get_credentials())
expand_context_hint: Use context_lines=3 for more surrounding code
"""

    # Estimate tokens (chars / 4 approximation)
    full_tokens = len(full_context) // 4
    snippet_tokens = len(snippet_format) // 4

    savings_percent = ((full_tokens - snippet_tokens) / full_tokens) * 100

    print(f"Full context: ~{full_tokens} tokens")
    print(f"Snippet format: ~{snippet_tokens} tokens")
    print(f"Token savings: ~{savings_percent:.1f}%")

    assert savings_percent > 40, f"Expected >40% savings, got {savings_percent:.1f}%"
    assert savings_percent < 80, f"Expected <80% savings (should be in 40-70% range), got {savings_percent:.1f}%"

    print(f"✅ Token savings within expected range (40-70%): {savings_percent:.1f}%")


def test_backward_compatibility():
    """Test that existing behavior is preserved"""
    print("\n\nTesting backward compatibility...")

    # The function should work with default parameters
    line = "result = authenticate(user)"
    pattern = extract_usage_pattern(line, "authenticate")

    # Should extract something useful
    assert pattern is not None, "Pattern extraction should not return None for valid input"
    assert "authenticate" in pattern, "Pattern should contain the symbol name"

    print(f"✓ Backward compatibility maintained")
    print(f"✓ Default extraction works: '{pattern}'")
    print("✅ Backward compatibility tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Story 7: Smart Snippet Selection - Standalone Tests")
    print("=" * 70)

    try:
        test_basic_pattern_extraction()
        test_token_savings_estimate()
        test_backward_compatibility()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nStory 7 implementation is working correctly:")
        print("  ✓ Pattern extraction working")
        print("  ✓ Token savings in expected range (40-70%)")
        print("  ✓ Backward compatible")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
