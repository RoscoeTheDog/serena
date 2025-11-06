import json
import platform
from pathlib import Path
from typing import Any

from serena.config.context_mode import SerenaAgentMode
from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional
from serena.tools.onboarding_helpers import (
    detect_tech_stack,
    find_command_files,
    detect_code_style,
    generate_commands_memory,
    generate_completion_checklist,
)
from serena.constants import (
    get_centralized_project_dir,
    get_project_config_path,
)


class ActivateProjectTool(Tool, ToolMarkerDoesNotRequireActiveProject):
    """
    Activates a project by name.
    """

    def apply(self, project: str) -> str:
        """
        Activates the project with the given name.

        :param project: the name of a registered project to activate or a path to a project directory
        """
        active_project = self.agent.activate_project_from_path_or_name(project)

        # Ensure project.yml exists (in case project was registered but .serena was deleted)
        from pathlib import Path
        project_yml_path = Path(active_project.path_to_project_yml())
        if not project_yml_path.exists():
            # Regenerate project.yml from existing project config
            from serena.config.serena_config import ProjectConfig
            ProjectConfig.autogenerate(
                active_project.project_root,
                project_name=active_project.project_name,
                project_language=active_project.language,
                save_to_disk=True
            )

        # Check if a parent project was used instead of the requested path
        used_parent = hasattr(active_project, '_used_parent_path') and hasattr(active_project, '_requested_path')

        # Check and auto-onboard if needed
        onboarding_status = self._check_and_auto_onboard(active_project)

        if active_project.is_newly_created:
            result_str = (
                f"Created and activated a new project with name '{active_project.project_name}' at {active_project.project_root}, language: {active_project.project_config.language.value}. "
                "You can activate this project later by name.\n"
                f"The project's Serena configuration is in {active_project.path_to_project_yml()}. In particular, you may want to edit the project name and the initial prompt."
            )
            if used_parent:
                result_str = f"Using parent project at {active_project._used_parent_path}\n" + result_str
        else:
            result_str = f"Activated existing project with name '{active_project.project_name}' at {active_project.project_root}, language: {active_project.project_config.language.value}"
            if used_parent:
                result_str = f"Using parent project at {active_project._used_parent_path} (requested: {active_project._requested_path})\n" + result_str

        # Add onboarding status if onboarding was performed
        if onboarding_status["performed"]:
            result_str += "\n\n" + onboarding_status["message"]

        if active_project.project_config.initial_prompt:
            result_str += f"\nAdditional project information:\n {active_project.project_config.initial_prompt}"
        result_str += (
            f"\nAvailable memories:\n {json.dumps(list(self.memories_manager.list_memories(include_metadata=False)))}"
            + "You should not read these memories directly, but rather use the `read_memory` tool to read them later if needed for the task."
        )
        result_str += f"\nAvailable tools:\n {json.dumps(self.agent.get_active_tool_names())}"
        
        # Clean up temporary attributes
        if used_parent:
            delattr(active_project, '_used_parent_path')
            delattr(active_project, '_requested_path')
        
        return result_str

    def _check_and_auto_onboard(self, project) -> dict:
        """
        Check if project needs onboarding and perform it automatically if needed.

        :param project: the activated project
        :return: dict with 'performed' (bool) and 'message' (str)
        """
        from .memory_tools import ListMemoriesTool

        list_memories_tool = self.agent.get_tool(ListMemoriesTool)
        memories = json.loads(list_memories_tool.apply())

        if len(memories) == 0:
            # No memories exist - perform auto-onboarding
            return self._auto_onboard_project(project)
        else:
            return {
                "performed": False,
                "message": f"Project already onboarded ({len(memories)} memories available)"
            }

    def _auto_onboard_project(self, project) -> dict:
        """
        Automatically onboard a project by analyzing files and creating basic memories.

        :param project: the project to onboard
        :return: dict with 'performed' (bool) and 'message' (str)
        """
        from .memory_tools import WriteMemoryTool

        write_memory = self.agent.get_tool(WriteMemoryTool)

        # Detect tech stack using helper functions (implemented in Session 2)
        tech_stack = self._detect_tech_stack(project)

        # Find command files using helper functions (implemented in Session 2)
        commands = self._find_command_files(project)

        # Detect code style hints using helper functions (implemented in Session 2)
        style_info = self._detect_code_style(project)

        # Create project overview memory
        overview = f"""# {project.project_name}

**Language**: {project.language}
**Location**: {project.project_root}
**Tech Stack**: {tech_stack}
**Platform**: {platform.system()}

## Auto-Detected Information

This project was automatically onboarded. The information below was detected from
configuration files and project structure. You may want to supplement this with
additional information as you work with the project.
"""

        write_memory.apply(
            memory_name="project_overview.md",
            content=overview
        )

        # Create suggested commands memory
        commands_md = self._generate_commands_memory(commands, project)
        write_memory.apply(
            memory_name="suggested_commands.md",
            content=commands_md
        )

        # Create code style memory if detected
        if style_info:
            write_memory.apply(
                memory_name="code_style_and_conventions.md",
                content=style_info
            )

        # Create task completion checklist
        completion_checklist = self._generate_completion_checklist(commands)
        write_memory.apply(
            memory_name="task_completion_checklist.md",
            content=completion_checklist
        )

        memories_created = 4 if style_info else 3

        return {
            "performed": True,
            "message": (
                f"✓ Auto-onboarded project (created {memories_created} memories)\n"
                f"  - Detected tech stack: {tech_stack}\n"
                f"  - Found {len(commands)} command sources\n"
                "  - Use `read_memory` to view detailed information"
            )
        }

    def _detect_tech_stack(self, project) -> str:
        """Wrapper for tech stack detection."""
        return detect_tech_stack(project)

    def _find_command_files(self, project) -> dict:
        """Wrapper for command file detection."""
        return find_command_files(project)

    def _detect_code_style(self, project) -> str:
        """Wrapper for code style detection."""
        return detect_code_style(project)

    def _generate_commands_memory(self, commands: dict, project) -> str:
        """Wrapper for commands memory generation."""
        return generate_commands_memory(commands, project)

    def _generate_completion_checklist(self, commands: dict) -> str:
        """Wrapper for completion checklist generation."""
        return generate_completion_checklist(commands)


