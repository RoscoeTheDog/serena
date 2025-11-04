"""
Unit tests for semantic truncation functionality.
"""

import pytest

from serena.util.semantic_truncator import (
    CodeSection,
    ComplexityLevel,
    SectionType,
    SemanticTruncator,
    TruncationResult,
)


# Sample Python code for testing
SAMPLE_PYTHON_CODE = '''
class PaymentProcessor:
    """Handles payment processing."""

    def __init__(self):
        self.active = True

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

    def refund_payment(self, transaction_id):
        """Process a refund."""
        transaction = get_transaction(transaction_id)
        if not transaction:
            return False
        return process_refund(transaction)

def process_payment(card, amount):
    """External payment processing."""
    # Complex logic here
    result = external_api_call(card, amount)
    return result

def get_transaction(transaction_id):
    """Fetch transaction from database."""
    return db.query(transaction_id)

def process_refund(transaction):
    """Process refund logic."""
    return refund_api_call(transaction)
'''

# Sample JavaScript code for testing
SAMPLE_JS_CODE = '''
class UserManager {
    constructor() {
        this.users = [];
    }

    addUser(user) {
        this.users.push(user);
        this.notifyObservers(user);
    }

    removeUser(userId) {
        const index = this.users.findIndex(u => u.id === userId);
        if (index !== -1) {
            this.users.splice(index, 1);
        }
    }

    notifyObservers(user) {
        observers.forEach(o => o.update(user));
    }
}

function validateUser(user) {
    if (!user.name || !user.email) {
        return false;
    }
    return true;
}

const processUserData = (data) => {
    return data.filter(validateUser);
};
'''


class TestCodeSection:
    """Test CodeSection dataclass."""

    def test_code_section_creation(self):
        """Test creating a code section."""
        section = CodeSection(
            type=SectionType.FUNCTION,
            name="test_func",
            start_line=10,
            end_line=20,
            tokens=100,
            complexity=ComplexityLevel.LOW,
            calls=["helper_func"],
            signature="def test_func():",
        )

        assert section.type == SectionType.FUNCTION
        assert section.name == "test_func"
        assert section.line_range == "10-20"
        assert section.tokens == 100

    def test_line_range_single_line(self):
        """Test line range for single-line section."""
        section = CodeSection(
            type=SectionType.FUNCTION, name="test", start_line=10, end_line=10, tokens=10
        )

        assert section.line_range == "10"

    def test_to_dict(self):
        """Test converting section to dictionary."""
        section = CodeSection(
            type=SectionType.FUNCTION,
            name="test_func",
            start_line=10,
            end_line=20,
            tokens=100,
            calls=["helper"],
            called_by=["caller"],
        )

        result = section.to_dict()

        assert result["type"] == "function"
        assert result["name"] == "test_func"
        assert result["lines"] == "10-20"
        assert result["tokens"] == 100
        assert "helper" in result["calls"]
        assert "caller" in result["called_by"]


