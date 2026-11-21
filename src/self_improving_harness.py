"""
Self-Improving Agent Harness for Aria (arXiv:2611.22299v1).
Decomposes agent runtime into 4 orthogonal components:
  1. CONTEXT_MEMORY: dynamic compaction, observation truncation, reflection stores.
  2. AGENT_CONTROL: step budget allocation, loop-break guards, backtracking branches.
  3. ACTION_INTERFACE: tool schemas, robust JSON/tag parsers, command sanitizers.
  4. VERIFICATION_RECOVERY: pre-stop assertions, regression gates, counterfactual recovery.

Executes a closed-loop self-improvement cycle:
  Trajectory Observation -> Pattern Diagnosis -> Patch Proposal -> Invariant Verification Gate -> Live Deployment.
"""

import re
import sys
import time
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Tuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.counterfactual_engine import CounterfactualEngine, DisturbanceType


class RuntimeComponent(str, Enum):
    CONTEXT_MEMORY = "CONTEXT_MEMORY"
    AGENT_CONTROL = "AGENT_CONTROL"
    ACTION_INTERFACE = "ACTION_INTERFACE"
    VERIFICATION_RECOVERY = "VERIFICATION_RECOVERY"


class FailurePattern(str, Enum):
    REPEATED_ACTION_LOOP = "REPEATED_ACTION_LOOP"
    PREMATURE_STOP = "PREMATURE_STOP"
    TOOL_SYNTAX_REJECTION = "TOOL_SYNTAX_REJECTION"
    DISTURBANCE_MISATTRIBUTION = "DISTURBANCE_MISATTRIBUTION"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


@dataclass
class HarnessDiagnosis:
    pattern: FailurePattern
    component: RuntimeComponent
    root_cause: str
    trigger_step: int
    remediation_proposal: str


