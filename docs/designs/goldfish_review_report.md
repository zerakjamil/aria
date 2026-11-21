# Goldfish Annotated Review Report

**Target:** `docs/designs/aria_phase7_grpo_and_linux_admin.md` (`Lines 1–361`)  
**Status:** Resolved (Proceeded without automated text edits; findings preserved for implementation)

## Prioritized Findings & AI Suggestions

### 1. Non-Existent Reference to `tests/test_invariants.py` & Invariant Baseline [`egm-codebase-details`] - Severity: Blocker
*   **Affected Scope:** [Lines 36–37](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L36-L37) (Goal G6), [Lines 333–338](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L333-L338) (Section Target Files Item 9), [Lines 344–345](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L344-L345) (Section Verification Plan Item 1)
*   **Discrepancy Description:** The design establishes Goal G6 as "Retain 100% green status across all 43 existing test invariants in `tests/test_invariants.py`", targets modifying `tests/test_invariants.py` from 43 to 48 invariants, and specifies `pytest tests/test_invariants.py` as its regression gate. In the current local repository, `tests/test_invariants.py` does not exist. Citing a non-existent file as an existing system baseline violates codebase grounding standards.
*   **Rationale:** The existing repo test suite contains `tests/eval_personality.py` and `tests/judge_benchmark.py`. The 43 invariant suite was run on edge server `ayewar` during Phase 6 but was not staged as a standalone file in the local root.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** The critique is accurate. Changing the action from `Modify` to `Create` and consolidating all 48 test invariants (including the 43 core systems invariants and 5 new telemetry/sandbox invariants) into a newly generated `tests/test_invariants.py` establishes an airtight, reproducible regression baseline.
*   ***Proposed Edit:***
    *   Location: Lines 36–37, 333–338, 344–345
    *   Change: Update Goal G6 to "Establish and verify 100% green status across 48 automated test invariants in `tests/test_invariants.py` (covering 43 core system regression invariants and 5 new telemetry/sandbox safety invariants)". Change Item 9 to `tests/test_invariants.py (Create)` with full schema verification.

---

### 2. Unaccounted VRAM Footprint for Reference Policy ($\pi_{\text{ref}}$) Logits During GRPO Backprop [`egm-design`] - Severity: Blocker
*   **Affected Scope:** [Lines 153–156](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L153-L156) (GRPO Objective Formula), [Lines 187–192](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L187-L192) (Sequence Diagram Phase 4), [Lines 209–216](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L209-L216) (Section 3 VRAM Budget Table)
*   **Discrepancy Description:** The GRPO objective explicitly evaluates per-token KL divergence against a frozen reference policy: $-\beta \mathbb{D}_{\text{KL}}(\pi_\theta \parallel \pi_{\text{ref}})$. The VRAM budget accounts only for the active PyTorch 4-bit base model, LoRA weights, optimizer, and activation cache (3,346 MiB). There is zero memory allocated for $\pi_{\text{ref}}$. Loading a frozen 3B reference model in PyTorch requires an additional $\ge 1,920 \text{ MiB}$, pushing total VRAM to $5,266 \text{ MiB} > 4,096 \text{ MiB}$ and causing an immediate CUDA Out-Of-Memory abort.
*   **Rationale:** On a 4GB GPU, two 3B models cannot be co-located in VRAM during backpropagation.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** The critique correctly identifies an unmitigated memory crash. We can eliminate the reference model from backpropagation entirely by pre-computing scalar reference log-probabilities $\log \pi_{\text{ref}}(y_i|x)$ during the rollout generation phase (when the base model is already resident in Ollama/llama.cpp) and caching them in the trajectory buffer. PyTorch then evaluates token-level KL divergence using cached scalar tensors without loading a second model into VRAM.
*   ***Proposed Edit:***
    *   Location: Section 1.3, Section 2 Sequence Diagram, Section 3 VRAM Budget Table
    *   Change: Explicitly specify: "Reference policy log-probabilities $\log \pi_{\text{ref}}(y_i|x)$ are pre-computed during Phase 1 rollout generation in Ollama/llama.cpp and stored in the trajectory buffer. Phase 4 backpropagation loads only the single active policy $\pi_\theta$, evaluating KL divergence against the cached reference logits with zero additional GPU memory allocation."

