"""
Complexity analyzer for code symbols.

Analyzes code complexity using multiple metrics to help determine
when full symbol body should be retrieved vs signature-only mode.
"""
import ast
import logging
import re
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger(__name__)


@dataclass
class ComplexityMetrics:
    """Complexity metrics for a code symbol."""

    cyclomatic_complexity: int
    """Cyclomatic complexity (number of decision points + 1)"""

    nesting_depth: int
    """Maximum nesting depth of control structures"""

    lines_of_code: int
    """Number of non-empty lines in the body"""

    num_branches: int
    """Number of branching statements (if/elif/else, try/except, match/case)"""

    num_loops: int
    """Number of loops (for, while)"""

    has_exception_handling: bool
    """Whether the code contains try/except blocks"""

    has_nested_functions: bool
    """Whether the code contains nested function definitions"""

    has_complex_expressions: bool
    """Whether the code contains complex expressions (chained calls, comprehensions)"""

    @property
    def complexity_score(self) -> float:
        """
        Calculate overall complexity score (0-10 scale).

        Higher scores indicate more complex code that likely needs full body retrieval.
        """
        score = 0.0

        # Cyclomatic complexity contributes up to 3 points
        score += min(self.cyclomatic_complexity / 5.0, 3.0)

        # Nesting depth contributes up to 2 points
        score += min(self.nesting_depth / 2.0, 2.0)

        # Lines of code contributes up to 2 points
        score += min(self.lines_of_code / 50.0, 2.0)

        # Branches contribute up to 1 point
        score += min(self.num_branches / 5.0, 1.0)

        # Loops contribute up to 1 point
        score += min(self.num_loops / 3.0, 1.0)

        # Boolean flags contribute 0.5 each (up to 1.5 total)
        if self.has_exception_handling:
            score += 0.5
        if self.has_nested_functions:
            score += 0.5
        if self.has_complex_expressions:
            score += 0.5

        return min(score, 10.0)

    @property
    def complexity_level(self) -> Literal["low", "medium", "high"]:
        """Get the complexity level category."""
        score = self.complexity_score
        if score < 3.0:
            return "low"
        elif score < 6.0:
            return "medium"
        else:
            return "high"

    def get_flags(self) -> list[str]:
        """Get list of complexity flags/indicators."""
        flags = []

        if self.cyclomatic_complexity > 10:
            flags.append("high_cyclomatic_complexity")
        if self.nesting_depth > 3:
            flags.append("deep_nesting")
        if self.num_branches > 5:
            flags.append("many_branches")
        if self.num_loops > 2:
            flags.append("multiple_loops")
        if self.has_exception_handling:
            flags.append("exception_handling")
        if self.has_nested_functions:
            flags.append("nested_functions")
        if self.has_complex_expressions:
            flags.append("complex_expressions")
        if self.lines_of_code > 100:
            flags.append("long_function")

        return flags

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": round(self.complexity_score, 2),
            "level": self.complexity_level,
            "flags": self.get_flags(),
            "metrics": {
                "cyclomatic_complexity": self.cyclomatic_complexity,
                "nesting_depth": self.nesting_depth,
                "lines_of_code": self.lines_of_code,
                "branches": self.num_branches,
                "loops": self.num_loops,
            }
        }


