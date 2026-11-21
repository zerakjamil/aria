"""
Tests for Counterfactual World Model & Disturbance Disentanglement (arXiv:2611.24778).
Verifies that environmental disturbances (locks, port collisions, OOM, network blips)
are separated from intrinsic code/command defects with zero added parameter overhead.
"""

import pytest
from src.counterfactual_engine import CounterfactualEngine, DisturbanceType
from src.self_repair import ShellTracebackDistiller, ReflexionMemory, LocalizedTraceback


def test_lock_contention_git_diagnosis():
    action = "git commit -m 'feat: test'"
    stderr = "fatal: Unable to create '/repo/.git/index.lock': File exists."
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=128, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.LOCK_CONTENTION
    assert "rm -f .git/index.lock" in diag.remedy_action
    assert diag.counterfactual_estimate > 0.85


def test_lock_contention_dpkg_diagnosis():
    action = "apt-get install -y htop"
    stderr = "E: Could not get lock /var/lib/dpkg/lock-frontend - open (11: Resource temporarily unavailable)"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=100, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.LOCK_CONTENTION
    assert "sleep 2" in diag.remedy_action


def test_port_collision_diagnosis():
    action = "python3 -m uvicorn src.server:app --port 8000"
    stderr = "ERROR: [Errno 98] address already in use (EADDRINUSE)"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=1, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.PORT_COLLISION
    assert "8001" in diag.remedy_action
    assert diag.counterfactual_estimate >= 0.90


def test_resource_exhaustion_diagnosis():
    action = "python3 scripts/train.py"
    stderr = "torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=1, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.RESOURCE_EXHAUSTION
    assert diag.counterfactual_estimate >= 0.80


def test_network_transient_diagnosis():
    action = "curl -fsSL https://huggingface.co/api/models"
    stderr = "curl: (35) OpenSSL SSL_connect: Connection reset by peer in connection to huggingface.co:443"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=35, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.NETWORK_TRANSIENT
    assert "--retry 3" in diag.remedy_action


def test_filesystem_perm_diagnosis():
    action = "mkdir -p /mnt/external/data"
    stderr = "mkdir: cannot create directory '/mnt/external/data': Read-only file system"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=1, stderr=stderr)
    assert diag.is_disturbance is True
    assert diag.disturbance_type == DisturbanceType.FILESYSTEM_PERM


def test_intrinsic_defect_preservation():
    action = "python3 -c 'print(1 / 0)'"
    stderr = "ZeroDivisionError: division by zero"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=1, stderr=stderr)
    assert diag.is_disturbance is False
    assert diag.disturbance_type == DisturbanceType.INTRINSIC_DEFECT
    assert diag.remedy_action == action
    assert diag.counterfactual_estimate == 0.1


def test_zero_exit_code_is_factual_success():
    action = "ls -la"
    diag = CounterfactualEngine.diagnose_execution(action, exit_code=0, stderr="")
    assert diag.is_disturbance is False
    assert diag.counterfactual_estimate == 1.0


def test_shell_distiller_integration():
    stderr = "fatal: Unable to create '/repo/.git/index.lock': File exists."
    tb = ShellTracebackDistiller.distill(stderr, exit_code=128, command="git commit -m 'test'")
    assert tb.error_type == f"Disturbance_{DisturbanceType.LOCK_CONTENTION.value}"
    assert "rm -f .git/index.lock" in tb.message


def test_reflexion_memory_with_disturbance():
    mem = ReflexionMemory("task_1", "Commit changes to git")
    tb = LocalizedTraceback(
        error_type=f"Disturbance_{DisturbanceType.LOCK_CONTENTION.value}",
        message="Lock contention on .git/index.lock. Suggested counterfactual remedy: rm -f .git/index.lock",
        assertion_detail=f"DisturbanceType.{DisturbanceType.LOCK_CONTENTION.value}",
        raw_stderr="fatal: lock exists"
    )
    reflection = mem.generate_reflection_block(1, tb)
    assert "environmental disturbance" in reflection
    assert "Underlying command or code logic is preserved" in reflection