class RemoveProjectTool(Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional):
    """
    Removes a project from the Serena configuration.
    """

    def apply(self, project_name: str) -> str:
        """
        Removes a project from the Serena configuration.

        :param project_name: Name of the project to remove
        """
        self.agent.serena_config.remove_project(project_name)
        return f"Successfully removed project '{project_name}' from configuration."


class SwitchModesTool(Tool, ToolMarkerOptional):
    """
    Activates modes by providing a list of their names
    """

    def apply(self, modes: list[str]) -> str:
        """
        Activates the desired modes, like ["editing", "interactive"] or ["planning", "one-shot"]

        :param modes: the names of the modes to activate
        """
        mode_instances = [SerenaAgentMode.load(mode) for mode in modes]
        self.agent.set_modes(mode_instances)

        # Inform the Agent about the activated modes and the currently active tools
        result_str = f"Successfully activated modes: {', '.join([mode.name for mode in mode_instances])}" + "\n"
        result_str += "\n".join([mode_instance.prompt for mode_instance in mode_instances]) + "\n"
        result_str += f"Currently active tools: {', '.join(self.agent.get_active_tool_names())}"
        return result_str


class GetCurrentConfigTool(Tool, ToolMarkerOptional):
    """
    Prints the current configuration of the agent, including the active and available projects, tools, contexts, and modes.
    """

    def apply(self) -> str:
        """
        Print the current configuration of the agent, including the active and available projects, tools, contexts, and modes.
        """
        return self.agent.get_current_config_overview()