---

### 3. Host D-Bus Disconnect & Root Escalation Failure in Bubblewrap Sandbox [`egm-design`] - Severity: Blocker
*   **Affected Scope:** [Lines 73–82](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L73-L82) (CUJ 2), [Lines 141–146](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L141-L146) (Section 1.2), [Lines 280–287](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L280-L287) (Detailed Plan Item 2)
*   **Discrepancy Description:** CUJ 2 and Section 1.2 specify that Aria diagnoses systemd service failures (`systemctl status mock-worker.service`), constructs a fix, and verifies it inside Bubblewrap isolated via `--ro-bind /usr /usr`, `--tmpfs /tmp`, and `--unshare-net`. In Linux, `systemctl` communicates with PID 1 via `/run/systemd/private` or D-Bus. In an unprivileged Bubblewrap namespace without systemd as PID 1, `systemctl` aborts with `System has not been booted with systemd as init system (PID 1). Can't operate.` Read-only root also blocks writing to `/etc/systemd/system/`.
*   **Rationale:** Live systemd daemon commands cannot execute in standard unprivileged container namespaces.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Critique is valid. We must not attempt to run live `systemctl` inside unprivileged Bubblewrap. Instead, sysadmin remediation tasks must be verified using mock root environments (`/tmp/mock_root/etc/systemd/system/`), static syntax linters (`systemd-analyze verify --root=/tmp/mock_root ...`), and Python-based process supervisor fixtures.
*   ***Proposed Edit:***
    *   Location: Section 1.2, CUJ 2, Detailed Plan Item 2
    *   Change: Replace direct `systemctl` execution inside the sandbox with isolated mock environments: "Sandboxed service validation utilizes an ephemeral mock directory tree in tmpfs (`/tmp/sandbox_root/`). Service unit remediation is validated using standalone configuration validators (`systemd-analyze verify --root=/tmp/sandbox_root`) and Python process supervisors rather than invoking live PID 1 D-Bus calls."

---

### 4. Dual-Paradigm Scope Creep: Conflating Edge GRPO with Linux Sysadmin Tooling [`egm-zoom-out`] - Severity: Major
*   **Affected Scope:** [Lines 11–17](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L11-L17) (Overview), [Lines 95–125](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L95-L125) (Architecture), [Lines 295–310](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L295-L310) (Detailed Plan Items 4 & 5)
*   **Discrepancy Description:** Coupling on-device GRPO policy training with full-blown Linux sysadmin sandboxing in a single sprint conflates two complex frontiers, risking delivery failure.
*   **Rationale:** If the primary goal is advancing validation accuracy from 57.34% to 65.0%, adding Bubblewrap namespaces and 50 synthetic systemd scenarios introduces unnecessary complexity to the core RL loop.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Restructuring into two sequential, dependency-ordered subphases maintains both objectives while eliminating blast radius:
    * **Phase 7.1 (Core GRPO Policy Optimization):** Focuses strictly on the memory-interleaved GRPO trainer, graduated rewards, and algorithmic/Python struggle sets to hit the 65.0% accuracy milestone.
    * **Phase 7.2 (Sandboxed Linux Administration & Tooling):** Introduces `telemetry_probe.py`, `sandbox_runner.py`, and the 50 system maintenance scenarios on top of the stabilized RL loop.
*   ***Proposed Edit:***
    *   Location: Overview, Technical Plan, Detailed Implementation Plan
    *   Change: Formulate explicit phasing: "Phase 7 is executed in two sequential milestones: Milestone 7.1 establishes on-device GRPO policy training on verifiable coding benchmarks to hit the 65.0% accuracy target; Milestone 7.2 extends the verified RL harness to sandboxed Linux system administration and read-only host telemetry."

---

