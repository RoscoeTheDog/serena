"""
Session tracking for phase detection and verbosity control.

This module provides functionality to track tool usage patterns across a session
and detect whether the LLM is in exploration or implementation phase.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal, Optional


class Phase(str, Enum):
    """Detected session phase"""
    EXPLORATION = "exploration"
    IMPLEMENTATION = "implementation"
    MIXED = "mixed"


@dataclass
class ToolCall:
    """Record of a single tool call"""
    tool_name: str
    timestamp: datetime
    is_edit: bool
    is_search: bool
    is_read: bool
    file_path: Optional[str] = None


@dataclass
class SessionTracker:
    """
    Tracks tool usage patterns to detect session phase and recommend verbosity levels.

    Phase Detection Logic:
    - Exploration: High ratio of search/read operations, broad scope, multiple files
    - Implementation: Multiple edits in short time, narrow scope, repeated file access
    - Mixed: Balanced mix of operations

    Verbosity Recommendations:
    - Exploration phase → minimal verbosity (token-efficient)
    - Implementation phase → normal verbosity (more detail)
    - Mixed/uncertain → normal verbosity (safe default)
    """

    tool_history: list[ToolCall] = field(default_factory=list)
    edit_count: int = 0
    search_count: int = 0
    read_count: int = 0
    accessed_files: set[str] = field(default_factory=set)
    recent_window_size: int = 10  # Number of recent calls to consider

    # Configurable thresholds for phase detection
    exploration_search_ratio: float = 3.0  # searches > edits * ratio → exploration
    implementation_edit_ratio: float = 1.0  # edits > searches → implementation
    focused_work_file_threshold: int = 5  # repeated access to same file count

    def record_tool_call(
        self,
        tool_name: str,
        is_edit: bool = False,
        is_search: bool = False,
        is_read: bool = False,
        file_path: Optional[str] = None,
    ) -> None:
        """
        Record a tool call for phase detection.

        :param tool_name: Name of the tool being called
        :param is_edit: Whether this is an edit operation
        :param is_search: Whether this is a search operation
        :param is_read: Whether this is a read operation
        :param file_path: Optional file path for tracking file access patterns
        """
        tool_call = ToolCall(
            tool_name=tool_name,
            timestamp=datetime.now(),
            is_edit=is_edit,
            is_search=is_search,
            is_read=is_read,
            file_path=file_path,
        )
        self.tool_history.append(tool_call)

        if is_edit:
            self.edit_count += 1
        if is_search:
            self.search_count += 1
        if is_read:
            self.read_count += 1
        if file_path:
            self.accessed_files.add(file_path)

    def detect_phase(self) -> Phase:
        """
        Detect current session phase based on recent tool usage patterns.

        Returns:
            Phase enum indicating current phase (exploration, implementation, or mixed)
        """
        if len(self.tool_history) < 3:
            # Too early to determine phase, default to exploration
            return Phase.EXPLORATION

        recent_calls = self.tool_history[-self.recent_window_size:]
        recent_edits = sum(1 for call in recent_calls if call.is_edit)
        recent_searches = sum(1 for call in recent_calls if call.is_search)
        recent_reads = sum(1 for call in recent_calls if call.is_read)

        # Implementation phase: high edit activity
        if recent_edits > 0 and recent_edits > recent_searches * self.implementation_edit_ratio:
            return Phase.IMPLEMENTATION

        # Exploration phase: high search/read activity, low edits
        if (recent_searches + recent_reads) > recent_edits * self.exploration_search_ratio:
            return Phase.EXPLORATION

        # Mixed phase: balanced activity
        return Phase.MIXED

    def is_focused_work(self) -> bool:
        """
        Determine if the LLM is doing focused work on specific files.
        Focused work suggests more detailed output is appropriate.

        Returns:
            True if repeatedly accessing same files, False otherwise
        """
        if len(self.tool_history) < self.focused_work_file_threshold:
            return False

        recent_calls = self.tool_history[-self.recent_window_size:]
        recent_files = [call.file_path for call in recent_calls if call.file_path]

        if not recent_files:
            return False

        # Check if >50% of recent calls access the same file
        from collections import Counter
        file_counts = Counter(recent_files)
        most_common_count = file_counts.most_common(1)[0][1]

        return most_common_count >= self.focused_work_file_threshold

    def recommend_verbosity(self) -> Literal["minimal", "normal", "detailed"]:
        """
        Recommend verbosity level based on detected phase and patterns.

        Returns:
            Recommended verbosity level: "minimal", "normal", or "detailed"
        """
        phase = self.detect_phase()

        # Focused work on specific files → detailed
        if self.is_focused_work():
            return "detailed"

        # Exploration phase → minimal (token-efficient)
        if phase == Phase.EXPLORATION:
            return "minimal"

        # Implementation phase → normal (balance of detail and efficiency)
        if phase == Phase.IMPLEMENTATION:
            return "normal"

        # Mixed or uncertain → normal (safe default)
        return "normal"

    def get_phase_reason(self) -> str:
        """
        Get human-readable explanation for the detected phase.

        Returns:
            String explaining why this phase was detected
        """
        phase = self.detect_phase()
        recent_calls = self.tool_history[-self.recent_window_size:]
        recent_edits = sum(1 for call in recent_calls if call.is_edit)
        recent_searches = sum(1 for call in recent_calls if call.is_search)
        recent_reads = sum(1 for call in recent_calls if call.is_read)

        if phase == Phase.EXPLORATION:
            return f"exploration_phase (searches={recent_searches}, reads={recent_reads}, edits={recent_edits})"
        elif phase == Phase.IMPLEMENTATION:
            return f"implementation_phase (edits={recent_edits}, searches={recent_searches})"
        elif self.is_focused_work():
            return "focused_work (repeated file access)"
        else:
            return "mixed_phase"

    def get_stats(self) -> dict:
        """
        Get current session statistics.

        Returns:
            Dictionary with session statistics
        """
        return {
            "total_calls": len(self.tool_history),
            "edit_count": self.edit_count,
            "search_count": self.search_count,
            "read_count": self.read_count,
            "unique_files": len(self.accessed_files),
            "current_phase": self.detect_phase().value,
            "recommended_verbosity": self.recommend_verbosity(),
        }

    def reset(self) -> None:
        """Reset session tracking (useful for new conversation/session)"""
        self.tool_history.clear()
        self.edit_count = 0
        self.search_count = 0
        self.read_count = 0
        self.accessed_files.clear()