class GetProjectConfigTool(Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional):
    """
    Retrieve current project configuration from centralized storage.
    Similar to claude-context's get_codebase_config tool.
    """

    def apply(self, project_path: str) -> str:
        """
        Retrieve current project configuration.

        Args:
            project_path: Absolute or relative path to project root

        Returns:
            JSON string containing:
            - project_name: Project name
            - language: Programming language
            - storage_location: "centralized" or "legacy"
            - config_path: Actual path to config file
            - ignored_paths: List of ignored paths
            - read_only: Whether project is read-only
            - ignore_all_files_in_gitignore: Whether to ignore gitignored files
            - initial_prompt: Initial prompt for the project
            - encoding: File encoding
            - excluded_tools: List of excluded tools
            - included_optional_tools: List of included optional tools

        Example:
            get_project_config("/path/to/project")
        """
        from serena.config.serena_config import ProjectConfig
        import yaml

        project_root = Path(project_path).resolve()
        if not project_root.exists():
            return json.dumps({
                "error": f"Project root not found: {project_root}"
            }, indent=2)

        # Check centralized location only
        config_path = get_project_config_path(project_root)

        if not config_path.exists():
            return json.dumps({
                "error": f"No project configuration found at {config_path}",
                "hint": "Use activate_project to create a new project configuration"
            }, indent=2)

        storage_location = "centralized"

        # Load the config
        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            result = {
                "project_name": config_data.get("project_name", project_root.name),
                "language": config_data.get("language", "unknown"),
                "storage_location": storage_location,
                "config_path": str(config_path),
                "ignored_paths": config_data.get("ignored_paths", []),
                "read_only": config_data.get("read_only", False),
                "ignore_all_files_in_gitignore": config_data.get("ignore_all_files_in_gitignore", True),
                "initial_prompt": config_data.get("initial_prompt", ""),
                "encoding": config_data.get("encoding", "utf-8"),
                "excluded_tools": config_data.get("excluded_tools", []),
                "included_optional_tools": config_data.get("included_optional_tools", [])
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to load project configuration: {str(e)}"
            }, indent=2)


class UpdateProjectConfigTool(Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional):
    """
    Update project configuration settings in centralized storage.
    Similar to claude-context's update_codebase_config tool.
    """

    def apply(self, project_path: str, **settings: Any) -> str:
        """
        Update project configuration settings.

        Args:
            project_path: Absolute or relative path to project root
            **settings: Configuration keys to update (e.g., project_name, language, ignored_paths, etc.)

        Returns:
            JSON string with updated configuration

        Valid settings:
            - project_name (str): Project name
            - language (str): Programming language
            - ignored_paths (list): List of paths to ignore
            - read_only (bool): Whether project is read-only
            - ignore_all_files_in_gitignore (bool): Whether to ignore gitignored files
            - initial_prompt (str): Initial prompt for the project
            - encoding (str): File encoding
            - excluded_tools (list): List of tools to exclude
            - included_optional_tools (list): List of optional tools to include

        Example:
            update_project_config("/path/to/project", read_only=True, ignored_paths=["temp/", "cache/"])
        """
        from serena.config.serena_config import ProjectConfig
        from serena.util.general import load_yaml, save_yaml

        project_root = Path(project_path).resolve()
        if not project_root.exists():
            return json.dumps({
                "error": f"Project root not found: {project_root}"
            }, indent=2)

        # Use centralized storage only
        centralized_path = get_project_config_path(project_root)

        # Load existing config
        if not centralized_path.exists():
            return json.dumps({
                "error": f"No project configuration found. Use activate_project to create one first.",
                "hint": f"Expected at: {centralized_path}"
            }, indent=2)

        config_data = load_yaml(centralized_path, preserve_comments=True)

        # Update settings
        for key, value in settings.items():
            if key in ["project_name", "language", "ignored_paths", "read_only",
                      "ignore_all_files_in_gitignore", "initial_prompt", "encoding",
                      "excluded_tools", "included_optional_tools"]:
                config_data[key] = value
            else:
                return json.dumps({
                    "error": f"Invalid setting: {key}",
                    "valid_settings": ["project_name", "language", "ignored_paths", "read_only",
                                      "ignore_all_files_in_gitignore", "initial_prompt", "encoding",
                                      "excluded_tools", "included_optional_tools"]
                }, indent=2)

        # Save updated config
        try:
            save_yaml(str(centralized_path), config_data, preserve_comments=True)

            result = {
                "updated": True,
                "config_path": str(centralized_path),
                "storage_location": "centralized",
                "updated_settings": list(settings.keys()),
                "current_config": {
                    "project_name": config_data.get("project_name"),
                    "language": config_data.get("language"),
                    "ignored_paths": config_data.get("ignored_paths", []),
                    "read_only": config_data.get("read_only", False),
                    "ignore_all_files_in_gitignore": config_data.get("ignore_all_files_in_gitignore", True),
                    "initial_prompt": config_data.get("initial_prompt", ""),
                    "encoding": config_data.get("encoding", "utf-8"),
                    "excluded_tools": config_data.get("excluded_tools", []),
                    "included_optional_tools": config_data.get("included_optional_tools", [])
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to update project configuration: {str(e)}"
            }, indent=2)