### 5. Synchronous VRAM Thrashing & Ollama Process Churn on Per-Step Training Cycles [`egm-inventive-catalyst`] - Severity: Major
*   **Affected Scope:** [Lines 160–197](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L160-L197) (Sequence Diagram), [Lines 298–304](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L298-L304) (Detailed Plan Item 4)
*   **Discrepancy Description:** Unloading Ollama, loading PyTorch, backpropagating, and reloading Ollama on every batch of training prompts spends more time loading/unloading 2.1 GB weights across PCIe than computing gradients.
*   **Rationale:** Repeating model unloads every 8 prompts introduces massive I/O thrashing.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Apply TRIZ Principle 15 (Dynamics) and Asynchronous Trajectory Buffering. In Phase A, Ollama generates rollouts for an entire epoch (50–100 prompts) into an on-disk buffer (`data/trajectories_epoch_t.jsonl`), pre-computing both rollout text and reference log-probabilities. In Phase B, Ollama unloads once; PyTorch runs all gradient steps across the buffered trajectories. Ollama reloads only once per epoch.
*   ***Proposed Edit:***
    *   Location: Section 2 Sequence Diagram, Detailed Plan Item 4
    *   Change: Update sequence diagram to show epoch-level buffering: "Harness generates rollouts for batch/epoch into `data/trajectory_buffer.jsonl` with cached reference logits -> Ollama unloads once -> PyTorch executes gradient steps across all buffered groups -> PyTorch exports adapter checkpoint -> Ollama reloads once for evaluation."

---

### 6. Vanishing Advantage and Zero-Gradient Stagnation on Homogeneous Group Rollouts ($G=4$) [`egm-inventive-catalyst`] - Severity: Major
*   **Affected Scope:** [Lines 149–156](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L149-L156) (Section 1.3), [Lines 301–302](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L301-L302) (Detailed Plan Item 4)
*   **Discrepancy Description:** With binary rewards $R \in \{+1.0, -1.0\}$ and $G=4$, when all 4 completions fail ($R=[-1,-1,-1,-1]$) or all 4 pass ($R=[+1,+1,+1,+1]$), group variance is zero ($\sigma(R) = 0$). Normalized advantage becomes $A_i = 0$, producing zero gradients ($\nabla \mathcal{L} = 0$) and wasting 100% of rollout compute.
*   **Rationale:** Binary all-or-nothing rewards frequently produce zero-variance groups.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Replace flat binary rewards with a graduated reward function:
    * Syntax error / unparseable AST: $-1.0$
    * Uncaught runtime exception: $-0.5$
    * Partial assertion pass ($k$ of $M$ tests): $-0.2 + 0.8 \times (k/M)$
    * Complete assertion pass ($M/M$ tests): $+1.0$
    * Execution timeout / hang: $-1.0$
    Additionally, implement batch-level advantage normalization fallback when intra-group variance is zero.
*   ***Proposed Edit:***
    *   Location: Section 1.3, Detailed Plan Item 4
    *   Change: Update reward function definition and advantage normalization formulas to incorporate graduated unit test feedback and batch-level fallback.

---

### 7. Root Partition (`/`) Cache Exhaustion by PyTorch and Hugging Face [`egm-codebase-details`] - Severity: Major
*   **Affected Scope:** [Lines 259–261](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L259-L261) (NFR Performance), [Lines 298–304](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L298-L304) (Detailed Plan Item 4)
*   **Discrepancy Description:** Server `ayewar`'s root partition `/` has only 1.9 GB of free disk space. PyTorch and Hugging Face default to caching in `~/.cache/huggingface/` and `~/.cache/torch/` on root. Without explicit redirection, training will fill root `/` within seconds and freeze the OS.
*   **Rationale:** Root partition overflow causes immediate Linux OS instability.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Hardcode environment variables `HF_HOME=/srv/storage/cache/huggingface`, `TORCH_HOME=/srv/storage/cache/torch`, and `TMPDIR=/srv/storage/tmp` in `grpo_trainer.py` and service configs before importing PyTorch.
*   ***Proposed Edit:***
    *   Location: Non-Functional Requirements Item 3, Detailed Plan Item 4
    *   Change: Add explicit cache redirection directive: "All training processes enforce `HF_HOME=/srv/storage/cache/huggingface`, `TORCH_HOME=/srv/storage/cache/torch`, and `TMPDIR=/srv/storage/tmp` at initialization, preventing any writes to the 96%-full root `/` partition."

---

