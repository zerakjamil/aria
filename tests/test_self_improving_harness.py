"""
Tests for Self-Improving Agent Harness (arXiv:2611.22299v1).
Verifies:
1. 4-component decomposition: CONTEXT_MEMORY, AGENT_CONTROL, ACTION_INTERFACE, VERIFICATION_RECOVERY.
2. Trajectory failure pattern diagnosis (loop, premature stop, disturbance misattribution, syntax errors).
3. Patch proposal, validation gate against system invariants, and live hook deployment.
4. Runtime interceptor behavior during agent execution loops.
"""

import pytest
from src.self_improving_harness import (
    SelfImprovingHarness,
    RuntimeComponent,
    FailurePattern,
    HarnessPatch,
    HarnessDiagnosis,
)
from src.agent_loop import AgentStep


def test_runtime_components_enumeration():
    expected = {"CONTEXT_MEMORY", "AGENT_CONTROL", "ACTION_INTERFACE", "VERIFICATION_RECOVERY"}
    actual = {c.value for c in RuntimeComponent}
    assert actual == expected


def test_failure_patterns_enumeration():
    expected = {
        "REPEATED_ACTION_LOOP",
        "PREMATURE_STOP",
        "TOOL_SYNTAX_REJECTION",
        "DISTURBANCE_MISATTRIBUTION",
        "UNHANDLED_EXCEPTION",
    }
    actual = {p.value for p in FailurePattern}
    assert actual == expected


def test_diagnose_repeated_action_loop():
    harness = SelfImprovingHarness()
    steps = [
        AgentStep(
            step_number=1,
            thought="Checking status",
            action_type="command",
            action_payload="systemctl status redis",
            observation="ERROR: service not found",
            exit_code=1,
            duration_ms=10.0,
            is_safe=True
        ),
        AgentStep(
            step_number=2,
            thought="Retrying status",
            action_type="command",
            action_payload="systemctl status redis",
            observation="ERROR: service not found",
            exit_code=1,
            duration_ms=10.0,
            is_safe=True
        )
    ]
    diag = harness.diagnose_trajectory(steps)
    assert diag is not None
    assert diag.pattern == FailurePattern.REPEATED_ACTION_LOOP
    assert diag.component == RuntimeComponent.AGENT_CONTROL
    assert diag.trigger_step == 2


def test_diagnose_premature_stop():
    harness = SelfImprovingHarness()
    steps = [
        AgentStep(
            step_number=1,
            thought="Stopping early",
            action_type="finish",
            action_payload="",
            observation="",
            exit_code=0,
            duration_ms=5.0,
            is_safe=True
        )
    ]
    diag = harness.diagnose_trajectory(steps)
    assert diag is not None
    assert diag.pattern == FailurePattern.PREMATURE_STOP
    assert diag.component == RuntimeComponent.VERIFICATION_RECOVERY


def test_diagnose_disturbance_misattribution():
    harness = SelfImprovingHarness()
    steps = [
        AgentStep(
            step_number=1,
            thought="Running git commit",
            action_type="command",
            action_payload="git commit -m 'feat: update'",
            observation="fatal: Unable to create '/repo/.git/index.lock': File exists.",
            exit_code=128,
            duration_ms=15.0,
            is_safe=True
        )
    ]
    diag = harness.diagnose_trajectory(steps)
    assert diag is not None
    assert diag.pattern == FailurePattern.DISTURBANCE_MISATTRIBUTION
    assert diag.component == RuntimeComponent.VERIFICATION_RECOVERY
    assert "rm -f .git/index.lock" in diag.remediation_proposal


def test_patch_proposal_and_validation():
    harness = SelfImprovingHarness()
    diag = HarnessDiagnosis(
        pattern=FailurePattern.REPEATED_ACTION_LOOP,
        component=RuntimeComponent.AGENT_CONTROL,
        root_cause="Repeated failing command",
        trigger_step=2,
        remediation_proposal="Inject loop breaker guard"
    )
    patch = harness.propose_patch(diag)
    assert patch.component == RuntimeComponent.AGENT_CONTROL
    assert patch.target_name == "loop_breaker_guard"
    assert patch.is_validated is False

    # Validate patch
    is_valid = harness.validate_patch(patch)
    assert is_valid is True
    assert patch.is_validated is True


def test_patch_deployment_and_hook_execution():
    harness = SelfImprovingHarness()
    diag = HarnessDiagnosis(
        pattern=FailurePattern.REPEATED_ACTION_LOOP,
        component=RuntimeComponent.AGENT_CONTROL,
        root_cause="Repeated failing command",
        trigger_step=2,
        remediation_proposal="Inject loop breaker guard"
    )
    patch = harness.propose_patch(diag)
    harness.validate_patch(patch)
    deployed = harness.deploy_patch(patch)
    assert deployed is True
    assert len(harness.active_hooks[RuntimeComponent.AGENT_CONTROL]) == 1

    # Simulate loop attempt
    history = [
        {"action_type": "command", "action_payload": "pytest fail_test.py", "exit_code": 1}
    ]
    new_type, new_payload, intercepted = harness.apply_control_hooks("command", "pytest fail_test.py", history)
    assert intercepted is True
    assert new_type == "finish"
    assert "HARNESS_LOOP_BREAKER" in new_payload


def test_audit_summary_telemetry():
    harness = SelfImprovingHarness()
    diag = HarnessDiagnosis(
        pattern=FailurePattern.PREMATURE_STOP,
        component=RuntimeComponent.VERIFICATION_RECOVERY,
        root_cause="Empty finish on step 1",
        trigger_step=1,
        remediation_proposal="Pre-stop verifier"
    )
    patch = harness.propose_patch(diag)
    harness.validate_patch(patch)
    harness.deploy_patch(patch)

    summary = harness.audit_summary()
    assert summary["total_patches_generated"] == 1
    assert summary["active_hooks_by_component"]["VERIFICATION_RECOVERY"] == 1
    assert len(summary["recent_patches"]) == 1