class ResetProjectConfigTool(Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional):
    """
    Reset project configuration to safe defaults.
    Similar to claude-context's reset_codebase_config tool.
    """

    def apply(self, project_path: str) -> str:
        """
        Reset project configuration to safe defaults.

        Args:
            project_path: Absolute or relative path to project root

        Returns:
            JSON string with reset configuration

        Note: This will preserve project_name and language but reset all other settings to defaults.

        Example:
            reset_project_config("/path/to/project")
        """
        from serena.config.serena_config import ProjectConfig
        from serena.util.general import load_yaml, save_yaml

        project_root = Path(project_path).resolve()
        if not project_root.exists():
            return json.dumps({
                "error": f"Project root not found: {project_root}"
            }, indent=2)

        centralized_path = get_project_config_path(project_root)

        if not centralized_path.exists():
            return json.dumps({
                "error": f"No project configuration found at {centralized_path}",
                "hint": "Use activate_project to create a new project configuration"
            }, indent=2)

        # Load existing config to preserve name and language
        try:
            config_data = load_yaml(centralized_path, preserve_comments=True)
            project_name = config_data.get("project_name", project_root.name)
            language = config_data.get("language", "python")

            # Reset to defaults
            default_config = {
                "project_name": project_name,
                "language": language,
                "ignored_paths": [],
                "read_only": False,
                "ignore_all_files_in_gitignore": True,
                "initial_prompt": "",
                "encoding": "utf-8",
                "excluded_tools": [],
                "included_optional_tools": []
            }

            # Save reset config
            save_yaml(str(centralized_path), default_config, preserve_comments=False)

            result = {
                "reset": True,
                "config_path": str(centralized_path),
                "storage_location": "centralized",
                "preserved": ["project_name", "language"],
                "current_config": default_config
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "error": f"Failed to reset project configuration: {str(e)}"
            }, indent=2)


class ListProjectConfigsTool(Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional):
    """
    List all configured projects with their configurations.
    Similar to claude-context's list_codebase_configs tool.
    """

    def apply(self) -> str:
        """
        List all configured projects.

        Returns:
            JSON string containing list of projects with:
            - project_name: Project name
            - project_path: Resolved project path (if resolvable)
            - storage_location: "centralized" or "legacy"
            - config_path: Path to config file
            - language: Programming language
            - config_summary: Key configuration settings

        Example:
            list_project_configs()
        """
        import yaml

        projects = []
        centralized_projects_dir = Path.home() / ".serena" / "projects"

        # Scan centralized projects directory
        if centralized_projects_dir.exists():
            for project_dir in centralized_projects_dir.iterdir():
                if project_dir.is_dir():
                    config_path = project_dir / "project.yml"
                    if config_path.exists():
                        try:
                            with open(config_path, encoding="utf-8") as f:
                                config_data = yaml.safe_load(f)

                            # Try to resolve project path from registered projects
                            project_root = None
                            for registered in self.agent.serena_config.projects:
                                if get_centralized_project_dir(Path(registered.path)).name == project_dir.name:
                                    project_root = registered.path
                                    break

                            projects.append({
                                "project_name": config_data.get("project_name", "unknown"),
                                "project_path": str(project_root) if project_root else f"<unresolvable: {project_dir.name}>",
                                "storage_location": "centralized",
                                "config_path": str(config_path),
                                "language": config_data.get("language", "unknown"),
                                "config_summary": {
                                    "read_only": config_data.get("read_only", False),
                                    "ignored_paths_count": len(config_data.get("ignored_paths", [])),
                                    "has_initial_prompt": bool(config_data.get("initial_prompt", "")),
                                    "excluded_tools_count": len(config_data.get("excluded_tools", [])),
                                    "included_optional_tools_count": len(config_data.get("included_optional_tools", []))
                                }
                            })
                        except Exception as e:
                            projects.append({
                                "project_name": "error",
                                "error": f"Failed to load config from {config_path}: {str(e)}"
                            })

        result = {
            "total_projects": len(projects),
            "projects": projects
        }

        return json.dumps(result, indent=2)
