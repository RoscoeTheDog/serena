"""
Unit tests for pattern extraction functionality in text_utils.py
Tests the extract_usage_pattern function with various code patterns.
"""

import pytest

from serena.text_utils import extract_usage_pattern


class TestExtractUsagePattern:
    """Tests for extract_usage_pattern function"""

    # Test import statements
    def test_extract_from_import(self):
        """Test extraction from 'from X import Y' statements"""
        line = "from auth import authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "import authenticate"

    def test_extract_from_import_with_module_path(self):
        """Test extraction from imports with dotted module paths"""
        line = "from auth.services import authenticate, login"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "import authenticate"

    def test_extract_from_import_multiple(self):
        """Test extraction when symbol is one of multiple imports"""
        line = "from utils import foo, bar, baz"
        result = extract_usage_pattern(line, "bar")
        assert result == "import bar"

    def test_extract_import_statement(self):
        """Test extraction from 'import X' statements"""
        line = "import authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "import authenticate"

    # Test function calls
    def test_extract_simple_function_call(self):
        """Test extraction of simple function call"""
        line = "result = authenticate(user, password)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(user, password)"

    def test_extract_function_call_no_args(self):
        """Test extraction of function call with no arguments"""
        line = "x = get_config()"
        result = extract_usage_pattern(line, "get_config")
        assert result == "get_config()"

    def test_extract_function_call_with_whitespace(self):
        """Test extraction handles whitespace around parentheses"""
        line = "result = process  (  data  )"
        result = extract_usage_pattern(line, "process")
        assert result == "process  (  data  )"

    # Test method calls
    def test_extract_method_call(self):
        """Test extraction of method call on object"""
        line = "user.authenticate(password)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "user.authenticate(password)"

    def test_extract_chained_method_call(self):
        """Test extraction of chained method call"""
        line = "user.profile.get_name()"
        result = extract_usage_pattern(line, "get_name")
        assert result == "user.profile.get_name()"

    def test_extract_nested_method_call(self):
        """Test extraction of deeply nested method call"""
        line = "app.services.auth.validate(token)"
        result = extract_usage_pattern(line, "validate")
        assert result == "app.services.auth.validate(token)"

    # Test property access
    def test_extract_property_access(self):
        """Test extraction of property access"""
        line = "x = user.username"
        result = extract_usage_pattern(line, "username")
        # Should capture the property access
        assert "username" in result

    # Test assignments
    def test_extract_assignment(self):
        """Test extraction from assignment statement"""
        line = "handler = authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "handler = authenticate"

    def test_extract_assignment_with_type(self):
        """Test extraction from typed assignment"""
        line = "func: Callable = authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert "authenticate" in result

    # Test function arguments
    def test_extract_as_argument(self):
        """Test extraction when symbol is used as argument"""
        line = "register_handler(authenticate)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "register_handler(authenticate)"

    def test_extract_as_argument_multiple(self):
        """Test extraction when symbol is one of multiple arguments"""
        line = "setup(authenticate, authorize, validate)"
        result = extract_usage_pattern(line, "authenticate")
        assert "authenticate" in result

    # Test return statements
    def test_extract_return_statement(self):
        """Test extraction from return statement"""
        line = "return authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "return authenticate"

    def test_extract_return_with_call(self):
        """Test extraction from return with function call"""
        line = "return authenticate(user)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(user)"

    # Test edge cases
    def test_extract_empty_line(self):
        """Test extraction from empty line returns None"""
        result = extract_usage_pattern("", "foo")
        assert result is None

    def test_extract_empty_symbol_name(self):
        """Test extraction with empty symbol name returns None"""
        result = extract_usage_pattern("some code", "")
        assert result is None

    def test_extract_symbol_not_found(self):
        """Test extraction when symbol not in line returns None"""
        result = extract_usage_pattern("some other code", "foo")
        assert result is None

    def test_extract_from_comment(self):
        """Test extraction from commented code"""
        line = "# TODO: use authenticate here"
        result = extract_usage_pattern(line, "authenticate")
        # Should still find the symbol even in comments
        assert result == "authenticate"

    def test_extract_with_leading_whitespace(self):
        """Test extraction handles leading whitespace"""
        line = "    result = foo.bar(x)"
        result = extract_usage_pattern(line, "bar")
        assert result == "foo.bar(x)"

    def test_extract_with_trailing_whitespace(self):
        """Test extraction handles trailing whitespace"""
        line = "result = foo()   "
        result = extract_usage_pattern(line, "foo")
        assert result == "foo()"

    # Test complex patterns
    def test_extract_complex_chained_call(self):
        """Test extraction from complex chained calls"""
        line = "result = obj.method1().method2(arg).method3()"
        result = extract_usage_pattern(line, "method2")
        # Should capture the specific method in the chain
        assert "method2(arg)" in result

    def test_extract_nested_function_calls(self):
        """Test extraction from nested function calls"""
        line = "result = outer(inner(authenticate(user)))"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(user)"

    def test_extract_multiline_context(self):
        """Test extraction handles code that might span multiple lines"""
        line = "authenticate("
        result = extract_usage_pattern(line, "authenticate")
        # Should still extract what's available
        assert "authenticate(" in result

    # Test language-specific patterns
    def test_extract_python_decorator(self):
        """Test extraction from Python decorator"""
        line = "@authenticate"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate"

    def test_extract_python_list_comprehension(self):
        """Test extraction from list comprehension"""
        line = "[authenticate(u) for u in users]"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(u)"

    def test_extract_python_lambda(self):
        """Test extraction from lambda expression"""
        line = "lambda x: authenticate(x)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(x)"

    # Test symbol name with special characters
    def test_extract_symbol_with_underscore(self):
        """Test extraction of symbol with underscore"""
        line = "result = get_user_name()"
        result = extract_usage_pattern(line, "get_user_name")
        assert result == "get_user_name()"

    def test_extract_symbol_with_numbers(self):
        """Test extraction of symbol with numbers"""
        line = "validate2(data)"
        result = extract_usage_pattern(line, "validate2")
        assert result == "validate2(data)"

    # Test partial matches (should not match)
    def test_no_extract_partial_match(self):
        """Test that partial matches don't incorrectly match"""
        line = "result = authenticate_user()"
        result = extract_usage_pattern(line, "authenticate")
        # Should not match 'authenticate' as part of 'authenticate_user'
        # The function should only match whole words
        assert result is None or "authenticate_user" in result


class TestPatternExtractionIntegration:
    """Integration tests for pattern extraction with real-world code samples"""

    def test_extract_from_django_view(self):
        """Test extraction from typical Django view code"""
        line = "return authenticate(request, username=username, password=password)"
        result = extract_usage_pattern(line, "authenticate")
        assert "authenticate(request, username=username, password=password)" == result

    def test_extract_from_flask_route(self):
        """Test extraction from Flask route"""
        line = "@app.route('/login')"
        result = extract_usage_pattern(line, "route")
        assert "route('/login')" in result

    def test_extract_from_class_method(self):
        """Test extraction from class method call"""
        line = "self.authenticate(credentials)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "self.authenticate(credentials)"

    def test_extract_from_async_call(self):
        """Test extraction from async function call"""
        line = "await authenticate(user)"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate(user)"

    def test_extract_from_type_annotation(self):
        """Test extraction from type annotation"""
        line = "def login(auth: authenticate) -> bool:"
        result = extract_usage_pattern(line, "authenticate")
        assert result == "authenticate"
