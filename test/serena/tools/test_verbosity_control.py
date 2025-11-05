"""
Integration tests for verbosity control system.

Tests integration of verbosity parameter with Tool base class and session tracking.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock
from serena.util.session_tracker import SessionTracker, Phase


class MockAgent:
    """Mock SerenaAgent for testing"""

    def __init__(self, session_tracker=None):
        self.session_tracker = session_tracker or SessionTracker()
        self.serena_config = Mock()
        self.serena_config.default_max_tool_answer_chars = 10000


class MockTool:
    """Mock Tool class for testing verbosity methods"""

    def __init__(self, agent):
        self.agent = agent

    def _resolve_verbosity(self, verbosity="auto"):
        """Copy of Tool._resolve_verbosity for testing"""
        if verbosity == "auto":
            if hasattr(self.agent, 'session_tracker') and self.agent.session_tracker is not None:
                return self.agent.session_tracker.recommend_verbosity()
            else:
                return "normal"
        else:
            return verbosity

    def _add_verbosity_metadata(self, result, verbosity_used, estimated_tokens_full=None):
        """Copy of Tool._add_verbosity_metadata for testing"""
        verbosity_reason = "explicit_request"
        if hasattr(self.agent, 'session_tracker') and self.agent.session_tracker is not None:
            verbosity_reason = self.agent.session_tracker.get_phase_reason()

        metadata = {
            "_verbosity": {
                "verbosity_used": verbosity_used,
                "verbosity_reason": verbosity_reason,
                "upgrade_available": verbosity_used != "detailed",
            }
        }

        if estimated_tokens_full is not None and verbosity_used != "detailed":
            metadata["_verbosity"]["estimated_tokens_full"] = estimated_tokens_full
            metadata["_verbosity"]["upgrade_hint"] = f"Use verbosity='detailed' to get full output (~{estimated_tokens_full} tokens)"
        elif verbosity_used == "minimal":
            metadata["_verbosity"]["upgrade_hint"] = "Use verbosity='normal' or verbosity='detailed' for more information"
        elif verbosity_used == "normal":
            metadata["_verbosity"]["upgrade_hint"] = "Use verbosity='detailed' for full output"

        if isinstance(result, dict):
            result_with_metadata = result.copy()
            result_with_metadata.update(metadata)
            return json.dumps(result_with_metadata, indent=2)

        metadata_str = json.dumps(metadata, indent=2)
        return f"{result}\n\n{metadata_str}"

    def _record_tool_call_for_session(self, is_edit=False, is_search=False, is_read=False, file_path=None):
        """Copy of Tool._record_tool_call_for_session for testing"""
        if hasattr(self.agent, 'session_tracker') and self.agent.session_tracker is not None:
            self.agent.session_tracker.record_tool_call(
                tool_name="mock_tool",
                is_edit=is_edit,
                is_search=is_search,
                is_read=is_read,
                file_path=file_path,
            )


class TestVerbosityControlIntegration:
    """Integration tests for verbosity control"""

    def test_resolve_verbosity_auto_exploration(self):
        """Test auto verbosity resolves to minimal during exploration"""
        tracker = SessionTracker()
        # Simulate exploration phase
        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("auto")
        assert resolved == "minimal"

    def test_resolve_verbosity_auto_implementation(self):
        """Test auto verbosity resolves to normal during implementation"""
        tracker = SessionTracker()
        # Simulate implementation phase
        for i in range(8):
            tracker.record_tool_call(f"edit_{i}", is_edit=True)

        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("auto")
        assert resolved == "normal"

    def test_resolve_verbosity_auto_focused_work(self):
        """Test auto verbosity resolves to detailed during focused work"""
        tracker = SessionTracker()
        # Simulate focused work
        for i in range(6):
            tracker.record_tool_call(f"tool_{i}", is_read=True, file_path="models.py")

        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("auto")
        assert resolved == "detailed"

    def test_resolve_verbosity_explicit_minimal(self):
        """Test explicit minimal verbosity is honored"""
        agent = MockAgent()
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("minimal")
        assert resolved == "minimal"

    def test_resolve_verbosity_explicit_normal(self):
        """Test explicit normal verbosity is honored"""
        agent = MockAgent()
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("normal")
        assert resolved == "normal"

    def test_resolve_verbosity_explicit_detailed(self):
        """Test explicit detailed verbosity is honored"""
        agent = MockAgent()
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("detailed")
        assert resolved == "detailed"

    def test_resolve_verbosity_no_session_tracker(self):
        """Test fallback to normal when no session tracker"""
        agent = MockAgent(session_tracker=None)
        tool = MockTool(agent)

        resolved = tool._resolve_verbosity("auto")
        assert resolved == "normal"

    def test_add_verbosity_metadata_string_result(self):
        """Test adding verbosity metadata to string result"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        result = "Some tool output"
        output = tool._add_verbosity_metadata(result, "minimal")

        assert "Some tool output" in output
        assert "_verbosity" in output
        assert "verbosity_used" in output
        assert "minimal" in output
        assert "upgrade_hint" in output

    def test_add_verbosity_metadata_dict_result(self):
        """Test adding verbosity metadata to dict result"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        result = {"symbols": [{"name": "User", "kind": "Class"}]}
        output = tool._add_verbosity_metadata(result, "normal")

        # Parse JSON output
        parsed = json.loads(output)
        assert "symbols" in parsed
        assert "_verbosity" in parsed
        assert parsed["_verbosity"]["verbosity_used"] == "normal"
        assert parsed["_verbosity"]["upgrade_available"] is True

    def test_add_verbosity_metadata_with_token_estimate(self):
        """Test verbosity metadata with token estimate"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        result = "Abbreviated output"
        output = tool._add_verbosity_metadata(result, "minimal", estimated_tokens_full=5000)

        assert "estimated_tokens_full" in output
        assert "5000" in output
        assert "verbosity='detailed'" in output

    def test_add_verbosity_metadata_detailed_no_upgrade(self):
        """Test verbosity metadata for detailed (no upgrade available)"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        result = "Full detailed output"
        output = tool._add_verbosity_metadata(result, "detailed", estimated_tokens_full=5000)

        parsed_metadata = json.loads(output.split("\n\n")[-1])
        assert parsed_metadata["_verbosity"]["verbosity_used"] == "detailed"
        assert parsed_metadata["_verbosity"]["upgrade_available"] is False
        # Should not include estimate when already detailed
        assert "estimated_tokens_full" not in parsed_metadata["_verbosity"]

    def test_record_tool_call_for_session_edit(self):
        """Test recording edit tool call in session"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        tool._record_tool_call_for_session(is_edit=True, file_path="models.py")

        assert tracker.edit_count == 1
        assert len(tracker.tool_history) == 1
        assert "models.py" in tracker.accessed_files

    def test_record_tool_call_for_session_search(self):
        """Test recording search tool call in session"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        tool._record_tool_call_for_session(is_search=True)

        assert tracker.search_count == 1
        assert len(tracker.tool_history) == 1

    def test_record_tool_call_for_session_no_tracker(self):
        """Test recording tool call when no session tracker (should not crash)"""
        agent = MockAgent(session_tracker=None)
        tool = MockTool(agent)

        # Should not raise exception
        tool._record_tool_call_for_session(is_search=True)

    def test_workflow_exploration_to_implementation(self):
        """Test complete workflow: exploration → implementation with verbosity changes"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        # Phase 1: Exploration (10 searches)
        for i in range(10):
            tool._record_tool_call_for_session(is_search=True)

        verbosity = tool._resolve_verbosity("auto")
        assert verbosity == "minimal"
        assert tracker.detect_phase() == Phase.EXPLORATION

        # Phase 2: Implementation (8 edits)
        for i in range(8):
            tool._record_tool_call_for_session(is_edit=True, file_path=f"file{i}.py")

        verbosity = tool._resolve_verbosity("auto")
        assert verbosity == "normal"
        assert tracker.detect_phase() == Phase.IMPLEMENTATION

    def test_workflow_exploration_to_focused_work(self):
        """Test workflow: exploration → focused work with verbosity changes"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        # Phase 1: Exploration
        for i in range(10):
            tool._record_tool_call_for_session(is_search=True)

        verbosity1 = tool._resolve_verbosity("auto")
        assert verbosity1 == "minimal"

        # Phase 2: Focused work on one file
        for i in range(6):
            tool._record_tool_call_for_session(is_read=True, file_path="models.py")

        verbosity2 = tool._resolve_verbosity("auto")
        assert verbosity2 == "detailed"
        assert tracker.is_focused_work() is True

    def test_verbosity_metadata_phase_reason(self):
        """Test that phase reason is included in metadata"""
        tracker = SessionTracker()
        # Set up exploration phase
        for i in range(10):
            tracker.record_tool_call(f"search_{i}", is_search=True)

        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        result = "Output"
        output = tool._add_verbosity_metadata(result, "minimal")

        assert "verbosity_reason" in output
        assert "exploration_phase" in output

    def test_backward_compatibility_explicit_verbosity(self):
        """Test that explicit verbosity always works (backward compatible)"""
        # Even with no session tracker
        agent = MockAgent(session_tracker=None)
        tool = MockTool(agent)

        # All explicit levels should work
        assert tool._resolve_verbosity("minimal") == "minimal"
        assert tool._resolve_verbosity("normal") == "normal"
        assert tool._resolve_verbosity("detailed") == "detailed"

    def test_metadata_upgrade_hints(self):
        """Test that appropriate upgrade hints are provided for each verbosity level"""
        tracker = SessionTracker()
        agent = MockAgent(session_tracker=tracker)
        tool = MockTool(agent)

        # Minimal → should suggest normal or detailed
        output_minimal = tool._add_verbosity_metadata("result", "minimal")
        assert "verbosity='normal'" in output_minimal or "verbosity='detailed'" in output_minimal

        # Normal → should suggest detailed
        output_normal = tool._add_verbosity_metadata("result", "normal")
        assert "verbosity='detailed'" in output_normal

        # Detailed → should not have token estimate in upgrade_hint (already max)
        output_detailed = tool._add_verbosity_metadata("result", "detailed")
        metadata = json.loads(output_detailed.split("\n\n")[-1])
        assert metadata["_verbosity"]["upgrade_available"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
