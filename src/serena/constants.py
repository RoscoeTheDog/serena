import hashlib
import os
from pathlib import Path

_repo_root_path = Path(__file__).parent.parent.parent.resolve()
_serena_pkg_path = Path(__file__).parent.resolve()

SERENA_MANAGED_DIR_NAME = ".serena"


def _resolve_serena_home() -> Path:
    """
    Resolve Serena's managed home directory, honouring the SERENA_HOME override.

    SERENA_HOME is resolved on every call (not cached at import time) so that tests and
    embedding applications can redirect all project storage to a scratch directory without
    depending on module import order. Semantics match SerenaPaths: unset or blank means
    "use the default location".

    Returns:
        Path to the managed home dir (``$SERENA_HOME`` if set, else ``~/.serena``)
    """
    home_dir = os.environ.get("SERENA_HOME")
    if home_dir is None or home_dir.strip() == "":
        return Path.home() / ".serena"
    return Path(home_dir.strip()).expanduser()


_serena_in_home_managed_dir = _resolve_serena_home()

SERENA_MANAGED_DIR_IN_HOME = str(_serena_in_home_managed_dir)

# TODO: Path-related constants should be moved to SerenaPaths; don't add further constants here.
REPO_ROOT = str(_repo_root_path)
PROMPT_TEMPLATES_DIR_INTERNAL = str(_serena_pkg_path / "resources" / "config" / "prompt_templates")
PROMPT_TEMPLATES_DIR_IN_USER_HOME = str(_serena_in_home_managed_dir / "prompt_templates")
SERENAS_OWN_CONTEXT_YAMLS_DIR = str(_serena_pkg_path / "resources" / "config" / "contexts")
"""The contexts that are shipped with the Serena package, i.e. the default contexts."""
USER_CONTEXT_YAMLS_DIR = str(_serena_in_home_managed_dir / "contexts")
"""Contexts defined by the user. If a name of a context matches a name of a context in SERENAS_OWN_CONTEXT_YAMLS_DIR, the user context will override the default one."""
SERENAS_OWN_MODE_YAMLS_DIR = str(_serena_pkg_path / "resources" / "config" / "modes")
"""The modes that are shipped with the Serena package, i.e. the default modes."""
USER_MODE_YAMLS_DIR = str(_serena_in_home_managed_dir / "modes")
"""Modes defined by the user. If a name of a mode matches a name of a mode in SERENAS_OWN_MODE_YAMLS_DIR, the user mode will override the default one."""
INTERNAL_MODE_YAMLS_DIR = str(_serena_pkg_path / "resources" / "config" / "internal_modes")
"""Internal modes, never overridden by user modes."""
SERENA_DASHBOARD_DIR = str(_serena_pkg_path / "resources" / "dashboard")
SERENA_ICON_DIR = str(_serena_pkg_path / "resources" / "icons")

DEFAULT_ENCODING = "utf-8"
DEFAULT_CONTEXT = "desktop-app"
DEFAULT_MODES = ("interactive", "editing")

PROJECT_TEMPLATE_FILE = str(_serena_pkg_path / "resources" / "project.template.yml")
SERENA_CONFIG_TEMPLATE_FILE = str(_serena_pkg_path / "resources" / "serena_config.template.yml")

SERENA_LOG_FORMAT = "%(levelname)-5s %(asctime)-15s [%(threadName)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"


# Centralized Project Storage Helpers
# All project data is stored in ~/.serena/projects/{project-id}/
# Legacy {project_root}/.serena/ directories are no longer supported

def get_project_identifier(project_root: Path) -> str:
    """
    Generate a deterministic project identifier from absolute path.

    Uses SHA256 hash (first 16 chars) to create a unique, deterministic identifier
    for each project. This ensures:
    - Same project always gets same ID (deterministic)
    - No path length issues
    - No special character problems
    - Collision-resistant (16 hex chars = 64 bits)
    - Cross-platform compatible
    - Anonymous (doesn't reveal project path)

    Args:
        project_root: Absolute path to project root

    Returns:
        16-character hex string (first 16 chars of SHA256 hash)

    Example:
        >>> get_project_identifier(Path("/home/user/projects/myapp"))
        "a1b2c3d4e5f6g7h8"
        >>> get_project_identifier(Path("C:\\Users\\Admin\\Documents\\GitHub\\serena"))
        "f9e8d7c6b5a4321"
    """
    # Normalize path (resolve symlinks, convert to absolute)
    normalized = project_root.resolve()

    # Hash the string representation (lowercase for case-insensitive FS)
    path_str = str(normalized).lower()
    hash_obj = hashlib.sha256(path_str.encode('utf-8'))

    # Return first 16 hex characters
    return hash_obj.hexdigest()[:16]


def get_centralized_projects_root() -> Path:
    """
    Get the root directory holding all per-project storage directories.

    Resolved on every call so that a SERENA_HOME override applies regardless of when it was
    set. This is a pure path computation: the directory is NOT created here.

    Returns:
        Path to ``$SERENA_HOME/projects`` (default ``~/.serena/projects``)
    """
    return _resolve_serena_home() / "projects"


def get_centralized_project_dir(project_root: Path) -> Path:
    """
    Get the centralized directory for a project's Serena data.

    This directory is located at ~/.serena/projects/{project-id}/ and contains:
    - project.yml (project configuration)
    - memories/ (project-specific memories)
    - cache/ (language server caches)

    This is a pure path computation: the directory is NOT created here. Callers that
    write into it are responsible for creating it (e.g. via mkdir(parents=True, exist_ok=True)),
    so that read-only queries do not litter ~/.serena/projects/ with empty directories.

    Args:
        project_root: Absolute path to project root

    Returns:
        Path to ~/.serena/projects/{project-id}/

    Example:
        >>> get_centralized_project_dir(Path("/home/user/myapp"))
        Path("/home/user/.serena/projects/a1b2c3d4e5f6g7h8")
    """
    project_id = get_project_identifier(project_root)
    return get_centralized_projects_root() / project_id


def get_project_config_path(project_root: Path) -> Path:
    """
    Get path to centralized project.yml configuration file.

    Args:
        project_root: Absolute path to project root

    Returns:
        Path to ~/.serena/projects/{project-id}/project.yml

    Example:
        >>> get_project_config_path(Path("/home/user/myapp"))
        Path("/home/user/.serena/projects/a1b2c3d4e5f6g7h8/project.yml")
    """
    return get_centralized_project_dir(project_root) / "project.yml"


def get_project_memories_path(project_root: Path) -> Path:
    """
    Get path to centralized memories directory.

    This is a pure path computation: the directory is NOT created here (see
    get_centralized_project_dir); writers create it on demand.

    Args:
        project_root: Absolute path to project root

    Returns:
        Path to ~/.serena/projects/{project-id}/memories/

    Example:
        >>> get_project_memories_path(Path("/home/user/myapp"))
        Path("/home/user/.serena/projects/a1b2c3d4e5f6g7h8/memories")
    """
    return get_centralized_project_dir(project_root) / "memories"


