import pytest
import asyncio
from src.agent_loop import SlotClosedAgentLoop, AgentTaskResult, AgentStep
from src.tools import CodebaseTools
from src.executor import SafeExecutor

def test_extract_action_json():
    loop = SlotClosedAgentLoop()
    raw = '{"thought": "Check system memory", "action": "command", "payload": "free -m"}'
    thought, action, payload = loop.extract_action(raw)
    assert thought == "Check system memory"
    assert action == "command"
    assert payload == "free -m"

def test_extract_action_xml_tags():
    loop = SlotClosedAgentLoop()
    raw = '<thought>Read the configuration</thought> <action type="read_file">src/config.py</action>'
    thought, action, payload = loop.extract_action(raw)
    assert thought == "Read the configuration"
    assert action == "read_file"
    assert payload == "src/config.py"

def test_extract_action_finish():
    loop = SlotClosedAgentLoop()
    raw = 'Everything is operational and verified.'
    thought, action, payload = loop.extract_action(raw)
    assert action == "finish"
    assert payload == "Everything is operational and verified."

def test_slot_closed_loop_execution():
    async def _run_test():
        loop = SlotClosedAgentLoop()
        task = "Verify host uptime and disk space"
        
        call_count = 0
        async def mock_query(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '{"thought": "Checking disk space", "action": "command", "payload": "df -h"}'
            elif call_count == 2:
                return '{"thought": "Checking uptime", "action": "command", "payload": "uptime"}'
            else:
                return '{"thought": "All slots satisfied", "action": "finish", "payload": "Disk and uptime are within normal parameters."}'
                
        loop.query_model = mock_query
        
        result = await loop.execute_task(task, required_slots=["diagnosis", "verification"])
        assert result.status == "completed"
        assert len(result.steps) >= 2
        assert result.steps[0].action_payload == "df -h"
        assert result.steps[0].exit_code == 0
        assert result.steps[1].action_payload == "uptime"
        assert result.steps[1].exit_code == 0
        assert "parameters" in result.final_answer

    asyncio.run(_run_test())
