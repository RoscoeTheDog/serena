"""Upstream Diff Analyzer

Analyzes git diff between upstream/main and current branch to identify conflicts
in files modified by the fork.

Usage:
    python upstream_diff_analyzer.py [--target-dirs DIR [DIR ...]]
"""
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from serena.util.shell import subprocess_check_output

log = logging.getLogger(__name__)


class UpstreamDiffAnalyzer:
    """Analyzes git differences between fork and upstream."""

    def __init__(self, target_dirs: Optional[List[str]] = None):
        """
        Initialize the analyzer.

        Args:
            target_dirs: List of directories to analyze for conflicts.
                        Defaults to ['src/serena/config/', 'src/serena/tools/', 'src/serena/project.py']
        """
        self.target_dirs = target_dirs or [
            "src/serena/config/",
            "src/serena/tools/",
            "src/serena/project.py"
        ]
        self.upstream_remote = "upstream"
        self.upstream_branch = "main"

    def check_upstream_remote(self) -> bool:
        """Check if upstream remote is configured."""
        try:
            remotes = subprocess_check_output(["git", "remote", "-v"])
            return self.upstream_remote in remotes
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to check git remotes: {e}")
            return False

    def get_merge_base(self) -> Optional[str]:
        """Get the merge base between current branch and upstream/main."""
        try:
            merge_base = subprocess_check_output([
                "git", "merge-base", "HEAD", f"{self.upstream_remote}/{self.upstream_branch}"
            ])
            return merge_base
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to get merge base: {e}")
            return None

    def get_modified_files(self, merge_base: str) -> Dict[str, str]:
        """
        Get files modified in upstream since merge base.

        Args:
            merge_base: The merge base commit hash

        Returns:
            Dictionary mapping file paths to modification status (M=modified, A=added, D=deleted)
        """
        try:
            # Get file status changes from upstream
            output = subprocess_check_output([
                "git", "diff", "--name-status",
                f"{merge_base}..{self.upstream_remote}/{self.upstream_branch}"
            ])

            modified_files = {}
            for line in output.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    status, filepath = parts
                    modified_files[filepath] = status

            return modified_files
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to get modified files: {e}")
            return {}

    def filter_target_files(self, modified_files: Dict[str, str]) -> Dict[str, str]:
        """
        Filter modified files to only include target directories.

        Args:
            modified_files: Dictionary of all modified files

        Returns:
            Dictionary of modified files in target directories
        """
        target_files = {}
        for filepath, status in modified_files.items():
            for target_dir in self.target_dirs:
                # Handle both files and directories
                if filepath.startswith(target_dir) or filepath == target_dir.rstrip('/'):
                    target_files[filepath] = status
                    break

        return target_files

    def get_file_diff(self, filepath: str, merge_base: str) -> Optional[str]:
        """
        Get the line-level diff for a specific file.

        Args:
            filepath: Path to the file
            merge_base: The merge base commit hash

        Returns:
            Diff output or None if file doesn't exist or error occurred
        """
        try:
            diff = subprocess_check_output([
                "git", "diff",
                f"{merge_base}..{self.upstream_remote}/{self.upstream_branch}",
                "--", filepath
            ], strip=False)
            return diff
        except subprocess.CalledProcessError:
            return None

    def analyze(self) -> Dict:
        """
        Run complete upstream diff analysis.

        Returns:
            Dictionary with analysis results containing:
                - merge_base: The merge base commit
                - target_files: Files in target dirs modified by upstream
                - conflicts_found: Boolean indicating if conflicts exist
                - file_diffs: Detailed diffs for each conflicting file
        """
        # Check upstream remote exists
        if not self.check_upstream_remote():
            return {
                "error": f"Upstream remote '{self.upstream_remote}' not configured",
                "conflicts_found": False
            }

        # Get merge base
        merge_base = self.get_merge_base()
        if not merge_base:
            return {
                "error": "Could not determine merge base with upstream/main",
                "conflicts_found": False
            }

        # Get all modified files in upstream
        modified_files = self.get_modified_files(merge_base)
        if not modified_files:
            return {
                "merge_base": merge_base,
                "target_files": {},
                "conflicts_found": False,
                "message": "No files modified in upstream/main"
            }

        # Filter to target directories
        target_files = self.filter_target_files(modified_files)

        # Get detailed diffs for target files
        file_diffs = {}
        for filepath in target_files.keys():
            diff = self.get_file_diff(filepath, merge_base)
            if diff:
                file_diffs[filepath] = diff

        return {
            "merge_base": merge_base,
            "target_files": target_files,
            "conflicts_found": len(target_files) > 0,
            "file_diffs": file_diffs,
            "total_upstream_changes": len(modified_files),
            "target_directory_changes": len(target_files)
        }


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze upstream diff for conflicts")
    parser.add_argument(
        "--target-dirs",
        nargs="+",
        help="Target directories to check for conflicts (default: config/, tools/, project.py)"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Run analysis
    analyzer = UpstreamDiffAnalyzer(target_dirs=args.target_dirs)
    results = analyzer.analyze()

    # Print results
    if "error" in results:
        print(f"ERROR: {results['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"Merge base: {results['merge_base']}")
    print(f"Total upstream changes: {results['total_upstream_changes']}")
    print(f"Changes in target directories: {results['target_directory_changes']}")
    print(f"Conflicts found: {results['conflicts_found']}")

    if results['conflicts_found']:
        print("\nFiles modified in target directories:")
        for filepath, status in results['target_files'].items():
            status_map = {'M': 'Modified', 'A': 'Added', 'D': 'Deleted'}
            print(f"  [{status_map.get(status, status)}] {filepath}")


if __name__ == "__main__":
    main()