class ComplexityAnalyzer:
    """Analyzes code complexity for Python code using AST."""

    @staticmethod
    def analyze_python(code: str) -> ComplexityMetrics:
        """
        Analyze Python code complexity.

        :param code: Python source code to analyze
        :return: ComplexityMetrics object
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            log.warning("Failed to parse Python code for complexity analysis")
            # Return default metrics for unparseable code
            return ComplexityAnalyzer._fallback_analysis(code)

        # Initialize counters
        cyclomatic = 1  # Base complexity is 1
        max_nesting = 0
        num_branches = 0
        num_loops = 0
        has_try = False
        has_nested_func = False
        has_complex_expr = False

        # Track nesting level during traversal
        current_nesting = 0

        def visit(node: ast.AST, nesting_level: int) -> None:
            nonlocal cyclomatic, max_nesting, num_branches, num_loops
            nonlocal has_try, has_nested_func, has_complex_expr, current_nesting

            current_nesting = nesting_level
            max_nesting = max(max_nesting, nesting_level)

            # Increment cyclomatic complexity for decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                cyclomatic += 1
                if isinstance(node, (ast.While, ast.For, ast.AsyncFor)):
                    num_loops += 1
                if isinstance(node, ast.If):
                    num_branches += 1

            # Count elif as separate branches
            if isinstance(node, ast.If) and node.orelse:
                # Check if orelse is another If (elif) or just else
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    cyclomatic += 1
                    num_branches += 1

            # Exception handling
            if isinstance(node, ast.Try):
                has_try = True
                cyclomatic += len(node.handlers)
                num_branches += 1

            # Nested functions/classes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if nesting_level > 0:  # Nested definition
                    has_nested_func = True

            # Complex expressions
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                has_complex_expr = True

            # Chained attribute access (e.g., a.b.c.d)
            if isinstance(node, ast.Attribute):
                depth = 0
                current = node
                while isinstance(current, ast.Attribute):
                    depth += 1
                    current = current.value
                if depth > 2:
                    has_complex_expr = True

            # Boolean operators add to complexity
            if isinstance(node, ast.BoolOp):
                cyclomatic += len(node.values) - 1

            # Match/case statements (Python 3.10+)
            if isinstance(node, ast.Match):
                cyclomatic += len(node.cases)
                num_branches += 1

            # Recurse into children with increased nesting for control structures
            for child in ast.iter_child_nodes(node):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.Try)):
                    visit(child, nesting_level + 1)
                else:
                    visit(child, nesting_level)

        # Visit all top-level nodes
        for node in ast.iter_child_nodes(tree):
            visit(node, 0)

        # Count lines of code (non-empty, non-comment)
        lines = [line.strip() for line in code.split('\n')]
        loc = sum(1 for line in lines if line and not line.startswith('#'))

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            nesting_depth=max_nesting,
            lines_of_code=loc,
            num_branches=num_branches,
            num_loops=num_loops,
            has_exception_handling=has_try,
            has_nested_functions=has_nested_func,
            has_complex_expressions=has_complex_expr,
        )

    @staticmethod
    def _fallback_analysis(code: str) -> ComplexityMetrics:
        """
        Fallback analysis using regex patterns when AST parsing fails.
        Less accurate but better than nothing.
        """
        lines = [line.strip() for line in code.split('\n')]
        loc = sum(1 for line in lines if line and not line.startswith('#'))

        # Count control flow keywords
        control_flow_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'match', 'case']
        keyword_counts = {kw: sum(1 for line in lines if re.search(r'\b' + kw + r'\b', line)) for kw in control_flow_keywords}

        # Rough estimates
        cyclomatic = 1 + keyword_counts['if'] + keyword_counts['elif'] + keyword_counts['for'] + keyword_counts['while']
        num_branches = keyword_counts['if'] + keyword_counts['elif'] + keyword_counts['try'] + keyword_counts['match']
        num_loops = keyword_counts['for'] + keyword_counts['while']
        has_try = keyword_counts['try'] > 0
        has_nested_func = bool(re.search(r'def\s+\w+.*:\s*\n\s+.*def\s+\w+', code, re.MULTILINE))
        has_complex_expr = bool(re.search(r'\[.*for.*in.*\]|\{.*for.*in.*\}', code))

        # Estimate nesting by indentation
        max_indent = max((len(line) - len(line.lstrip()) for line in code.split('\n') if line.strip()), default=0)
        nesting_depth = max_indent // 4  # Assume 4-space indentation

        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            nesting_depth=nesting_depth,
            lines_of_code=loc,
            num_branches=num_branches,
            num_loops=num_loops,
            has_exception_handling=has_try,
            has_nested_functions=has_nested_func,
            has_complex_expressions=has_complex_expr,
        )

    @staticmethod
    def analyze(code: str, language: str = "python") -> ComplexityMetrics:
        """
        Analyze code complexity for any supported language.

        :param code: Source code to analyze
        :param language: Programming language (currently only "python" is fully supported)
        :return: ComplexityMetrics object
        """
        if language.lower() == "python":
            return ComplexityAnalyzer.analyze_python(code)
        else:
            # For other languages, use fallback analysis
            log.warning(f"Language {language} not fully supported for complexity analysis, using fallback")
            return ComplexityAnalyzer._fallback_analysis(code)

    @staticmethod
    def should_recommend_full_body(metrics: ComplexityMetrics) -> bool:
        """
        Determine if full body should be recommended based on complexity.

        High complexity code should always show full body to avoid missing important details.
        """
        return metrics.complexity_level == "high"

    @staticmethod
    def get_recommendation(metrics: ComplexityMetrics) -> str:
        """Get human-readable recommendation."""
        if metrics.complexity_level == "high":
            return "complexity_high_suggest_full_body"
        elif metrics.complexity_level == "medium":
            return "complexity_medium_signature_may_suffice"
        else:
            return "complexity_low_signature_sufficient"
