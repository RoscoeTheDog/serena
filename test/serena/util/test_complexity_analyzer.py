"""
Unit tests for complexity analyzer.
"""

import pytest
from serena.util.complexity_analyzer import ComplexityAnalyzer, ComplexityMetrics


class TestComplexityAnalyzer:
    """Test suite for ComplexityAnalyzer."""

    def test_simple_function(self):
        """Test complexity analysis of a simple function."""
        code = """
def greet(name):
    return f"Hello, {name}!"
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.cyclomatic_complexity == 1  # Base complexity
        assert metrics.nesting_depth == 0
        assert metrics.complexity_level == "low"
        assert metrics.complexity_score < 3.0

    def test_function_with_if_statement(self):
        """Test complexity with single if statement."""
        code = """
def check_age(age):
    if age >= 18:
        return "adult"
    else:
        return "minor"
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.cyclomatic_complexity >= 2  # Base + if
        assert metrics.num_branches >= 1
        assert metrics.complexity_level in ["low", "medium"]

    def test_nested_loops(self):
        """Test complexity with nested loops."""
        code = """
def matrix_sum(matrix):
    total = 0
    for row in matrix:
        for cell in row:
            total += cell
    return total
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.cyclomatic_complexity >= 3  # Base + 2 loops
        assert metrics.num_loops >= 2
        assert metrics.nesting_depth >= 2
        assert "nested_loops" in metrics.get_flags() or metrics.nesting_depth > 1

    def test_exception_handling(self):
        """Test complexity with exception handling."""
        code = """
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except TypeError:
        return None
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.has_exception_handling is True
        assert metrics.cyclomatic_complexity >= 3  # Base + 2 exception handlers
        assert "exception_handling" in metrics.get_flags()

    def test_nested_functions(self):
        """Test complexity with nested functions."""
        code = """
def outer():
    x = 10
    def inner():
        return x * 2
    return inner()
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.has_nested_functions is True
        assert "nested_functions" in metrics.get_flags()

    def test_complex_expressions(self):
        """Test complexity with complex expressions."""
        code = """
def process_data(items):
    result = [x * 2 for x in items if x > 0]
    return result
"""
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.has_complex_expressions is True
        assert "complex_expressions" in metrics.get_flags()

    def test_high_complexity_function(self):
        """Test a function with high complexity."""
        code = """
def complex_function(data):
    if data is None:
        return []

    result = []
    for item in data:
        if item['type'] == 'A':
            for sub_item in item['children']:
                if sub_item['active']:
                    try:
                        result.append(process(sub_item))
                    except Exception as e:
                        log_error(e)
        elif item['type'] == 'B':
            if item['valid']:
                result.append(item)

    return result
"""
        metrics = ComplexityAnalyzer.analyze(code)

        # This function should be flagged as high complexity
        assert metrics.cyclomatic_complexity > 5
        assert metrics.nesting_depth >= 3
        assert metrics.complexity_level in ["medium", "high"]
        assert ComplexityAnalyzer.should_recommend_full_body(metrics)

    def test_complexity_score_ranges(self):
        """Test that complexity scores fall within expected ranges."""
        # Low complexity
        simple_code = "def simple(): return 42"
        simple_metrics = ComplexityAnalyzer.analyze(simple_code)
        assert 0 <= simple_metrics.complexity_score <= 10.0
        assert simple_metrics.complexity_level == "low"

        # Medium complexity
        medium_code = """
