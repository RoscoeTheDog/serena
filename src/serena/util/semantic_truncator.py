"""
Semantic Truncation with Context Markers

Intelligently truncates code on semantic boundaries (never mid-function/class) with
an inventory of omitted sections and context markers showing relationships.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

log = logging.getLogger(__name__)


class SectionType(StrEnum):
    """Types of semantic sections in code."""

    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    MODULE = "module"
    PROPERTY = "property"
    IMPORT = "import"
    COMMENT = "comment"
    OTHER = "other"


class ComplexityLevel(StrEnum):
    """Complexity levels for sections."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CodeSection:
    """Represents a semantic section of code."""

    type: SectionType
    name: str
    start_line: int
    end_line: int
    tokens: int
    complexity: ComplexityLevel = ComplexityLevel.LOW
    calls: list[str] = field(default_factory=list)
    """Functions/methods this section calls"""
    called_by: list[str] = field(default_factory=list)
    """Functions/methods that call this section"""
    signature: str = ""
    """The signature line(s) of the section"""
    docstring: str = ""
    """The docstring of the section (if any)"""

    @property
    def line_range(self) -> str:
        """Returns line range as a string."""
        if self.start_line == self.end_line:
            return str(self.start_line)
        return f"{self.start_line}-{self.end_line}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "name": self.name,
            "lines": self.line_range,
            "tokens": self.tokens,
            "complexity": self.complexity,
            "calls": self.calls,
            "called_by": self.called_by,
        }


@dataclass
class TruncationResult:
    """Result of semantic truncation."""

    included_sections: list[CodeSection]
    truncated_sections: list[CodeSection]
    included_content: str
    total_truncated_tokens: int
    retrieval_hint: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "included_sections": [s.to_dict() for s in self.included_sections],
            "truncated_sections": [s.to_dict() for s in self.truncated_sections],
            "total_truncated_tokens": self.total_truncated_tokens,
            "retrieval_hint": self.retrieval_hint,
        }


