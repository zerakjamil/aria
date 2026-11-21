<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/aria-banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/aria-banner-light.svg">
    <img alt="Aria - Sovereign Personal Companion & Sandboxed Terminal Agent" src="assets/aria-banner-dark.png" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://huggingface.co/zerak12/aria-3b-gguf"><img src="https://img.shields.io/badge/🤗%20HuggingFace-aria--3b--gguf-ffd21e.svg" alt="HuggingFace GGUF"></a>
  <a href="https://huggingface.co/zerak12/aria-3b-lora"><img src="https://img.shields.io/badge/🤗%20HuggingFace-aria--3b--lora-blue.svg" alt="HuggingFace LoRA"></a>
  <a href="docs/aria_academic_paper.pdf"><img src="https://img.shields.io/badge/Academic%20Paper-PDF%20(8%20Pages)-red.svg" alt="Paper PDF"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/System%20Invariants-48%2F48%20Passing-10B981.svg" alt="Invariants"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-083834.svg" alt="License"></a>
</p>

---

## Abstract & System Identity

**Aria** is an edge-native, zero-cloud sovereign personal AI companion and sandboxed terminal agent engineered for local execution on resource-constrained consumer hardware (NVIDIA GeForce GTX 1650 Mobile, 4,096 MiB VRAM). 

By uniting **Dual-Mode Behavioral Intent Routing** (System 1: Empathetic Companion $\leftrightarrow$ System 2: Zero-Defect Systems Engineer) with **Zero-Copy Quantized Tensor Fusion** and an automated **4-Tier Safe Execution Sandbox**, Aria delivers continuous empathetic companionship and authoritative terminal agency without cloud telemetry or data egress.

---

## Empirical Benchmarks & Convergence Milestones

| Evaluation Frontier | Metric / Empirical Result | Technical Substrate |
| :--- | :--- | :--- |
| **Phase 8 Fast Turbo Convergence** | **0.9130 Final Loss** (Broke 1.0 ceiling) | 448 Curated Interaction Pairs · 404 Steps · RAM Streaming |
| **System Invariant Test Harness** | **48 / 48 Passed (100%) in 1.38s** | Native Pytest · State Machine · Security Blast Gates |
| **Edge Hardware Serving Envelope** | **1,436 MiB VRAM · 28.6–40.1 tokens/sec** | NVIDIA GTX 1650 Mobile (4,096 MiB physical capacity) |
| **Standardized Programming Sandbox** | **70.0% Pass@1 (14/20 problems)** | HumanEval/0–19 · Linux Subprocess Execution |
| **HumanEval-Fix Reflexion Repair** | **55.0% Pass Rate · 40.0% Recovery Rate** | +30.0% Absolute Gain over Single-Shot via Execution Telemetry |
| **Linguistic Entropy Preservation** | **Perplexity: 10.6705 ± 0.58596** | WikiText-2 Test Set · Fused Q4_K_M GGUF |
| **Zero-Copy Tensor Fusion Speed** | **6.2–7.8 seconds (Zero Disk Overhead)** | Custom C++17 OpenMP `llama-export-lora` Binary |

---

## Architectural Highlights

- **Dual-Mode Behavioral Intent Router:**
  - **Mode 1 (Empathetic Companion):** Emotional support, healthy rest validation, and startup founder reassurance with strictly enforced 3-sentence bounds and single-question conversational discipline.
  - **Mode 2 (Systems Engineer & Copilot):** Authoritative, zero-preamble code blocks, Linux command triage, and stack trace diagnosis with low-temperature deterministic sampling ($T=0.2$).
- **Dynamic Persona Fluidity Engine:** Deterministically compiles custom identity attributes (Gender, Name, Age, Relational Archetype e.g. brother, sister, peer mentor) while strictly preserving empathy, constitutional boundaries, and crisis quarantine invariants.
- **4-Tier Safe Execution Sandbox (ADR-005):** Deterministic AST blast-radius gating (Tier 0 Vitals $\to$ Tier 1 Workspace Mutation $\to$ Tier 2 Controlled System Ops $\to$ Tier 3 Hard-Blocked Destructive Commands rejected in 0.02ms).
- **Self-Healing Reflexion Diagnostic Loop:** Intercepts runtime errors (`exit != 0`), parses stderr diagnostics, and automatically synthesizes targeted remediation commands.
- **Crisis Quarantine Gate:** Deterministically redirects self-harm or acute distress indicators to verified 24/7 Lifeline resources (988), immediately quarantining the turn from episodic memory.

---

## Quickstart

### Option 1: Run Pre-Fused Model with Ollama

```bash
# Pull and run directly from Hugging Face
ollama run hf.co/zerak12/aria-3b-gguf:aria_q4.gguf
```

### Option 2: Build from Local Modelfile

```bash
# Clone the repository
git clone https://github.com/zerakjamil/aria.git
cd aria

# Build Ollama model
ollama create aria:3b -f models/Modelfile.aria

# Launch interactive CLI
ollama run aria:3b
```

### Option 3: Python API / FastAPI Daemon

```bash
# Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the 48 system invariant tests
pytest tests/test_invariants.py

# Launch the FastAPI daemon
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Research Publication & Documentation

- **Full Academic Paper (PDF):** [`docs/aria_academic_paper.pdf`](docs/aria_academic_paper.pdf)
- **LaTeX Source:** [`docs/aria_academic_paper.tex`](docs/aria_academic_paper.tex)
- **Postman API Collection:** [`docs/Aria_AI_Companion.postman_collection.json`](docs/Aria_AI_Companion.postman_collection.json)

```bibtex
@article{jamil2026aria,
  title   = {Sovereign Edge AI Personal Companions: Empirical Architecture, Zero-Copy Quantized Adapter Fusion, and Sandboxed Dual-Mode Terminal Agency},
  author  = {Jamil, Zerak},
  journal = {Department of Information System Engineering},
  year    = {2026},
  url     = {https://github.com/zerakjamil/aria}
}
```

---

## License

Apache License 2.0. Built by Zerak Jamil.
