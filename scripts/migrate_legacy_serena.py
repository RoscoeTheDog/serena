#!/usr/bin/env python3
"""
Migration script for legacy .serena/ directories.

This script discovers all projects with legacy .serena/ directories and safely
migrates their data to the centralized storage location (~/.serena/projects/{project-id}/).

Usage:
    python migrate_legacy_serena.py [OPTIONS]

Options:
    --search-paths PATH [PATH ...]  Paths to search for legacy projects (default: current dir)
    --dry-run                       Preview migration without making changes
    --verbose                       Enable detailed logging
    --no-backup                     Skip creating backup archives (not recommended)
    --output PATH                   Write migration report to file (default: stdout)

Examples:
    # Dry run in current directory
    python migrate_legacy_serena.py --dry-run

    # Migrate all projects in ~/projects
    python migrate_legacy_serena.py --search-paths ~/projects

    # Migrate with verbose output and save report
    python migrate_legacy_serena.py --verbose --output migration-report.json
"""

import argparse
import hashlib
import json
import logging
import shutil
import sys
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import serena utilities
try:
    from serena.constants import (
        get_project_identifier,
        get_centralized_project_dir,
        SERENA_MANAGED_DIR_NAME,
    )
except ImportError:
    # Fallback for running without serena installed
    print("Warning: serena package not found. Using fallback implementations.", file=sys.stderr)

    SERENA_MANAGED_DIR_NAME = ".serena"

    def get_project_identifier(project_root: Path) -> str:
        """Fallback implementation."""
        normalized = project_root.resolve()
        path_str = str(normalized).lower()
        hash_obj = hashlib.sha256(path_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]

    def get_legacy_project_dir(project_root: Path) -> Path:
        """Fallback implementation."""
        return project_root / SERENA_MANAGED_DIR_NAME

    def get_centralized_project_dir(project_root: Path) -> Path:
        """Fallback implementation."""
        project_id = get_project_identifier(project_root)
        centralized_dir = Path.home() / ".serena" / "projects" / project_id
        centralized_dir.mkdir(parents=True, exist_ok=True)
        return centralized_dir


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of migrating a single project."""
    project_root: Path
    legacy_dir: Path
    centralized_dir: Path
    success: bool
    error: Optional[str] = None
    files_migrated: int = 0
    backup_path: Optional[Path] = None
    validation_errors: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "project_root": str(self.project_root),
            "legacy_dir": str(self.legacy_dir),
            "centralized_dir": str(self.centralized_dir),
            "success": self.success,
            "error": self.error,
            "files_migrated": self.files_migrated,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "validation_errors": self.validation_errors,
            "skipped_files": self.skipped_files,
        }


@dataclass
class MigrationReport:
    """Overall migration report."""
    timestamp: str
    total_discovered: int = 0
    total_migrated: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    results: List[MigrationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_discovered": self.total_discovered,
                "total_migrated": self.total_migrated,
                "total_failed": self.total_failed,
                "total_skipped": self.total_skipped,
            },
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to pretty JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_human_readable(self) -> str:
        """Convert to human-readable summary."""
        lines = [
            "=" * 80,
            "MIGRATION REPORT",
            "=" * 80,
            f"Timestamp: {self.timestamp}",
            "",
            "SUMMARY:",
            f"  Total projects discovered: {self.total_discovered}",
            f"  Successfully migrated:     {self.total_migrated}",
            f"  Failed:                    {self.total_failed}",
            f"  Skipped:                   {self.total_skipped}",
            "",
            "DETAILS:",
        ]

        for i, result in enumerate(self.results, 1):
            status = "SUCCESS" if result.success else "FAILED"
            lines.append(f"\n{i}. {status}: {result.project_root}")
            lines.append(f"   Legacy dir:      {result.legacy_dir}")
            lines.append(f"   Centralized dir: {result.centralized_dir}")
            lines.append(f"   Files migrated:  {result.files_migrated}")

            if result.backup_path:
                lines.append(f"   Backup created:  {result.backup_path}")

            if result.error:
                lines.append(f"   Error: {result.error}")

            if result.validation_errors:
                lines.append("   Validation errors:")
                for err in result.validation_errors:
                    lines.append(f"     - {err}")

            if result.skipped_files:
                lines.append(f"   Skipped files: {len(result.skipped_files)}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)


class LegacyProjectMigrator:
    """Handles migration of legacy .serena/ directories to centralized storage."""

    def __init__(
        self,
        search_paths: List[Path],
        dry_run: bool = False,
        create_backup: bool = True,
        verbose: bool = False,
    ):
        self.search_paths = [Path(p).resolve() for p in search_paths]
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.verbose = verbose

        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(levelname)s: %(message)s'
        )

    def discover_legacy_projects(self) -> List[Path]:
        """
        Discover all projects with legacy .serena/ directories.

        Returns:
            List of project root directories containing .serena/
        """
        logger.info("Discovering legacy .serena/ directories...")
        legacy_projects = []

        for search_path in self.search_paths:
            if not search_path.exists():
                logger.warning(f"Search path does not exist: {search_path}")
                continue

            logger.debug(f"Searching in: {search_path}")

            # Use rglob to find all .serena directories
            for serena_dir in search_path.rglob(SERENA_MANAGED_DIR_NAME):
                # Skip if it's not a directory
                if not serena_dir.is_dir():
                    continue

                # Skip if it's in the centralized location (~/.serena/projects/)
                if ".serena/projects" in str(serena_dir):
                    logger.debug(f"Skipping centralized storage: {serena_dir}")
                    continue

                project_root = serena_dir.parent

                # Check if this looks like a valid legacy project
                if self._is_valid_legacy_project(serena_dir):
                    logger.info(f"Found legacy project: {project_root}")
                    legacy_projects.append(project_root)
                else:
                    logger.debug(f"Skipping invalid .serena/ dir: {serena_dir}")

        logger.info(f"Discovered {len(legacy_projects)} legacy projects")
        return legacy_projects

    def _is_valid_legacy_project(self, serena_dir: Path) -> bool:
        """
        Check if a .serena/ directory is a valid legacy project.

        A valid legacy project should have at least one of:
        - project.yml file
        - memories/ directory
        """
        has_project_yml = (serena_dir / "project.yml").exists()
        has_memories_dir = (serena_dir / "memories").is_dir()

        return has_project_yml or has_memories_dir

    def validate_project_data(self, legacy_dir: Path) -> List[str]:
        """
        Validate data integrity before migration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check project.yml if it exists
        project_yml = legacy_dir / "project.yml"
        if project_yml.exists():
            if not project_yml.is_file():
                errors.append("project.yml exists but is not a file")
            elif project_yml.stat().st_size == 0:
                errors.append("project.yml is empty")

        # Check memories directory if it exists
        memories_dir = legacy_dir / "memories"
        if memories_dir.exists():
            if not memories_dir.is_dir():
                errors.append("memories exists but is not a directory")

        return errors

    def create_backup_archive(self, legacy_dir: Path) -> Optional[Path]:
        """
        Create a backup archive of the legacy directory.

        Returns:
            Path to backup archive, or None if backup failed
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create backup of {legacy_dir}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{SERENA_MANAGED_DIR_NAME}.backup-{timestamp}.tar.gz"
        backup_path = legacy_dir.parent / backup_name

        try:
            logger.info(f"Creating backup archive: {backup_path}")

            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(legacy_dir, arcname=SERENA_MANAGED_DIR_NAME)

            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def migrate_project(self, project_root: Path) -> MigrationResult:
        """
        Migrate a single project from legacy to centralized storage.

        Args:
            project_root: Root directory of the project

        Returns:
            MigrationResult with migration details
        """
        legacy_dir = get_legacy_project_dir(project_root)
        centralized_dir = get_centralized_project_dir(project_root)

        result = MigrationResult(
            project_root=project_root,
            legacy_dir=legacy_dir,
            centralized_dir=centralized_dir,
            success=False,
        )

        logger.info(f"\nMigrating: {project_root}")
        logger.info(f"  From: {legacy_dir}")
        logger.info(f"  To:   {centralized_dir}")

        # Validate data
        validation_errors = self.validate_project_data(legacy_dir)
        if validation_errors:
            result.validation_errors = validation_errors
            logger.warning(f"Validation warnings: {validation_errors}")

        # Create backup if enabled
        if self.create_backup:
            backup_path = self.create_backup_archive(legacy_dir)
            if backup_path:
                result.backup_path = backup_path
            elif not self.dry_run:
                result.error = "Failed to create backup archive"
                logger.error(f"Migration aborted for {project_root}: backup failed")
                return result

        # Perform migration
        try:
            files_migrated = self._migrate_files(legacy_dir, centralized_dir, result)
            result.files_migrated = files_migrated
            result.success = True

            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate {files_migrated} files")
            else:
                logger.info(f"Successfully migrated {files_migrated} files")

        except Exception as e:
            result.error = str(e)
            logger.error(f"Migration failed: {e}")

        return result

    def _migrate_files(
        self,
        legacy_dir: Path,
        centralized_dir: Path,
        result: MigrationResult
    ) -> int:
        """
        Migrate files from legacy to centralized directory.

        Returns:
            Number of files migrated
        """
        files_migrated = 0

        # Migrate project.yml
        legacy_project_yml = legacy_dir / "project.yml"
        if legacy_project_yml.exists():
            centralized_project_yml = centralized_dir / "project.yml"

            if centralized_project_yml.exists():
                logger.warning(f"Centralized project.yml already exists: {centralized_project_yml}")
                logger.info("Skipping project.yml migration (centralized version takes precedence)")
                result.skipped_files.append("project.yml (already exists)")
            else:
                if not self.dry_run:
                    shutil.copy2(legacy_project_yml, centralized_project_yml)
                    logger.debug(f"Migrated: project.yml")
                files_migrated += 1

        # Migrate memories/ directory
        legacy_memories = legacy_dir / "memories"
        if legacy_memories.is_dir():
            centralized_memories = centralized_dir / "memories"
            centralized_memories.mkdir(exist_ok=True)

            for memory_file in legacy_memories.rglob("*"):
                if memory_file.is_file():
                    # Calculate relative path within memories/
                    rel_path = memory_file.relative_to(legacy_memories)
                    dest_file = centralized_memories / rel_path

                    if dest_file.exists():
                        logger.warning(f"File already exists in centralized storage: {rel_path}")
                        result.skipped_files.append(str(rel_path))
                    else:
                        if not self.dry_run:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(memory_file, dest_file)
                            logger.debug(f"Migrated: memories/{rel_path}")
                        files_migrated += 1

        return files_migrated

    def run(self) -> MigrationReport:
        """
        Run the full migration process.

        Returns:
            MigrationReport with results
        """
        timestamp = datetime.now().isoformat()
        report = MigrationReport(timestamp=timestamp)

        if self.dry_run:
            logger.info("=" * 80)
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("=" * 80)

        # Discover projects
        legacy_projects = self.discover_legacy_projects()
        report.total_discovered = len(legacy_projects)

        if not legacy_projects:
            logger.info("No legacy projects found")
            return report

        # Migrate each project
        for project_root in legacy_projects:
            result = self.migrate_project(project_root)
            report.results.append(result)

            if result.success:
                report.total_migrated += 1
            elif result.skipped_files and not result.error:
                report.total_skipped += 1
            else:
                report.total_failed += 1

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate legacy .serena/ directories to centralized storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--search-paths",
        nargs="+",
        default=["."],
        help="Paths to search for legacy projects (default: current directory)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup archives (not recommended)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Write migration report to file (default: stdout)",
    )

    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Report output format (default: text)",
    )

    args = parser.parse_args()

    # Create migrator
    migrator = LegacyProjectMigrator(
        search_paths=args.search_paths,
        dry_run=args.dry_run,
        create_backup=not args.no_backup,
        verbose=args.verbose,
    )

    # Run migration
    report = migrator.run()

    # Output report
    if args.format == "json":
        output_text = report.to_json()
    else:
        output_text = report.to_human_readable()

    if args.output:
        args.output.write_text(output_text)
        logger.info(f"\nReport written to: {args.output}")
    else:
        print("\n" + output_text)

    # Exit with appropriate code
    if report.total_failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
