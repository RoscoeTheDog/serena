"""
Unit tests for SessionTracker class.

Tests phase detection, verbosity recommendation, and session tracking functionality.
"""

import pytest
from serena.util.session_tracker import Phase, SessionTracker, ToolCall


class TestSessionTracker:
    """Test suite for SessionTracker class"""

    def test_init(self):
        """Test SessionTracker initialization"""
        tracker = SessionTracker()
        assert tracker.edit_count == 0
        assert tracker.search_count == 0
        assert tracker.read_count == 0
        assert len(tracker.tool_history) == 0
        assert len(tracker.accessed_files) == 0

    def test_record_tool_call_edit(self):
        """Test recording edit tool calls"""
        tracker = SessionTracker()
        tracker.record_tool_call("replace_symbol_body", is_edit=True, file_path="models.py")

        assert tracker.edit_count == 1
        assert tracker.search_count == 0
        assert tracker.read_count == 0
        assert len(tracker.tool_history) == 1
        assert "models.py" in tracker.accessed_files

        call = tracker.tool_history[0]
        assert call.tool_name == "replace_symbol_body"
        assert call.is_edit is True
        assert call.is_search is False
        assert call.is_read is False
        assert call.file_path == "models.py"

    def test_record_tool_call_search(self):
        """Test recording search tool calls"""
        tracker = SessionTracker()
        tracker.record_tool_call("find_symbol", is_search=True)

        assert tracker.edit_count == 0
        assert tracker.search_count == 1
        assert tracker.read_count == 0
        assert len(tracker.tool_history) == 1

    def test_record_tool_call_read(self):
        """Test recording read tool calls"""
        tracker = SessionTracker()
        tracker.record_tool_call("get_symbols_overview", is_read=True, file_path="api.py")

        assert tracker.edit_count == 0
        assert tracker.search_count == 0
        assert tracker.read_count == 1
        assert len(tracker.tool_history) == 1
        assert "api.py" in tracker.accessed_files

    def test_detect_phase_early_session(self):
        """Test phase detection with <3 tool calls (should default to exploration)"""
        tracker = SessionTracker()
        tracker.record_tool_call("find_symbol", is_search=True)
        tracker.record_tool_call("get_symbols_overview", is_read=True)

        phase = tracker.detect_phase()
        assert phase == Phase.EXPLORATION

    def test_detect_phase_exploration(self):
        """Test phase detection for exploration phase (high search/read ratio)"""
        tracker = SessionTracker()

        # Simulate exploration: lots of searches and reads, few edits
        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)
        for i in range(5):
            tracker.record_tool_call(f"read_{i}", is_read=True)
        tracker.record_tool_call("edit_1", is_edit=True)

        phase = tracker.detect_phase()
        assert phase == Phase.EXPLORATION

    def test_detect_phase_implementation(self):
        """Test phase detection for implementation phase (high edit ratio)"""
        tracker = SessionTracker()

        # Simulate implementation: lots of edits, fewer searches
        for i in range(8):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)
        for i in range(2):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        phase = tracker.detect_phase()
        assert phase == Phase.IMPLEMENTATION

    def test_detect_phase_mixed(self):
        """Test phase detection for mixed phase (balanced activity)"""
        tracker = SessionTracker()

        # Simulate mixed phase: balanced edits and searches
        for i in range(5):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)
        for i in range(5):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        phase = tracker.detect_phase()
        assert phase == Phase.MIXED

    def test_is_focused_work_false_early(self):
        """Test focused work detection with too few calls"""
        tracker = SessionTracker()
        for i in range(3):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path="same.py")

        assert tracker.is_focused_work() is False

    def test_is_focused_work_true(self):
        """Test focused work detection with repeated file access"""
        tracker = SessionTracker()

        # Access same file multiple times (>= threshold)
        for i in range(6):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path="models.py")

        assert tracker.is_focused_work() is True

    def test_is_focused_work_false_diverse(self):
        """Test focused work detection with diverse file access"""
        tracker = SessionTracker()

        # Access different files
        for i in range(10):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path=f"file{i}.py")

        assert tracker.is_focused_work() is False

    def test_recommend_verbosity_exploration(self):
        """Test verbosity recommendation for exploration phase"""
        tracker = SessionTracker()

        # Simulate exploration
        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        verbosity = tracker.recommend_verbosity()
        assert verbosity == "minimal"

    def test_recommend_verbosity_implementation(self):
        """Test verbosity recommendation for implementation phase"""
        tracker = SessionTracker()

        # Simulate implementation
        for i in range(8):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)
        tracker.record_tool_call("search_1", is_search=True)

        verbosity = tracker.recommend_verbosity()
        assert verbosity == "normal"

    def test_recommend_verbosity_focused_work(self):
        """Test verbosity recommendation for focused work (should override phase)"""
        tracker = SessionTracker()

        # Simulate focused work on one file
        for i in range(6):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path="models.py")

        verbosity = tracker.recommend_verbosity()
        assert verbosity == "detailed"

    def test_recommend_verbosity_mixed(self):
        """Test verbosity recommendation for mixed phase"""
        tracker = SessionTracker()

        # Simulate mixed phase
        for i in range(5):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)
        for i in range(5):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        verbosity = tracker.recommend_verbosity()
        assert verbosity == "normal"

    def test_get_phase_reason_exploration(self):
        """Test phase reason explanation for exploration"""
        tracker = SessionTracker()

        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        reason = tracker.get_phase_reason()
        assert "exploration_phase" in reason
        assert "searches=" in reason

    def test_get_phase_reason_implementation(self):
        """Test phase reason explanation for implementation"""
        tracker = SessionTracker()

        for i in range(8):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)

        reason = tracker.get_phase_reason()
        assert "implementation_phase" in reason
        assert "edits=" in reason

    def test_get_phase_reason_focused(self):
        """Test phase reason explanation for focused work"""
        tracker = SessionTracker()

        for i in range(6):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path="models.py")

        reason = tracker.get_phase_reason()
        assert "focused_work" in reason

    def test_get_stats(self):
        """Test getting session statistics"""
        tracker = SessionTracker()

        tracker.record_tool_call("edit_1", is_edit=True, file_path="models.py")
        tracker.record_tool_call("search_1", is_search=True)
        tracker.record_tool_call("read_1", is_read=True, file_path="api.py")

        stats = tracker.get_stats()
        assert stats["total_calls"] == 3
        assert stats["edit_count"] == 1
        assert stats["search_count"] == 1
        assert stats["read_count"] == 1
        assert stats["unique_files"] == 2
        assert "current_phase" in stats
        assert "recommended_verbosity" in stats

    def test_reset(self):
        """Test resetting session tracker"""
        tracker = SessionTracker()

        tracker.record_tool_call("edit_1", is_edit=True, file_path="models.py")
        tracker.record_tool_call("search_1", is_search=True)
        tracker.record_tool_call("read_1", is_read=True)

        assert len(tracker.tool_history) == 3

        tracker.reset()

        assert len(tracker.tool_history) == 0
        assert tracker.edit_count == 0
        assert tracker.search_count == 0
        assert tracker.read_count == 0
        assert len(tracker.accessed_files) == 0

    def test_custom_thresholds(self):
        """Test custom threshold configuration"""
        tracker = SessionTracker(
            exploration_search_ratio=5.0,
            implementation_edit_ratio=2.0,
            focused_work_file_threshold=3,
        )

        # With custom thresholds
        for i in range(6):
            tracker.record_tool_call(f"search_{i}", is_search=True)
        tracker.record_tool_call("edit_1", is_edit=True)

        # Should still be exploration with higher threshold
        phase = tracker.detect_phase()
        assert phase == Phase.EXPLORATION

    def test_recent_window_only(self):
        """Test that only recent calls (within window) affect phase detection"""
        tracker = SessionTracker(recent_window_size=5)

        # Old history: many searches
        for i in range(10):
            tracker.record_tool_call(f"old_search_{i}", is_search=True)

        # Recent history (last 5): mostly edits
        for i in range(5):
            tracker.record_tool_call(f"recent_edit_{i}", is_edit=True)

        # Should detect implementation based on recent window
        phase = tracker.detect_phase()
        assert phase == Phase.IMPLEMENTATION

    def test_multiple_file_tracking(self):
        """Test tracking multiple unique files"""
        tracker = SessionTracker()

        files = ["models.py", "api.py", "utils.py", "config.py"]
        for file_path in files:
            tracker.record_tool_call(f"read_{file_path}", is_read=True, file_path=file_path)

        assert len(tracker.accessed_files) == 4
        for file_path in files:
            assert file_path in tracker.accessed_files

    def test_phase_transition_exploration_to_implementation(self):
        """Test phase transition from exploration to implementation"""
        tracker = SessionTracker()

        # Start with exploration
        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        assert tracker.detect_phase() == Phase.EXPLORATION

        # Transition to implementation
        for i in range(8):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)

        assert tracker.detect_phase() == Phase.IMPLEMENTATION

    def test_edge_case_no_file_path(self):
        """Test tool calls without file paths"""
        tracker = SessionTracker()

        tracker.record_tool_call("some_tool", is_search=True, file_path=None)
        tracker.record_tool_call("another_tool", is_read=True, file_path=None)

        assert len(tracker.accessed_files) == 0
        assert len(tracker.tool_history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
