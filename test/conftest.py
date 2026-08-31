import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from sensai.util.logging import configure

from serena.constants import SERENA_MANAGED_DIR_IN_HOME, SERENA_MANAGED_DIR_NAME
from serena.project import Project
from serena.util.file_system import GitignoreParser
from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import Language, LanguageServerConfig
from solidlsp.ls_logger import LanguageServerLogger
from solidlsp.settings import SolidLSPSettings

configure(level=logging.ERROR)

# Redirect per-project storage (~/.serena/projects/<id>/) into a throwaway directory for the
# duration of the test session. Without this, every test that loads a Project or constructs a
# MemoriesManager writes into the user's real ~/.serena/projects/ using a hash of a random
# tmpdir, so each run permanently leaks directories that nothing ever cleans up.
#
# This deliberately runs in pytest_configure, i.e. AFTER this module's `serena.constants` import
# above has already bound the import-time constants. Only the lazily-resolved project-storage
# paths follow SERENA_HOME, so the language-server binary cache under the real ~/.serena
# (SERENA_MANAGED_DIR_IN_HOME, used by create_ls below) is still shared and not re-downloaded.
_SERENA_HOME_TMP: str | None = None
_SERENA_HOME_PREV: str | None = None


def pytest_configure(config: pytest.Config) -> None:
    global _SERENA_HOME_TMP, _SERENA_HOME_PREV
    _SERENA_HOME_PREV = os.environ.get("SERENA_HOME")
    _SERENA_HOME_TMP = tempfile.mkdtemp(prefix="serena-test-home-")
    # Mirror the production layout: the managed dir is literally named ".serena", so tests that
    # assert on the shape of a storage path (e.g. that it contains ".serena/projects/") stay valid.
    serena_home = Path(_SERENA_HOME_TMP) / SERENA_MANAGED_DIR_NAME
    serena_home.mkdir(parents=True, exist_ok=True)
    os.environ["SERENA_HOME"] = str(serena_home)


def pytest_unconfigure(config: pytest.Config) -> None:
    if _SERENA_HOME_PREV is None:
        os.environ.pop("SERENA_HOME", None)
    else:
        os.environ["SERENA_HOME"] = _SERENA_HOME_PREV
    if _SERENA_HOME_TMP:
        shutil.rmtree(_SERENA_HOME_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def resources_dir() -> Path:
    """Path to the test resources directory."""
    current_dir = Path(__file__).parent
    return current_dir / "resources"


class LanguageParamRequest:
    param: Language


def get_repo_path(language: Language) -> Path:
    return Path(__file__).parent / "resources" / "repos" / language / "test_repo"


def create_ls(
    language: Language,
    repo_path: str | None = None,
    ignored_paths: list[str] | None = None,
    trace_lsp_communication: bool = False,
    log_level: int = logging.ERROR,
) -> SolidLanguageServer:
    ignored_paths = ignored_paths or []
    if repo_path is None:
        repo_path = str(get_repo_path(language))
    gitignore_parser = GitignoreParser(str(repo_path))
    for spec in gitignore_parser.get_ignore_specs():
        ignored_paths.extend(spec.patterns)
    config = LanguageServerConfig(code_language=language, ignored_paths=ignored_paths, trace_lsp_communication=trace_lsp_communication)
    logger = LanguageServerLogger(log_level=log_level)
    return SolidLanguageServer.create(
        config,
        logger,
        repo_path,
        solidlsp_settings=SolidLSPSettings(solidlsp_dir=SERENA_MANAGED_DIR_IN_HOME, project_data_relative_path=SERENA_MANAGED_DIR_NAME),
    )


def create_default_ls(language: Language) -> SolidLanguageServer:
    repo_path = str(get_repo_path(language))
    return create_ls(language, repo_path)


def create_default_project(language: Language) -> Project:
    repo_path = str(get_repo_path(language))
    return Project.load(repo_path)


@pytest.fixture(scope="session")
def repo_path(request: LanguageParamRequest) -> Path:
    """Get the repository path for a specific language.

    This fixture requires a language parameter via pytest.mark.parametrize:

    Example:
    ```
    @pytest.mark.parametrize("repo_path", [Language.PYTHON], indirect=True)
    def test_python_repo(repo_path):
        assert (repo_path / "src").exists()
    ```

    """
    if not hasattr(request, "param"):
        raise ValueError("Language parameter must be provided via pytest.mark.parametrize")

    language = request.param
    return get_repo_path(language)


@pytest.fixture(scope="session")
def language_server(request: LanguageParamRequest):
    """Create a language server instance configured for the specified language.

    This fixture requires a language parameter via pytest.mark.parametrize:

    Example:
    ```
    @pytest.mark.parametrize("language_server", [Language.PYTHON], indirect=True)
    def test_python_server(language_server: SyncLanguageServer) -> None:
        # Use the Python language server
        pass
    ```

    You can also test multiple languages in a single test:
    ```
    @pytest.mark.parametrize("language_server", [Language.PYTHON, Language.TYPESCRIPT], indirect=True)
    def test_multiple_languages(language_server: SyncLanguageServer) -> None:
        # This test will run once for each language
        pass
    ```

    """
    if not hasattr(request, "param"):
        raise ValueError("Language parameter must be provided via pytest.mark.parametrize")

    language = request.param
    server = create_default_ls(language)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(scope="session")
def project(request: LanguageParamRequest):
    """Create a Project for the specified language.

    This fixture requires a language parameter via pytest.mark.parametrize:

    Example:
    ```
    @pytest.mark.parametrize("project", [Language.PYTHON], indirect=True)
    def test_python_project(project: Project) -> None:
        # Use the Python project to test something
        pass
    ```

    You can also test multiple languages in a single test:
    ```
    @pytest.mark.parametrize("project", [Language.PYTHON, Language.TYPESCRIPT], indirect=True)
    def test_multiple_languages(project: SyncLanguageServer) -> None:
        # This test will run once for each language
        pass
    ```

    """
    if not hasattr(request, "param"):
        raise ValueError("Language parameter must be provided via pytest.mark.parametrize")

    language = request.param
    yield create_default_project(language)