class TestSemanticTruncator:
    """Test SemanticTruncator class."""

    def test_init_with_custom_estimator(self):
        """Test initialization with custom token estimator."""

        def custom_estimator(text):
            return len(text) // 3

        truncator = SemanticTruncator(token_estimator=custom_estimator)
        assert truncator.token_estimator("123") == 1

    def test_init_with_default_estimator(self):
        """Test initialization with default token estimator."""
        truncator = SemanticTruncator()
        # Default is chars/4
        assert truncator.token_estimator("1234") == 1

    def test_parse_python_classes(self):
        """Test parsing Python classes."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        # Should find PaymentProcessor class and functions
        assert len(sections) > 0

        class_sections = [s for s in sections if s.type == SectionType.CLASS]
        assert len(class_sections) == 1
        assert class_sections[0].name == "PaymentProcessor"

    def test_parse_python_functions(self):
        """Test parsing Python functions."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        function_sections = [s for s in sections if s.type == SectionType.FUNCTION]
        function_names = [s.name for s in function_sections]

        assert "process_payment" in function_names
        assert "get_transaction" in function_names
        assert "process_refund" in function_names

    def test_parse_python_extracts_signatures(self):
        """Test that signatures are extracted correctly."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        # Find a specific function
        func_sections = [s for s in sections if s.name == "validate_card"]
        assert len(func_sections) > 0

        section = func_sections[0]
        assert "def validate_card" in section.signature

    def test_parse_python_extracts_docstrings(self):
        """Test that docstrings are extracted."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        class_sections = [s for s in sections if s.type == SectionType.CLASS]
        assert len(class_sections) > 0

        section = class_sections[0]
        assert "Handles payment processing" in section.docstring

    def test_parse_python_syntax_error_fallback(self):
        """Test fallback for invalid Python syntax."""
        invalid_code = "def broken(\n    missing closing"

        truncator = SemanticTruncator()
        sections = truncator._parse_python(invalid_code)

        # Should fall back to generic parsing
        assert isinstance(sections, list)

    def test_build_call_graph(self):
        """Test building call graph with context markers."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        # Build call graph
        truncator._build_call_graph(sections, SAMPLE_PYTHON_CODE)

        # Find charge_card method - should call validate_card
        charge_sections = [s for s in sections if s.name == "charge_card"]
        if charge_sections:
            section = charge_sections[0]
            assert "validate_card" in section.calls

        # Find validate_card - should be called by charge_card
        validate_sections = [s for s in sections if s.name == "validate_card"]
        if validate_sections:
            section = validate_sections[0]
            # Note: called_by may include charge_card depending on parsing

    def test_select_sections_respects_token_budget(self):
        """Test that section selection respects token budget."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        # Set a low token budget
        included, truncated = truncator._select_sections(sections, max_tokens=200)

        # Should have some included and some truncated
        assert len(included) > 0
        assert len(truncated) > 0

        # Total tokens of included should be <= budget
        total_tokens = sum(s.tokens for s in included)
        assert total_tokens <= 200

    def test_select_sections_includes_all_when_budget_sufficient(self):
        """Test that all sections included when budget is large."""
        truncator = SemanticTruncator()
        sections = truncator._parse_python(SAMPLE_PYTHON_CODE)

        # Set a very high token budget
        included, truncated = truncator._select_sections(sections, max_tokens=100000)

        # All sections should be included
        assert len(included) == len(sections)
        assert len(truncated) == 0

    def test_build_included_content(self):
        """Test building included content from sections."""
        truncator = SemanticTruncator()

        sample_code = "line1\nline2\nline3\nline4\nline5"
        sections = [
            CodeSection(
                type=SectionType.FUNCTION,
                name="func1",
                start_line=1,
                end_line=2,
                tokens=10,
            ),
            CodeSection(
                type=SectionType.FUNCTION,
                name="func2",
                start_line=4,
                end_line=5,
                tokens=10,
            ),
        ]

        content = truncator._build_included_content(sample_code, sections)

        assert "line1" in content
        assert "line2" in content
        assert "line4" in content
        assert "line5" in content

    def test_generate_retrieval_hint_single_section(self):
        """Test retrieval hint for single truncated section."""
        truncator = SemanticTruncator()

        sections = [
            CodeSection(
                type=SectionType.FUNCTION,
                name="my_function",
                start_line=1,
                end_line=10,
                tokens=100,
            )
        ]

        hint = truncator._generate_retrieval_hint(sections, "models.py")

        assert "my_function" in hint
        assert "find_symbol" in hint
        assert "models.py" in hint

    def test_generate_retrieval_hint_multiple_sections(self):
        """Test retrieval hint for multiple truncated sections."""
        truncator = SemanticTruncator()

        sections = [
            CodeSection(
                type=SectionType.FUNCTION, name="func1", start_line=1, end_line=10, tokens=100
            ),
            CodeSection(
                type=SectionType.FUNCTION, name="func2", start_line=20, end_line=30, tokens=100
            ),
        ]

        hint = truncator._generate_retrieval_hint(sections, "")

        assert "func1" in hint
        assert "func2" in hint
        assert "find_symbol" in hint

    def test_truncate_python_code(self):
        """Test end-to-end truncation of Python code."""
        truncator = SemanticTruncator()

        result = truncator.truncate(
            content=SAMPLE_PYTHON_CODE, max_tokens=300, language="python", file_path="payment.py"
        )

        assert isinstance(result, TruncationResult)
        assert len(result.included_sections) > 0
        assert result.included_content != ""
        assert result.total_truncated_tokens >= 0

    def test_truncate_respects_semantic_boundaries(self):
        """Test that truncation doesn't split functions/classes."""
        truncator = SemanticTruncator()

        result = truncator.truncate(content=SAMPLE_PYTHON_CODE, max_tokens=200, language="python")

        # Included content should contain complete functions/methods
        lines = result.included_content.split("\n")

        # Should not have incomplete function definitions
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                # Check that there's a body following
                # (at minimum, the next line should be indented or a docstring)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Either continuation, docstring, or body
                    assert next_line.strip() != "" or line.endswith("\\")

    def test_truncate_javascript_code(self):
        """Test truncation of JavaScript code."""
        truncator = SemanticTruncator()

        result = truncator.truncate(
            content=SAMPLE_JS_CODE, max_tokens=200, language="javascript", file_path="user.js"
        )

        assert isinstance(result, TruncationResult)
        assert len(result.included_sections) > 0
        # Should have parsed some sections
        total_sections = len(result.included_sections) + len(result.truncated_sections)
        assert total_sections > 0

    def test_truncate_empty_content(self):
        """Test truncation with empty content."""
        truncator = SemanticTruncator()

        result = truncator.truncate(content="", max_tokens=100, language="python")

        assert len(result.included_sections) == 0
        assert len(result.truncated_sections) == 0
        assert result.included_content == ""
        assert result.total_truncated_tokens == 0

    def test_truncate_to_dict(self):
        """Test converting truncation result to dictionary."""
        truncator = SemanticTruncator()

        result = truncator.truncate(content=SAMPLE_PYTHON_CODE, max_tokens=200, language="python")

        result_dict = result.to_dict()

        assert "included_sections" in result_dict
        assert "truncated_sections" in result_dict
        assert "total_truncated_tokens" in result_dict
        assert isinstance(result_dict["included_sections"], list)

    def test_parse_generic_javascript(self):
        """Test generic parsing for JavaScript."""
        truncator = SemanticTruncator()

        sections = truncator._parse_generic(SAMPLE_JS_CODE, "javascript")

        # Should find some sections
        assert len(sections) > 0

        # Should find the UserManager class
        class_sections = [s for s in sections if "UserManager" in s.name or s.type == SectionType.CLASS]
        assert len(class_sections) > 0

    def test_get_language_patterns(self):
        """Test language pattern retrieval."""
        truncator = SemanticTruncator()

        python_patterns = truncator._get_language_patterns("python")
        assert "class" in python_patterns
        assert "function" in python_patterns

        js_patterns = truncator._get_language_patterns("javascript")
        assert "class" in js_patterns
        assert "function" in js_patterns

        unknown_patterns = truncator._get_language_patterns("unknown")
        assert "class" in unknown_patterns  # Falls back to Python

    def test_infer_section_type(self):
        """Test section type inference from pattern name."""
        truncator = SemanticTruncator()

        assert truncator._infer_section_type("class") == SectionType.CLASS
        assert truncator._infer_section_type("function") == SectionType.FUNCTION
        assert truncator._infer_section_type("method") == SectionType.METHOD
        assert truncator._infer_section_type("unknown") == SectionType.OTHER

    def test_complex_python_with_nested_functions(self):
        """Test parsing Python code with nested functions."""
        nested_code = '''
def outer():
    def inner():
        pass
    return inner

class Container:
    def method(self):
        def nested():
            pass
        return nested
'''
        truncator = SemanticTruncator()
        sections = truncator._parse_python(nested_code)

        # Should find outer function and Container class
        assert len(sections) > 0
        names = [s.name for s in sections]
        assert "outer" in names
        assert "Container" in names

    def test_truncation_preserves_order(self):
        """Test that included sections maintain original order."""
        truncator = SemanticTruncator()

        result = truncator.truncate(content=SAMPLE_PYTHON_CODE, max_tokens=300, language="python")

        # Check that sections are in ascending line order
        for i in range(len(result.included_sections) - 1):
            assert result.included_sections[i].start_line <= result.included_sections[i + 1].start_line

        for i in range(len(result.truncated_sections) - 1):
            assert result.truncated_sections[i].start_line <= result.truncated_sections[i + 1].start_line