### 8. Underspecified Hyperparameters & Training Configuration [`egm-implementation-readiness`] - Severity: Major
*   **Affected Scope:** [Lines 147–157](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L147-L157) (Section 1.3), [Lines 295–304](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L295-L304) (Detailed Plan Item 4)
*   **Discrepancy Description:** The design omits core training hyperparameters required by the Implementation Readiness Standard: learning rate, optimizer configuration, target LoRA modules, max sequence length, and prompt masking logic.
*   **Rationale:** An implementer cannot train without these exact parameters.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Add an explicit, complete hyperparameter table in Section 1.3.
*   ***Proposed Edit:***
    *   Location: Section 1.3, Detailed Plan Item 4
    *   Change: Insert concrete hyperparameter table: Base Model (`Qwen/Qwen2.5-3B-Instruct`), Learning Rate ($5 \times 10^{-6}$ with cosine decay), Optimizer (`paged_adamw_8bit`), LoRA rank $r=16, \alpha=32$, LoRA targets (`q_proj, k_proj, v_proj, o_proj`), Max Token Length (2048), Gradient Accumulation Steps (4), Prompt Masking (loss evaluated strictly on completion tokens).

---

### 9. Incompatible Python AST Traceback Distillation for Shell Errors [`egm-codebase-details`] - Severity: Major
*   **Affected Scope:** [Lines 141–146](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L141-L146) (Section 1.2), [Lines 288–294](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L288-L294) (Detailed Plan Item 3)
*   **Discrepancy Description:** Existing `TracebackDistiller` in `src/self_repair.py` parses Python syntax/assertion stack traces. Shell errors (exit code 127, command not found, permission denied) do not match Python regexes and fall back to generic errors without actionable details.
*   **Rationale:** Shell error diagnostics require dedicated parsing logic.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Refactor `src/self_repair.py` to introduce a dedicated `ShellTracebackDistiller` alongside the existing Python `TracebackDistiller`, mapping exit codes and stderr lines into actionable `<reflection>` blocks.
*   ***Proposed Edit:***
    *   Location: Detailed Plan Item 3
    *   Change: Specify creation of `ShellTracebackDistiller` in `src/self_repair.py` to extract command names, exit codes, and failure lines from stderr into `<reflection>` blocks.

---

### 10. Missing Mandatory "Risks & Mitigations" Section & Non-Compliant Attribution [`egm-structural`] - Severity: Major
*   **Affected Scope:** [Lines 219–248](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L219-L248) (Alternatives Considered), [Lines 251–266](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L251-L266) (Non-Functional Requirements)
*   **Discrepancy Description:** The document omits the mandatory top-level `## Risks & Mitigations` section required by `feature-spec-standard.md`. Additionally, `## Alternatives Considered` uses `Reason for Rejection: Rejected by author: ...`, which violates the standard's rule requiring objective technical trade-offs without personal attributions unless citing a maintainer PR/issue.
*   **Rationale:** Template compliance and objective technical justification.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Insert a dedicated `## Risks & Mitigations` section addressing VRAM overflow, sandbox breakout, vanishing gradients, and offline downtime. Reformat `## Alternatives Considered` to state objective technical rationales without "Rejected by author:".
*   ***Proposed Edit:***
    *   Location: After Technical Plan, and within Alternatives Considered
    *   Change: Insert `## Risks & Mitigations` section. Reformat rejection rationales to `Reason for Rejection: [Technical constraint and benchmark link]`.

---

### 11. Premature Per-Step Weight Fusion and Redundant GGUF Conversion Overhead [`egm-zoom-out`] - Severity: Major
*   **Affected Scope:** [Lines 193–197](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L193-L197) (Sequence Diagram Phase 5), [Lines 303–304](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L303-L304) (Detailed Plan Item 4)
*   **Discrepancy Description:** Converting LoRA to GGUF, merging into `aria_q4.gguf`, and restarting Ollama after every training step or iteration introduces unnecessary conversion overhead. Intermediate checkpoints should be evaluated directly in PyTorch against validation loss and token accuracy.
*   **Rationale:** GGUF fusion is a deployment step, not an inner training loop operation.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Restrict GGUF weight fusion and Ollama reloading to the end of a training session, triggered only when an adapter checkpoint achieves the target $\ge 65.0\%$ validation accuracy gate.
*   ***Proposed Edit:***
    *   Location: Section 2 Sequence Diagram, Detailed Plan Item 4
    *   Change: Remove GGUF fusion from the per-iteration loop. State: "GGUF weight fusion via `llama-export-lora` and Ollama deployment execute as a release step only after an adapter checkpoint achieves validation token accuracy $\ge 65.0\%$."