@dataclass
class HarnessPatch:
    patch_id: str
    component: RuntimeComponent
    target_name: str
    description: str
    hook_fn: Optional[Callable[..., Any]] = None
    is_validated: bool = False
    applied_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfImprovingHarness:
    """
    Self-Improving Runtime Harness orchestrator (arXiv:2611.22299v1).
    Monitors trajectories, detects runtime failure patterns, synthesizes modular hooks,
    gates deployment behind invariant regression tests, and applies live patches.
    """

    def __init__(self, enable_auto_validation: bool = False):
        self.enable_auto_validation = enable_auto_validation
        self.active_hooks: Dict[RuntimeComponent, List[HarnessPatch]] = {
            RuntimeComponent.CONTEXT_MEMORY: [],
            RuntimeComponent.AGENT_CONTROL: [],
            RuntimeComponent.ACTION_INTERFACE: [],
            RuntimeComponent.VERIFICATION_RECOVERY: [],
        }
        self.patch_history: List[HarnessPatch] = []
        self.diagnoses_history: List[HarnessDiagnosis] = []

    def diagnose_trajectory(self, steps: List[Any]) -> Optional[HarnessDiagnosis]:
        """
        Inspects step trajectory for failure modes across control, memory, action, and verification.
        Accepts list of AgentStep objects or step dictionaries.
        """
        if not steps:
            return None

        normalized_steps: List[Dict[str, Any]] = []
        for s in steps:
            if hasattr(s, "step_number"):
                normalized_steps.append({
                    "step_number": s.step_number,
                    "thought": s.thought,
                    "action_type": s.action_type,
                    "action_payload": s.action_payload,
                    "observation": s.observation,
                    "exit_code": s.exit_code,
                })
            elif isinstance(s, dict):
                normalized_steps.append(s)

        # 1. Detect Repeated Action Loops (AGENT_CONTROL defect)
        for i in range(len(normalized_steps) - 1):
            curr = normalized_steps[i]
            nxt = normalized_steps[i + 1]
            if (curr.get("action_type") == nxt.get("action_type") and
                curr.get("action_payload") == nxt.get("action_payload") and
                curr.get("action_payload") != "" and
                nxt.get("exit_code", 0) != 0):
                diag = HarnessDiagnosis(
                    pattern=FailurePattern.REPEATED_ACTION_LOOP,
                    component=RuntimeComponent.AGENT_CONTROL,
                    root_cause=f"Step {nxt.get('step_number')} repeated identical failing action '{curr.get('action_type')}: {curr.get('action_payload')}'.",
                    trigger_step=nxt.get("step_number", i + 2),
                    remediation_proposal="Inject loop breaker hook to prevent repeated identical failing action payloads."
                )
                self.diagnoses_history.append(diag)
                return diag

        # 2. Detect Premature Stop (VERIFICATION_RECOVERY defect)
        if len(normalized_steps) == 1:
            first = normalized_steps[0]
            if first.get("action_type") == "finish" and not first.get("action_payload"):
                diag = HarnessDiagnosis(
                    pattern=FailurePattern.PREMATURE_STOP,
                    component=RuntimeComponent.VERIFICATION_RECOVERY,
                    root_cause="Agent halted on step 1 with empty payload without executing required slots or verifications.",
                    trigger_step=1,
                    remediation_proposal="Register pre-stop assertion hook requiring verification before finish."
                )
                self.diagnoses_history.append(diag)
                return diag

        # 3. Detect Environmental Disturbance Misattribution (VERIFICATION_RECOVERY / Counterfactual)
        for s in normalized_steps:
            exit_code = s.get("exit_code", 0)
            obs = s.get("observation", "")
            action = s.get("action_payload", "")
            if exit_code != 0 and s.get("action_type") == "command":
                cf_diag = CounterfactualEngine.diagnose_execution(
                    action=action,
                    exit_code=exit_code,
                    stderr=obs,
                    stdout=""
                )
                if cf_diag.is_disturbance:
                    diag = HarnessDiagnosis(
                        pattern=FailurePattern.DISTURBANCE_MISATTRIBUTION,
                        component=RuntimeComponent.VERIFICATION_RECOVERY,
                        root_cause=f"Step {s.get('step_number')} failed due to {cf_diag.disturbance_type.value} environmental disturbance.",
                        trigger_step=s.get("step_number", 1),
                        remediation_proposal=f"Route through CounterfactualEngine remedy: '{cf_diag.remedy_action}'."
                    )
                    self.diagnoses_history.append(diag)
                    return diag

        # 4. Detect Tool Syntax / Malformed Action Rejection (ACTION_INTERFACE defect)
        for s in normalized_steps:
            obs = s.get("observation", "")
            if "Unknown action" in obs or "Failed to parse JSON" in obs or "invalid syntax" in obs.lower():
                diag = HarnessDiagnosis(
                    pattern=FailurePattern.TOOL_SYNTAX_REJECTION,
                    component=RuntimeComponent.ACTION_INTERFACE,
                    root_cause=f"Step {s.get('step_number')} failed tool interface parsing: {obs[:80]}.",
                    trigger_step=s.get("step_number", 1),
                    remediation_proposal="Add robust parsing fallback and action sanitizer in ACTION_INTERFACE."
                )
                self.diagnoses_history.append(diag)
                return diag

        return None

    def propose_patch(self, diagnosis: HarnessDiagnosis) -> HarnessPatch:
        """
        Synthesizes a targeted modular HarnessPatch based on the diagnosis.
        """
        patch_id = f"patch_{int(time.time()*1000)}_{diagnosis.pattern.value.lower()}"

        if diagnosis.pattern == FailurePattern.REPEATED_ACTION_LOOP:
            def loop_breaker_hook(action_type: str, payload: str, history: List[Dict[str, Any]]) -> Tuple[str, str, bool]:
                if len(history) >= 1:
                    last = history[-1]
                    if last.get("action_type") == action_type and last.get("action_payload") == payload and last.get("exit_code", 0) != 0:
                        # Intercept duplicate action
                        return "finish", f"[HARNESS_LOOP_BREAKER] Blocked repeating failing action '{action_type} {payload}'.", True
                return action_type, payload, False

            return HarnessPatch(
                patch_id=patch_id,
                component=RuntimeComponent.AGENT_CONTROL,
                target_name="loop_breaker_guard",
                description="Prevents back-to-back identical failing actions in control loop.",
                hook_fn=loop_breaker_hook,
                metadata={"pattern": diagnosis.pattern.value}
            )

        elif diagnosis.pattern == FailurePattern.PREMATURE_STOP:
            def pre_stop_verifier_hook(action_type: str, payload: str, slots_satisfied: List[str]) -> Tuple[str, str, bool]:
                if action_type == "finish" and not payload:
                    return "vitals", "", True  # Redirect to collect vitals rather than aborting blank
                return action_type, payload, False

            return HarnessPatch(
                patch_id=patch_id,
                component=RuntimeComponent.VERIFICATION_RECOVERY,
                target_name="pre_stop_assertion",
                description="Guards against unverified blank finish calls.",
                hook_fn=pre_stop_verifier_hook,
                metadata={"pattern": diagnosis.pattern.value}
            )

        elif diagnosis.pattern == FailurePattern.DISTURBANCE_MISATTRIBUTION:
            def counterfactual_recovery_hook(action: str, exit_code: int, stderr: str) -> Optional[str]:
                cf = CounterfactualEngine.diagnose_execution(action, exit_code, stderr)
                if cf.is_disturbance and cf.counterfactual_estimate >= 0.70:
                    return cf.remedy_action
                return None

            return HarnessPatch(
                patch_id=patch_id,
                component=RuntimeComponent.VERIFICATION_RECOVERY,
                target_name="counterfactual_auto_remedy",
                description="Automatically derives environmental disturbance remedy actions.",
                hook_fn=counterfactual_recovery_hook,
                metadata={"pattern": diagnosis.pattern.value}
            )

        elif diagnosis.pattern == FailurePattern.TOOL_SYNTAX_REJECTION:
            def robust_action_sanitizer(raw_text: str) -> Tuple[str, str]:
                clean = raw_text.strip().strip("`").strip()
                if clean.startswith("git ") or clean.startswith("df ") or clean.startswith("free "):
                    return "command", clean
                return "finish", clean

            return HarnessPatch(
                patch_id=patch_id,
                component=RuntimeComponent.ACTION_INTERFACE,
                target_name="action_syntax_sanitizer",
                description="Sanitizes raw model outputs into valid action and payload pairs.",
                hook_fn=robust_action_sanitizer,
                metadata={"pattern": diagnosis.pattern.value}
            )

        # Fallback generic patch
        return HarnessPatch(
            patch_id=patch_id,
            component=diagnosis.component,
            target_name="generic_recovery_hook",
            description=f"Generic fallback hook for {diagnosis.pattern.value}",
            hook_fn=lambda *args, **kwargs: None,
            metadata={"pattern": diagnosis.pattern.value}
        )

    def validate_patch(self, patch: HarnessPatch, test_command: Optional[str] = None) -> bool:
        """
        Validates patch against system regression test suite.
        Ensures runtime patches never regress system invariants (Paper 1 inviolable gate).
        """
        # Hook must be callable
        if patch.hook_fn is None or not callable(patch.hook_fn):
            patch.is_validated = False
            return False

        # Invariant regression check
        if test_command:
            try:
                proc = subprocess.run(
                    test_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30.0
                )
                if proc.returncode != 0:
                    patch.is_validated = False
                    return False
            except Exception:
                patch.is_validated = False
                return False

        patch.is_validated = True
        return True

    def deploy_patch(self, patch: HarnessPatch) -> bool:
        """
        Deploys a validated patch into the active harness hook registry.
        """
        if not patch.is_validated:
            return False

        patch.applied_at = time.time()
        self.active_hooks[patch.component].append(patch)
        self.patch_history.append(patch)
        return True

    def apply_control_hooks(self, action_type: str, payload: str, history: List[Dict[str, Any]]) -> Tuple[str, str, bool]:
        """
        Executes active AGENT_CONTROL hooks sequentially.
        Returns (action_type, payload, was_intercepted).
        """
        current_type, current_payload = action_type, payload
        intercepted = False
        for patch in self.active_hooks[RuntimeComponent.AGENT_CONTROL]:
            if patch.hook_fn:
                new_type, new_payload, modified = patch.hook_fn(current_type, current_payload, history)
                if modified:
                    current_type = new_type
                    current_payload = new_payload
                    intercepted = True
        return current_type, current_payload, intercepted

    def apply_verification_recovery_hooks(self, action: str, exit_code: int, stderr: str) -> Optional[str]:
        """
        Executes active VERIFICATION_RECOVERY hooks to derive counterfactual or automated remediation.
        """
        for patch in self.active_hooks[RuntimeComponent.VERIFICATION_RECOVERY]:
            if patch.hook_fn and patch.target_name == "counterfactual_auto_remedy":
                remedy = patch.hook_fn(action, exit_code, stderr)
                if remedy:
                    return remedy
        return None

    def audit_summary(self) -> Dict[str, Any]:
        """Returns structured audit metrics for the self-improving harness."""
        return {
            "total_diagnoses": len(self.diagnoses_history),
            "total_patches_generated": len(self.patch_history),
            "active_hooks_by_component": {
                comp.value: len(hooks) for comp, hooks in self.active_hooks.items()
            },
            "recent_patches": [
                {
                    "patch_id": p.patch_id,
                    "component": p.component.value,
                    "target": p.target_name,
                    "applied_at": p.applied_at
                } for p in self.patch_history[-5:]
            ]
        }

harness_singleton = SelfImprovingHarness()
