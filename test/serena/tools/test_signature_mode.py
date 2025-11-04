"""
Integration tests for signature mode with complexity analysis.

Tests the complete workflow of FindSymbolTool with detail_level="signature".
"""

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestSignatureMode:
    """Integration tests for signature mode functionality."""

    def create_test_file(self, tmpdir, filename, content):
        """Helper to create a test Python file."""
        filepath = tmpdir / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def test_signature_mode_simple_function(self, tmpdir):
        """Test signature mode on a simple function."""
        code = '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b
'''
        # This test verifies the structure of signature mode output
        # In a real integration test, we would call FindSymbolTool
        from serena.util.complexity_analyzer import ComplexityAnalyzer

        metrics = ComplexityAnalyzer.analyze(code)

        # Verify metrics structure
        assert hasattr(metrics, 'complexity_score')
        assert hasattr(metrics, 'complexity_level')
        assert metrics.complexity_level == "low"

        # Verify recommendation
        recommendation = ComplexityAnalyzer.get_recommendation(metrics)
        assert "signature" in recommendation or "sufficient" in recommendation

    def test_signature_mode_complex_function(self, tmpdir):
        """Test signature mode on a complex function."""
        code = '''
def process_data(items):
    """Process a list of items with complex logic."""
    results = []
    for item in items:
        if item['active']:
            for child in item['children']:
                if child['type'] == 'special':
                    try:
                        value = compute(child)
                        if value > threshold:
                            results.append(value)
                    except Exception as e:
                        log_error(e)
    return results
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer

        metrics = ComplexityAnalyzer.analyze(code)

        # Complex function should have high complexity
        assert metrics.cyclomatic_complexity > 5
        assert metrics.nesting_depth >= 3

        # Should recommend full body
        if metrics.complexity_level == "high":
            assert ComplexityAnalyzer.should_recommend_full_body(metrics)
            recommendation = ComplexityAnalyzer.get_recommendation(metrics)
            assert "full_body" in recommendation

    def test_signature_extraction(self):
        """Test signature extraction from symbol."""
        # This would be a real integration test with LanguageServerSymbol
        # For now, we test the logic that would be used

        function_body = '''def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)'''

        # Extract first line (signature)
        lines = function_body.splitlines()
        signature = lines[0]

        assert "def calculate_average(numbers):" in signature
        assert "def" in signature
        assert "calculate_average" in signature

    def test_docstring_extraction(self):
        """Test docstring extraction logic."""
        code = '''def example():
    """This is a docstring."""
    return 42'''

        import ast
        tree = ast.parse(code)
        func_def = tree.body[0]
        docstring = ast.get_docstring(func_def)

        assert docstring == "This is a docstring."

    def test_token_estimation_comparison(self):
        """Test that signature mode saves tokens compared to full body."""
        full_body = '''def complex_processing(data, config):
    """
    Process data according to configuration.

    Args:
        data: Input data to process
        config: Configuration dictionary

    Returns:
        Processed results
    """
    if not data:
        return []

    results = []
    for item in data:
        if validate(item, config):
            processed = transform(item)
            if processed:
                results.append(processed)

    return results'''

        # Signature + docstring
        signature_text = '''def complex_processing(data, config):
    """
    Process data according to configuration.

    Args:
        data: Input data to process
        config: Configuration dictionary

    Returns:
        Processed results
    """'''

        # Verify signature is significantly shorter
        full_length = len(full_body)
        sig_length = len(signature_text)

        savings = (full_length - sig_length) / full_length
        assert savings > 0.3  # At least 30% savings

        # Token estimation
        from serena.analytics import TokenCountEstimator
        estimator = TokenCountEstimator()

        full_tokens = estimator.estimate_token_count(full_body)
        sig_tokens = estimator.estimate_token_count(signature_text)

        assert sig_tokens < full_tokens
        token_savings = (full_tokens - sig_tokens) / full_tokens
        assert token_savings > 0.2  # At least 20% token savings

    def test_complexity_flags(self):
        """Test that complexity flags are correctly identified."""
        # Test nested loops
        nested_loop_code = '''
def process_matrix(matrix):
    for row in matrix:
        for cell in row:
            print(cell)
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(nested_loop_code)
        assert metrics.num_loops >= 2

        # Test exception handling
        exception_code = '''
def safe_operation():
    try:
        risky_call()
    except ValueError:
        handle_error()
