"""
Standalone test for pattern extraction - no pytest required
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from serena.text_utils import extract_usage_pattern


def test_extract_usage_pattern():
    """Run comprehensive tests on extract_usage_pattern"""

    tests = [
        # (line, symbol_name, expected_result_contains)
        # Import statements
        ("from auth import authenticate", "authenticate", "import authenticate"),
        ("from auth.services import authenticate", "authenticate", "import authenticate"),
        ("import authenticate", "authenticate", "import authenticate"),

        # Function calls
        ("result = authenticate(user, password)", "authenticate", "authenticate(user, password)"),
        ("x = get_config()", "get_config", "get_config()"),

        # Method calls
        ("user.authenticate(password)", "authenticate", "user.authenticate(password)"),
        ("user.profile.get_name()", "get_name", "user.profile.get_name()"),
        ("app.services.auth.validate(token)", "validate", "app.services.auth.validate(token)"),

        # Assignments
        ("handler = authenticate", "authenticate", "handler = authenticate"),

        # Function arguments
        ("register_handler(authenticate)", "authenticate", "register_handler(authenticate)"),

        # Return statements
        ("return authenticate", "authenticate", "return authenticate"),
        ("return authenticate(user)", "authenticate", "authenticate(user)"),

        # Edge cases
        ("", "foo", None),
        ("some code", "", None),
        ("some other code", "foo", None),

        # With whitespace
        ("    result = foo.bar(x)", "bar", "foo.bar(x)"),
        ("result = foo()   ", "foo", "foo()"),

        # Complex patterns
        ("result = outer(inner(authenticate(user)))", "authenticate", "authenticate(user)"),
        ("self.authenticate(credentials)", "authenticate", "self.authenticate(credentials)"),
        ("await authenticate(user)", "authenticate", "authenticate(user)"),
    ]

    passed = 0
    failed = 0

    for i, (line, symbol_name, expected) in enumerate(tests, 1):
        result = extract_usage_pattern(line, symbol_name)

        if expected is None:
            if result is None:
                print(f"[PASS] Test {i}: {line[:50]}... -> None")
                passed += 1
            else:
                print(f"[FAIL] Test {i}: {line[:50]}...")
                print(f"  Expected: None")
                print(f"  Got: {result}")
                failed += 1
        else:
            if result and expected in result:
                print(f"[PASS] Test {i}: {line[:50]}... -> {result}")
                passed += 1
            else:
                print(f"[FAIL] Test {i}: {line[:50]}...")
                print(f"  Expected to contain: {expected}")
                print(f"  Got: {result}")
                failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    print(f"{'='*60}")

    if failed == 0:
        print("[SUCCESS] All tests passed!")
        return True
    else:
        print(f"[FAILURE] {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = test_extract_usage_pattern()
    sys.exit(0 if success else 1)
