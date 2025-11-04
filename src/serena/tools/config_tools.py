import json

from serena.config.context_mode import SerenaAgentMode
from serena.tools import Tool, ToolMarkerDoesNotRequireActiveProject, ToolMarkerOptional


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
        
        # Check if a parent project was used instead of the requested path
        used_parent = hasattr(active_project, '_used_parent_path') and hasattr(active_project, '_requested_path')
        
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