---

### 12. Comprehension Gap: Unexplained Mechanism for Simulating Service Repairs [`egm-comprehension`] - Severity: Major
*   **Affected Scope:** [Lines 79–82](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L79-L82) (CUJ 2), [Lines 141–146](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L141-L146) (Section 1.2), [Lines 305–310](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L305-L310) (Detailed Plan Item 5)
*   **Discrepancy Description:** The document does not explain how a sandbox with a read-only root and no live systemd daemon can verify a service fix, creating a comprehension gap for readers without unstated project assumptions.
*   **Rationale:** Architectural clarity requires explaining synthetic mock environments.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Add a dedicated subsection in Section 1.2 explaining the mechanics of synthetic service repair fixtures: mock unit files in `/tmp/mock_root/etc/systemd/system/`, mock environment variables, and standalone verification via `systemd-analyze verify`.
*   ***Proposed Edit:***
    *   Location: Section 1.2
    *   Change: Add paragraph explaining synthetic service repair architecture and how test fixtures validate remediations without live systemd daemons.

---

### 13. Undefined Technical Acronyms (`RLVR`, `AST`, `PEFT`) [`egm-comprehension`] - Severity: Nit
*   **Affected Scope:** [Lines 1, 11, 35, 43](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L1)
*   **Discrepancy Description:** Acronyms `RLVR`, `AST`, and `PEFT` appear without initial expansion.
*   **Rationale:** Comprehension standards require expanding acronyms on first use.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Expand `RLVR` (Reinforcement Learning with Verifiable Rewards), `AST` (Abstract Syntax Tree), and `PEFT` (Parameter-Efficient Fine-Tuning) on first mention.
*   ***Proposed Edit:***
    *   Location: Title, Lines 11, 35, 43
    *   Change: Add full parenthetical expansions on first occurrence.

---

### 14. Lack of Ordered Implementation Phasing & Milestones [`egm-implementation-readiness`] - Severity: Nit
*   **Affected Scope:** [Lines 268–340](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L268-L340) (Section Detailed Implementation Plan)
*   **Discrepancy Description:** The 9 target files are listed in a flat enumeration without logical execution order or phased milestones.
*   **Rationale:** Clear implementation phasing improves build reliability.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Group the 9 files into 4 sequential phases: Phase 7.1 (Sandboxed Execution & Telemetry Probe); Phase 7.2 (Synthetic Dataset & Graduated Verifiable Rewards); Phase 7.3 (Memory-Interleaved GRPO Trainer); Phase 7.4 (End-to-End Validation & Weight Fusion).
*   ***Proposed Edit:***
    *   Location: Section Detailed Implementation Plan
    *   Change: Organize the 9 files under 4 clear sub-phases with explicit milestone gates.

---

### 15. Markdown Table Blank Cell Formatting Inconsistencies [`egm-structural`] - Severity: Nit
*   **Affected Scope:** [Lines 203–216](file:///Users/zerakjamil/.gemini/antigravity/scratch/aria/docs/designs/aria_phase7_grpo_and_linux_admin.md#L203-L216) (Section 3 VRAM Budget Table)
*   **Discrepancy Description:** Empty leading cells in subcomponent rows cause inconsistent rendering across Markdown linters.
*   **Rationale:** Valid Markdown table syntax.
*   ***AI Suggestion:*** `PROPOSE FIX`
*   ***Justification:** Populate the Phase column on every row or use hierarchical row names (`Rollout: KV Cache`, `Backprop: Trainable Weights`).
*   ***Proposed Edit:***
    *   Location: Section 3 VRAM Budget Table
    *   Change: Populate all empty table cells with explicit phase names.