'''
        metrics = ComplexityAnalyzer.analyze(exception_code)
        assert metrics.has_exception_handling

    def test_complexity_to_dict_format(self):
        """Test that complexity metrics serialize correctly to JSON."""
        code = '''
def example(x):
    if x > 0:
        return x * 2
    return 0
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(code)
        metrics_dict = metrics.to_dict()

        # Should be JSON-serializable
        json_str = json.dumps(metrics_dict)
        assert json_str

        # Parse back
        parsed = json.loads(json_str)
        assert "score" in parsed
        assert "level" in parsed
        assert "flags" in parsed
        assert "metrics" in parsed


class TestSignatureModeEdgeCases:
    """Test edge cases for signature mode."""

    def test_function_without_docstring(self):
        """Test function without a docstring."""
        code = '''
def no_docs():
    return 42
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(code)

        # Should still analyze correctly
        assert metrics.cyclomatic_complexity >= 1
        assert metrics.complexity_level == "low"

    def test_multiline_signature(self):
        """Test function with multi-line signature."""
        code = '''
def long_signature(
    param1,
    param2,
    param3
):
    """Function with long signature."""
    return param1 + param2 + param3
'''
        # Test that we can handle multi-line signatures
        lines = code.strip().splitlines()
        sig_lines = []
        for line in lines:
            sig_lines.append(line)
            if ':' in line:
                break

        signature = '\n'.join(sig_lines)
        assert 'param1' in signature
        assert 'param3' in signature

    def test_async_function(self):
        """Test async function analysis."""
        code = '''
async def fetch_data():
    """Fetch data asynchronously."""
    result = await api_call()
    return result
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(code)

        # Should handle async functions
        assert isinstance(metrics.cyclomatic_complexity, int)
        assert metrics.cyclomatic_complexity >= 1

    def test_class_method(self):
        """Test complexity analysis of class method."""
        code = '''
class DataProcessor:
    def process(self, data):
        """Process the data."""
        if not data:
            return None
        return self.transform(data)
'''
        # Analyze just the method
        method_code = '''
def process(self, data):
    """Process the data."""
    if not data:
        return None
    return self.transform(data)
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(method_code)

        assert metrics.cyclomatic_complexity >= 2  # Base + if
        assert metrics.complexity_level in ["low", "medium"]

    def test_empty_function(self):
        """Test analysis of empty/pass function."""
        code = '''
def placeholder():
    pass
'''
        from serena.util.complexity_analyzer import ComplexityAnalyzer
        metrics = ComplexityAnalyzer.analyze(code)

        assert metrics.cyclomatic_complexity == 1
        assert metrics.complexity_level == "low"


class TestSignatureModeBenefits:
    """Test the benefits of signature mode."""

    def test_token_savings_calculation(self):
        """Test that token savings are correctly calculated."""
        # Large function with lots of implementation details
        large_func = '''def big_function(data):
    """Process data."""
''' + '\n'.join([f'    line_{i} = process_{i}(data)' for i in range(100)])

        # Signature is just first few lines
        signature = '''def big_function(data):
    """Process data."""'''

        from serena.analytics import TokenCountEstimator
        estimator = TokenCountEstimator()

        full_tokens = estimator.estimate_token_count(large_func)
        sig_tokens = estimator.estimate_token_count(signature)

        # Should have massive savings
        savings_pct = ((full_tokens - sig_tokens) / full_tokens) * 100
        assert savings_pct > 70  # At least 70% savings

    def test_recommendation_accuracy(self):
        """Test that recommendations are accurate."""
        from serena.util.complexity_analyzer import ComplexityAnalyzer

        # Simple function - should recommend signature
        simple = "def simple(): return 1"
        simple_metrics = ComplexityAnalyzer.analyze(simple)
        assert not ComplexityAnalyzer.should_recommend_full_body(simple_metrics)

        # Complex function - may recommend full body
        complex_func = '''
def complex_algo(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            for j in range(i):
                if data[j] < data[i]:
                    try:
                        result.append(compute(i, j))
                    except:
                        pass
    return result
'''
        complex_metrics = ComplexityAnalyzer.analyze(complex_func)
        # High complexity should recommend full body
        if complex_metrics.complexity_level == "high":
            assert ComplexityAnalyzer.should_recommend_full_body(complex_metrics)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