class SemanticTruncator:
    """
    Intelligently truncates code on semantic boundaries with context markers.

    Never splits functions/classes mid-definition. Provides inventory of truncated
    sections with context markers showing relationships (calls, references).
    """

    def __init__(self, token_estimator=None):
        """
        Initialize semantic truncator.

        Args:
            token_estimator: Optional token estimation function (defaults to chars/4)
        """
        self.token_estimator = token_estimator or (lambda text: len(text) // 4)

    def truncate(
        self,
        content: str,
        max_tokens: int,
        language: Literal["python", "javascript", "typescript", "go", "rust", "java", "cpp", "unknown"] = "python",
        file_path: str = "",
    ) -> TruncationResult:
        """
        Truncate content on semantic boundaries with context markers.

        Args:
            content: The code content to truncate
            max_tokens: Maximum tokens to include
            language: Programming language (defaults to python)
            file_path: Optional file path for retrieval hints

        Returns:
            TruncationResult with included/truncated sections and context markers
        """
        # Parse content into sections based on language
        if language == "python":
            sections = self._parse_python(content)
        else:
            # Fallback to line-based semantic parsing for other languages
            sections = self._parse_generic(content, language)

        # Build call graph for context markers
        self._build_call_graph(sections, content)

        # Select sections to include based on token budget
        included, truncated = self._select_sections(sections, max_tokens)

        # Build included content
        included_content = self._build_included_content(content, included)

        # Calculate total truncated tokens
        total_truncated = sum(s.tokens for s in truncated)

        # Generate retrieval hint
        retrieval_hint = self._generate_retrieval_hint(truncated, file_path)

        return TruncationResult(
            included_sections=included,
            truncated_sections=truncated,
            included_content=included_content,
            total_truncated_tokens=total_truncated,
            retrieval_hint=retrieval_hint,
        )

    def _parse_python(self, content: str) -> list[CodeSection]:
        """Parse Python code using AST."""
        sections = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    section = self._extract_python_section(node, content)
                    if section:
                        sections.append(section)

        except SyntaxError as e:
            log.debug(f"Syntax error parsing Python code: {e}")
            # Fall back to generic parsing
            return self._parse_generic(content, "python")

        return sections

    def _extract_python_section(self, node: ast.AST, content: str) -> CodeSection | None:
        """Extract section information from Python AST node."""
        lines = content.split("\n")

        if isinstance(node, ast.ClassDef):
            section_type = SectionType.CLASS
            name = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine if it's a method or function based on parent
            section_type = SectionType.FUNCTION
            name = node.name
        else:
            return None

        start_line = node.lineno
        end_line = node.end_lineno or start_line

        # Extract signature (first line or until ':')
        signature_lines = []
        for i in range(start_line - 1, min(start_line + 5, len(lines))):
            signature_lines.append(lines[i])
            if ":" in lines[i] and not lines[i].strip().endswith("\\"):
                break
        signature = "\n".join(signature_lines).strip()

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Calculate tokens
        section_content = "\n".join(lines[start_line - 1 : end_line])
        tokens = self.token_estimator(section_content)

        # Estimate complexity (simple heuristic based on lines and nesting)
        num_lines = end_line - start_line + 1
        if num_lines < 10:
            complexity = ComplexityLevel.LOW
        elif num_lines < 30:
            complexity = ComplexityLevel.MEDIUM
        else:
            complexity = ComplexityLevel.HIGH

        return CodeSection(
            type=section_type,
            name=name,
            start_line=start_line,
            end_line=end_line,
            tokens=tokens,
            complexity=complexity,
            signature=signature,
            docstring=docstring,
        )

    def _parse_generic(self, content: str, language: str) -> list[CodeSection]:
        """
        Generic semantic parsing for languages without AST support.

        Uses regex patterns to detect function/class boundaries.
        """
        sections = []
        lines = content.split("\n")

        # Language-specific patterns
        patterns = self._get_language_patterns(language)

        current_section = None
        brace_count = 0

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Check for section start
            for pattern_name, pattern in patterns.items():
                match = re.match(pattern, stripped)
                if match:
                    # Save previous section if exists
                    if current_section:
                        current_section.end_line = i - 1
                        sections.append(current_section)

                    # Start new section
                    section_type = self._infer_section_type(pattern_name)
                    name = match.group(1) if match.groups() else "unknown"

                    current_section = CodeSection(
                        type=section_type,
                        name=name,
                        start_line=i,
                        end_line=i,
                        tokens=0,
                        signature=stripped,
                    )
                    break

            # Track braces for section boundaries
            if current_section:
                brace_count += stripped.count("{") - stripped.count("}")

                # End section when braces balance (for C-like languages)
                if brace_count == 0 and "{" in stripped:
                    current_section.end_line = i
                    section_content = "\n".join(lines[current_section.start_line - 1 : i])
                    current_section.tokens = self.token_estimator(section_content)
                    sections.append(current_section)
                    current_section = None

        # Add final section if exists
        if current_section:
            current_section.end_line = len(lines)
            section_content = "\n".join(lines[current_section.start_line - 1 :])
            current_section.tokens = self.token_estimator(section_content)
            sections.append(current_section)

        return sections

    def _get_language_patterns(self, language: str) -> dict[str, str]:
        """Get regex patterns for detecting semantic boundaries by language."""
        patterns = {
            "python": {
                "class": r"^class\s+(\w+)",
                "function": r"^def\s+(\w+)",
                "async_function": r"^async\s+def\s+(\w+)",
            },
            "javascript": {
                "class": r"^class\s+(\w+)",
                "function": r"^function\s+(\w+)",
                "arrow_function": r"^const\s+(\w+)\s*=.*=>",
                "method": r"^(\w+)\s*\(.*\)\s*\{",
            },
            "typescript": {
                "class": r"^class\s+(\w+)",
                "function": r"^function\s+(\w+)",
                "arrow_function": r"^const\s+(\w+):\s*.*=.*=>",
                "method": r"^(\w+)\s*\(.*\):.*\{",
            },
            "go": {
                "function": r"^func\s+(\w+)",
                "method": r"^func\s+\(\w+\s+\*?\w+\)\s+(\w+)",
            },
            "rust": {
                "function": r"^fn\s+(\w+)",
                "impl": r"^impl\s+(\w+)",
            },
            "java": {
                "class": r"^(?:public|private|protected)?\s*class\s+(\w+)",
                "method": r"^(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(",
            },
            "cpp": {
                "class": r"^class\s+(\w+)",
                "function": r"^\w+\s+(\w+)\s*\(",
            },
        }

        return patterns.get(language, patterns["python"])

    def _infer_section_type(self, pattern_name: str) -> SectionType:
        """Infer section type from pattern name."""
        if "class" in pattern_name:
            return SectionType.CLASS
        elif "method" in pattern_name:
            return SectionType.METHOD
        elif "function" in pattern_name or "fn" in pattern_name:
            return SectionType.FUNCTION
        else:
            return SectionType.OTHER

    def _build_call_graph(self, sections: list[CodeSection], content: str) -> None:
        """
        Build call graph to populate context markers (calls, called_by).

        Analyzes function calls within each section to detect relationships.
        """
        section_names = {s.name for s in sections}

        for section in sections:
            # Extract section content
            lines = content.split("\n")
            section_content = "\n".join(lines[section.start_line - 1 : section.end_line])

            # Find function/method calls in this section
            # Pattern matches: identifier followed by '('
            call_pattern = r"\b(\w+)\s*\("
            matches = re.findall(call_pattern, section_content)

            # Filter to only include calls to other sections we've parsed
            section.calls = [m for m in set(matches) if m in section_names and m != section.name]

        # Build reverse mapping (called_by)
        for section in sections:
            for call_name in section.calls:
                # Find the section with this name and add to its called_by
                for target in sections:
                    if target.name == call_name:
                        target.called_by.append(section.name)

    def _select_sections(self, sections: list[CodeSection], max_tokens: int) -> tuple[list[CodeSection], list[CodeSection]]:
        """
        Select sections to include based on token budget.

        Strategy:
        1. Include small sections first (most information density)
        2. Include sections with high complexity (likely important)
        3. Include sections that are called by already-included sections
        4. Stop when token budget exhausted
        """
        # Sort by token count (ascending) and complexity (descending)
        sorted_sections = sorted(sections, key=lambda s: (s.tokens, -1 if s.complexity == ComplexityLevel.HIGH else 0))

        included = []
        truncated = []
        current_tokens = 0

        for section in sorted_sections:
            if current_tokens + section.tokens <= max_tokens:
                included.append(section)
                current_tokens += section.tokens
            else:
                truncated.append(section)

        # Sort back to original order (by line number)
        included.sort(key=lambda s: s.start_line)
        truncated.sort(key=lambda s: s.start_line)

        return included, truncated

    def _build_included_content(self, content: str, sections: list[CodeSection]) -> str:
        """Build the included content from selected sections."""
        if not sections:
            return ""

        lines = content.split("\n")
        included_lines = []

        for section in sections:
            # Add section content
            section_lines = lines[section.start_line - 1 : section.end_line]
            included_lines.extend(section_lines)
            # Add separator between sections
            included_lines.append("")

        return "\n".join(included_lines)

    def _generate_retrieval_hint(self, truncated: list[CodeSection], file_path: str) -> str:
        """Generate hint for retrieving truncated sections."""
        if not truncated:
            return ""

        if len(truncated) == 1:
            section = truncated[0]
            if file_path:
                return f"To see the truncated section '{section.name}', use: find_symbol('{section.name}', relative_path='{file_path}', output_format='body')"
            else:
                return f"To see the truncated section '{section.name}', use: find_symbol('{section.name}', output_format='body')"

        # Multiple truncated sections
        section_names = ", ".join(f"'{s.name}'" for s in truncated[:3])
        if len(truncated) > 3:
            section_names += f", and {len(truncated) - 3} more"

        if file_path:
            return f"To see truncated sections ({section_names}), use: find_symbol('<name>', relative_path='{file_path}', output_format='body')"
        else:
            return f"To see truncated sections ({section_names}), use: find_symbol('<name>', output_format='body')"
