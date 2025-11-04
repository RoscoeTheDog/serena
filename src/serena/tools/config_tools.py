import json
import platform

from serena.config.context_mode import SerenaAgentMode
from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional
from serena.tools.onboarding_helpers import (
    detect_tech_stack,
    find_command_files,
    detect_code_style,
    generate_commands_memory,
    generate_completion_checklist,
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
            f"\nAvailable memories:\n {json.dumps(list(self.memories_manager.list_memories()))}"
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
