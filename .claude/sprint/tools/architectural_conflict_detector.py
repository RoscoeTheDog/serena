"""Architectural Conflict Detector

Detects architectural pattern conflicts between upstream changes and fork enhancements.
Specifically checks for conflicts with:
- Parent inheritance pattern in config module
- Centralized storage pattern in project.py

Usage:
    python architectural_conflict_detector.py --diff-results RESULTS_JSON
"""
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from serena.util.shell import subprocess_check_output

log = logging.getLogger(__name__)


class ArchitecturalPattern:
    """Represents an architectural pattern to check for conflicts."""

    def __init__(self, name: str, description: str, files: List[str], markers: List[str]):
        """
        Initialize pattern.

        Args:
            name: Pattern name (e.g., "centralized_storage")
            description: Human-readable description
            files: Files where pattern is implemented
            markers: Code patterns/strings to search for in diffs
        """
        self.name = name
        self.description = description
        self.files = files
        self.markers = markers


class ArchitecturalConflictDetector:
    """Detects architectural pattern conflicts in upstream changes."""

    def __init__(self):
        """Initialize detector with known fork enhancement patterns."""
        self.patterns = [
            ArchitecturalPattern(
                name="centralized_storage",
                description="Centralized storage pattern in project.py (lines 26-27)",
                files=["src/serena/project.py"],
                markers=[
                    r"storage_dir",
                    r"centralized",
                    r"def\s+get_project_root",
                    r"project\.storage",
                    r"\.serena.*storage"
                ]
            ),
            ArchitecturalPattern(
                name="parent_inheritance",
                description="Parent class inheritance in config module",
                files=[
                    "src/serena/config/base.py",
                    "src/serena/config/__init__.py"
                ],
                markers=[
                    r"class\s+\w+Config\(",
                    r"inherit",
                    r"parent.*config",
                    r"BaseConfig",
                    r"@dataclass.*Config"
                ]
            ),
            ArchitecturalPattern(
                name="config_module_structure",
                description="Config module organization and structure",
                files=[
                    "src/serena/config/",
                ],
                markers=[
                    r"from.*config.*import",
                    r"__init__\.py",
                    r"module.*structure",
                    r"config.*organization"
                ]
            ),
            ArchitecturalPattern(
                name="tools_module_enhancements",
                description="Tools module fork-specific enhancements",
                files=["src/serena/tools/"],
                markers=[
                    r"class.*Tool\(",
                    r"@tool",
                    r"tool.*registration",
                    r"tool.*factory"
                ]
            )
        ]

    def check_pattern_in_diff(self, diff_text: str, pattern: ArchitecturalPattern) -> Dict:
        """
        Check if a diff contains changes that might conflict with a pattern.

        Args:
            diff_text: The git diff output
            pattern: The architectural pattern to check

        Returns:
            Dictionary with conflict detection results
        """
        matches = []
        for marker in pattern.markers:
            # Search for marker in added (+) or removed (-) lines
            for line in diff_text.split('\n'):
                if line.startswith('+') or line.startswith('-'):
                    if re.search(marker, line, re.IGNORECASE):
                        matches.append({
                            "marker": marker,
                            "line": line.strip(),
                            "type": "addition" if line.startswith('+') else "removal"
                        })

        return {
            "pattern": pattern.name,
            "conflicts_detected": len(matches) > 0,
            "matches": matches,
            "severity": "high" if len(matches) > 2 else ("medium" if matches else "none")
        }

    def analyze_file(self, filepath: str, diff_text: str) -> List[Dict]:
        """
        Analyze a file's diff for architectural conflicts.

        Args:
            filepath: Path to the file being analyzed
            diff_text: The git diff output for the file

        Returns:
            List of conflict detection results for matching patterns
        """
        conflicts = []
        for pattern in self.patterns:
            # Check if file matches pattern's target files
            file_matches = False
            for pattern_file in pattern.files:
                if filepath.startswith(pattern_file) or filepath == pattern_file.rstrip('/'):
                    file_matches = True
                    break

            if file_matches:
                result = self.check_pattern_in_diff(diff_text, pattern)
                if result["conflicts_detected"]:
                    result["filepath"] = filepath
                    result["description"] = pattern.description
                    conflicts.append(result)

        return conflicts

    def analyze(self, diff_results: Dict) -> Dict:
        """
        Run complete architectural conflict analysis.

        Args:
            diff_results: Results from UpstreamDiffAnalyzer containing file_diffs

        Returns:
            Dictionary with conflict analysis results
        """
        if "error" in diff_results or not diff_results.get("conflicts_found"):
            return {
                "conflicts_found": False,
                "message": "No upstream changes to analyze"
            }

        all_conflicts = []
        file_diffs = diff_results.get("file_diffs", {})

        for filepath, diff_text in file_diffs.items():
            file_conflicts = self.analyze_file(filepath, diff_text)
            all_conflicts.extend(file_conflicts)

        # Group conflicts by severity
        high_severity = [c for c in all_conflicts if c["severity"] == "high"]
        medium_severity = [c for c in all_conflicts if c["severity"] == "medium"]

        # Extract unique patterns affected
        affected_patterns = list(set(c["pattern"] for c in all_conflicts))

        return {
            "conflicts_found": len(all_conflicts) > 0,
            "total_conflicts": len(all_conflicts),
            "high_severity_count": len(high_severity),
            "medium_severity_count": len(medium_severity),
            "affected_patterns": affected_patterns,
            "conflicts": all_conflicts,
            "recommendation": self._generate_recommendation(all_conflicts)
        }

    def _generate_recommendation(self, conflicts: List[Dict]) -> str:
        """Generate human-readable recommendation based on conflicts."""
        if not conflicts:
            return "No architectural conflicts detected. Safe to proceed with merge."

        high_count = len([c for c in conflicts if c["severity"] == "high"])

        if high_count > 0:
            return (
                f"GATE TRIGGERED: {high_count} high-severity architectural conflicts detected. "
                "Human review REQUIRED before proceeding. Do NOT attempt automated merge."
            )
        else:
            return (
                "Medium-severity conflicts detected. Review recommended before merge. "
                "Conflicts may require manual resolution or pattern adaptation."
            )


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect architectural conflicts in upstream changes")
    parser.add_argument(
        "--diff-results",
        required=True,
        help="Path to JSON file containing upstream diff analysis results"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Load diff results
    try:
        with open(args.diff_results, 'r') as f:
            diff_results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not load diff results: {e}", file=sys.stderr)
        sys.exit(1)

    # Run analysis
    detector = ArchitecturalConflictDetector()
    results = detector.analyze(diff_results)

    # Print results
    print(f"Conflicts found: {results['conflicts_found']}")
    if results['conflicts_found']:
        print(f"Total conflicts: {results['total_conflicts']}")
        print(f"High severity: {results['high_severity_count']}")
        print(f"Medium severity: {results['medium_severity_count']}")
        print(f"\nAffected patterns: {', '.join(results['affected_patterns'])}")
        print(f"\nRecommendation: {results['recommendation']}")

        print("\nDetailed conflicts:")
        for conflict in results['conflicts']:
            print(f"\n  Pattern: {conflict['pattern']}")
            print(f"  File: {conflict['filepath']}")
            print(f"  Severity: {conflict['severity']}")
            print(f"  Description: {conflict['description']}")
            print(f"  Matches: {len(conflict['matches'])}")


if __name__ == "__main__":
    main()
