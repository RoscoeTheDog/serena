"""
Standalone test for semantic truncator (no dependencies).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from serena.util.semantic_truncator import SemanticTruncator, SectionType

# Sample Python code
SAMPLE_CODE = '''
class PaymentProcessor:
    """Handles payment processing."""

    def validate_card(self, card):
        """Validate credit card."""
        if not card:
            return False
        return len(card) == 16

    def charge_card(self, card, amount):
        """Charge the credit card."""
        if not self.validate_card(card):
            raise ValueError("Invalid card")
        return process_payment(card, amount)

def process_payment(card, amount):
    """External payment processing."""
    result = external_api_call(card, amount)
    return result
'''


def test_basic_parsing():
    """Test basic Python parsing."""
    print("Test 1: Basic Python parsing...")
    truncator = SemanticTruncator()
    sections = truncator._parse_python(SAMPLE_CODE)

    assert len(sections) > 0, "Should parse at least one section"

    class_sections = [s for s in sections if s.type == SectionType.CLASS]
    assert len(class_sections) == 1, f"Should find 1 class, found {len(class_sections)}"
    assert class_sections[0].name == "PaymentProcessor"

    func_sections = [s for s in sections if s.type == SectionType.FUNCTION]
    func_names = [s.name for s in func_sections]
    assert "process_payment" in func_names

    print("[PASS] Basic parsing works!")


def test_call_graph():
    """Test call graph building."""
    print("\nTest 2: Call graph building...")
    truncator = SemanticTruncator()
    sections = truncator._parse_python(SAMPLE_CODE)
    truncator._build_call_graph(sections, SAMPLE_CODE)

    # Find charge_card - should call validate_card
    charge_sections = [s for s in sections if s.name == "charge_card"]
    assert len(charge_sections) > 0, "Should find charge_card"

    section = charge_sections[0]
    assert "validate_card" in section.calls, f"charge_card should call validate_card, got: {section.calls}"

    print("[PASS] Call graph works!")


def test_truncation():
    """Test end-to-end truncation."""
    print("\nTest 3: End-to-end truncation...")
    truncator = SemanticTruncator()

    result = truncator.truncate(
        content=SAMPLE_CODE,
        max_tokens=200,
        language="python",
        file_path="payment.py"
    )

    assert len(result.included_sections) > 0, "Should include some sections"
    assert result.included_content != "", "Should have included content"
    assert result.total_truncated_tokens >= 0, "Should have truncation stats"

    # Check that we got some sections
    total_sections = len(result.included_sections) + len(result.truncated_sections)
    assert total_sections > 0, "Should parse sections"

    print(f"[PASS] Truncation works! Included {len(result.included_sections)} sections, truncated {len(result.truncated_sections)}")
    print(f"  Total truncated tokens: {result.total_truncated_tokens}")


def test_semantic_boundaries():
    """Test that truncation respects semantic boundaries."""
    print("\nTest 4: Semantic boundary preservation...")
    truncator = SemanticTruncator()

    result = truncator.truncate(
        content=SAMPLE_CODE,
        max_tokens=150,
        language="python"
    )

    lines = result.included_content.split("\n")

    # Check for complete functions (no mid-function splits)
    for i, line in enumerate(lines):
        if line.strip().startswith("def "):
            # Should have body following
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Either has content or is continuation
                assert next_line.strip() != "" or line.endswith("\\"), \
                    f"Function at line {i} seems incomplete"

    print("[PASS] Semantic boundaries preserved!")


def test_javascript():
    """Test JavaScript parsing."""
    print("\nTest 5: JavaScript parsing...")

    js_code = '''
class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(user) {
        this.users.push(user);
    }
}

function validateUser(user) {
    return user.name && user.email;
}
'''

    truncator = SemanticTruncator()
    result = truncator.truncate(
        content=js_code,
        max_tokens=200,
        language="javascript"
    )

    total_sections = len(result.included_sections) + len(result.truncated_sections)
    assert total_sections > 0, "Should parse JavaScript sections"

    print(f"[PASS] JavaScript parsing works! Found {total_sections} sections")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Semantic Truncator Standalone Tests")
    print("=" * 60)

    try:
        test_basic_parsing()
        test_call_graph()
        test_truncation()
        test_semantic_boundaries()
        test_javascript()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