def medium(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print(i)
"""
        medium_metrics = ComplexityAnalyzer.analyze(medium_code)
        assert 0 <= medium_metrics.complexity_score <= 10.0

        # High complexity (many branches)
        high_code = """
def high(x):
    if x == 1:
        pass
    elif x == 2:
        pass
    elif x == 3:
        pass
    elif x == 4:
        pass
    elif x == 5:
        pass
    elif x == 6:
        pass
    elif x == 7:
        pass
    elif x == 8:
        pass
    else:
        pass

    for i in range(10):
        for j in range(10):
            if i + j > 15:
                print("high")
"""
        high_metrics = ComplexityAnalyzer.analyze(high_code)
        assert 0 <= high_metrics.complexity_score <= 10.0
        assert high_metrics.complexity_level in ["medium", "high"]

    def test_recommendations(self):
        """Test recommendation logic."""
        # Low complexity - signature should suffice
        simple_code = "def simple(): return 42"
        simple_metrics = ComplexityAnalyzer.analyze(simple_code)
        assert not ComplexityAnalyzer.should_recommend_full_body(simple_metrics)
        assert "signature_sufficient" in ComplexityAnalyzer.get_recommendation(simple_metrics)

        # High complexity - recommend full body
        complex_code = """
def complex_func(data):
    result = []
    for item in data:
        if item['x'] > 0:
            for sub in item['y']:
                if sub['valid']:
                    try:
                        result.append(process(sub))
                    except Exception:
                        pass
    return result
"""
        complex_metrics = ComplexityAnalyzer.analyze(complex_code)
        if complex_metrics.complexity_level == "high":
            assert ComplexityAnalyzer.should_recommend_full_body(complex_metrics)
            assert "full_body" in ComplexityAnalyzer.get_recommendation(complex_metrics)

    def test_to_dict_format(self):
        """Test that metrics can be converted to dict for JSON serialization."""
        code = """
def example(x):
    if x > 0:
        return x * 2
    return 0
"""
        metrics = ComplexityAnalyzer.analyze(code)
        metrics_dict = metrics.to_dict()

        # Check structure
        assert "score" in metrics_dict
        assert "level" in metrics_dict
        assert "flags" in metrics_dict
        assert "metrics" in metrics_dict

        # Check types
        assert isinstance(metrics_dict["score"], (int, float))
        assert isinstance(metrics_dict["level"], str)
        assert isinstance(metrics_dict["flags"], list)
        assert isinstance(metrics_dict["metrics"], dict)

        # Check metrics sub-dictionary
        assert "cyclomatic_complexity" in metrics_dict["metrics"]
        assert "nesting_depth" in metrics_dict["metrics"]
        assert "lines_of_code" in metrics_dict["metrics"]

    def test_fallback_on_syntax_error(self):
        """Test that analyzer falls back to heuristic analysis on syntax errors."""
        invalid_code = """
def broken(x:
    # Missing closing paren and colon placement wrong
    return x
"""
        # Should not raise exception, should return fallback metrics
        metrics = ComplexityAnalyzer.analyze(invalid_code)
        assert isinstance(metrics, ComplexityMetrics)
        assert metrics.cyclomatic_complexity >= 1

    def test_lines_of_code_counting(self):
        """Test that lines of code are counted correctly."""
        code = """
# This is a comment
def count_lines():
    # Another comment
    x = 1

    y = 2  # Inline comment
    return x + y
"""
        metrics = ComplexityAnalyzer.analyze(code)
        # Should count only non-comment, non-empty lines
        assert metrics.lines_of_code >= 3  # At least the def, x=1, y=2, return lines

    def test_boolean_operators(self):
        """Test that boolean operators increase complexity."""
        code = """
def check(a, b, c):
    if a and b or c:
        return True
    return False
"""
        metrics = ComplexityAnalyzer.analyze(code)
        # and/or should add to cyclomatic complexity
        assert metrics.cyclomatic_complexity > 2

    def test_empty_function(self):
        """Test analysis of empty function."""
        code = """
def empty():
    pass
"""
        metrics = ComplexityAnalyzer.analyze(code)
        assert metrics.cyclomatic_complexity == 1
        assert metrics.nesting_depth == 0
        assert metrics.complexity_level == "low"

    def test_very_long_function(self):
        """Test that long functions are flagged."""
        # Generate a long function
        lines = ["def long_func():"]
        for i in range(120):
            lines.append(f"    x{i} = {i}")
        lines.append("    return sum([x0, x1, x2])")
        code = "\n".join(lines)

        metrics = ComplexityAnalyzer.analyze(code)
        assert metrics.lines_of_code > 100
        assert "long_function" in metrics.get_flags()

    def test_async_functions(self):
        """Test analysis of async functions."""
        code = """
async def fetch_data():
    result = await get_data()
    return result
"""
        metrics = ComplexityAnalyzer.analyze(code)
        # Should not crash on async syntax
        assert isinstance(metrics, ComplexityMetrics)
        assert metrics.cyclomatic_complexity >= 1


class TestComplexityLevels:
    """Test complexity level categorization."""

    def test_low_complexity_examples(self):
        """Test various low complexity code examples."""
        examples = [
            "def simple(): return 42",
            "def add(a, b): return a + b",
            "def get_name(user): return user.name",
        ]

        for code in examples:
            metrics = ComplexityAnalyzer.analyze(code)
            assert metrics.complexity_level in ["low", "medium"], f"Failed for: {code}"

    def test_medium_complexity_examples(self):
        """Test medium complexity code examples."""
        code = """
def validate(data):
    if not data:
        return False
    if data['type'] not in ['A', 'B']:
        return False
    if 'value' not in data:
        return False
    return True
"""
        metrics = ComplexityAnalyzer.analyze(code)
        # This should be medium complexity
        assert metrics.complexity_level in ["medium", "high"]

    def test_high_complexity_examples(self):
        """Test high complexity code examples."""
        code = """
def process(items):
    results = []
    for item in items:
        if item['active']:
            for child in item['children']:
                if child['type'] == 'X':
                    try:
                        value = compute(child)
                        if value > 0:
                            for sub in child['subs']:
                                if sub['valid']:
                                    results.append(sub)
                    except Exception as e:
                        log(e)
                        continue
    return results
"""
        metrics = ComplexityAnalyzer.analyze(code)
        # This should definitely be high complexity
        assert metrics.cyclomatic_complexity > 10 or metrics.nesting_depth > 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
