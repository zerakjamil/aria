# Project Submission: Aria — Sovereign Edge AI Personal Companion & Terminal Agent

**Student**: Zerak Jamil  
**Course**: Artificial Intelligence  
**Institution**: Applied AI Systems & Edge Computing Group  
**Academic Paper**: Included (`docs/aria_academic_paper.pdf`)  

---

## 🔗 Project Links

* **GitHub Repository (Code, Training Pipelines & Tests)**:  
  👉 [https://github.com/zerakjamil/aria](https://github.com/zerakjamil/aria)

* **Hugging Face Hub (Model Weights & GGUF Artifacts)**:  
  👉 [https://huggingface.co/zerak12/aria-3b](https://huggingface.co/zerak12/aria-3b)

---

## ⚡ Quick Test Command (1-Click Run)

To test the model locally in any terminal using Ollama:

```bash
ollama run hf.co/zerak12/aria-3b
```

---

## 🧠 Model Architecture & Layer Mechanics

* **Base Foundation Model**: `Qwen2.5-3B-Instruct` (36 decoder transformer layers, vocabulary size 151,936).
* **Targeted LoRA Projections**: Parameter-efficient low-rank adaptation on attention query ($q_{\text{proj}}$) and value ($v_{\text{proj}}$) projection matrices across all 36 layers (rank $r=16$, scale $\alpha=32$).
* **Mechanistic SVD Verification**: Computed Singular Value Decomposition directly on raw weight deltas ($\Delta W$ across 72 projections). Condition number $\kappa \approx 13.75$ and effective rank $r_{\text{eff}} = 11.71$ (73.2% capacity utilization), mathematically ruling out rank collapse and capacity saturation.
* **Layer-Wise Gradient Streaming**: Engineered streaming backpropagation through PyTorch autograd, fitting 3B training within a 4 GB VRAM consumer edge boundary (NVIDIA GTX 1650 Mobile).
* **Zero-Copy Quantized Fusion**: Compiled custom C++ `llama-export-lora` to execute in-memory dequantization, low-rank tensor addition, and re-quantization into 4-bit GGUF in 6.2 seconds without intermediate disk allocation.

---

## 📊 Empirical Convergence & Multi-Phase Progression

| Phase | Description / Curriculum | Corpus Size | Train Loss | Val Loss | Val Token Accuracy | Compute (FLOPs) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 1** | Baseline LoRA | 70 | 4.7275 → 4.1259 | 3.4259 | 45.29% | $2.31 \times 10^{15}$ |
| **Phase 2** | Distillation LoRA | 91 | 4.6355 → 3.8288 | 4.1367 | 43.98% | $3.08 \times 10^{15}$ |
| **Phase 3** | Multi-Persona Routing | 112 | 4.5235 → 3.6088 | 2.7469 | 50.88% | $3.69 \times 10^{15}$ |
| **Phase 4** | Frontier Distillation | 160 | 3.3820 → 2.8474 | 2.9453 | 50.48% | $5.30 \times 10^{15}$ |
| **Phase 5** | Self-Evolution RLVR | 163 | 4.0724 → 2.9326 | 2.5557 | 53.01% | $5.45 \times 10^{15}$ |
| **Phase 6** | Struggle Distillation | 175 | 3.7332 → 2.9816 | 2.3617 | 57.34% | $5.85 \times 10^{15}$ |
| **Phase 7** | GRPO & Linux Sandbox Triage | 348 | 3.3658 → 1.3556 | **0.3226** | **90.94%** | $2.32 \times 10^{16}$ |
| **Phase 8** | Stress-Test Hard Mining | 448 | 2.0968 → **0.9130** | 0.8520 | 80.7%–85.3% | $3.15 \times 10^{16}$ |

* **Linguistic Entropy Check**: Held-out WikiText-2 perplexity ($PPL = 10.67 \pm 0.58$, $\mathcal{L}_{CE} = 2.3675$ nats/token), verifying zero linguistic collapse or repetitive degeneration.

---

## 🛡️ Benchmark & Test Suite Verification

* **HumanEval-Fix Debugging Benchmark ($N=20$)**:
  * Single-Shot Baseline: 25.0% (5/20)
  * Sandbox-Guided Self-Repair ($K_{\max}=3$): **55.0% (11/20)** (+30.0% absolute recovery delta, 40.0% bug repair rate).
* **System Invariants**: 48 out of 48 automated test invariants passing 100% green on edge server `ayewar`.
