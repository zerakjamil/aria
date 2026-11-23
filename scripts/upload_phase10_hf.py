import os
import sys
from huggingface_hub import HfApi

TOKEN = os.getenv('HF_TOKEN')
if not TOKEN:
    token_file = os.path.expanduser('~/.cache/huggingface/token')
    if os.path.exists(token_file):
        with open(token_file) as f:
            TOKEN = f.read().strip()

if not TOKEN:
    print('Error: HF_TOKEN not found.')
    sys.exit(1)

api = HfApi(token=TOKEN)

gguf_readme = """---
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
tags:
- gguf
- llama.cpp
- ollama
- q4_k_m
- rlvr
- grpo
- reinforcement-learning
- code-repair
- terminal-agent
pipeline_tag: text-generation
---

<div align="center">
  <img src="https://huggingface.co/zerak12/aria-3b-gguf/resolve/main/aria-banner.png" width="100%" alt="Aria Banner">
</div>

# Aria 3B GGUF (Phase 10 GRPO & RLVR Self-Evolution)

**Aria** is a sovereign personal AI companion and sandboxed terminal agent fine-tuned from `Qwen/Qwen2.5-3B-Instruct` on edge hardware (NVIDIA GeForce GTX 1650 Mobile, 4,096 MiB physical VRAM).

Phase 10 pioneers **On-Device GRPO (Group Relative Policy Optimization)** and **RLVR (Reinforcement Learning with Verifiable Rewards)**:
1. **Verifiable Unit Assertion Sandbox**: Candidate solutions are executed in a dual-tier subprocess sandbox against strict ground-truth invariants.
2. **Normalized Group Relative Advantages**: Groups ($G=4$) are sampled with temperature $T=0.7$; advantage $\\hat{A}_i = \\frac{r_i - \\bar{r}}{\\sigma_r + 10^{-4}}$ reinforces contrastive trajectories ($\\sigma_R > 0$).
3. **Execution-Guided Reflexion**: Failed trajectories undergo automated self-repair powered by `TracebackDistiller`.

## Model Details
- **Developer**: Zerak Jamil (Department of Information System Engineering, Erbil Polytechnic University)
- **Base Model**: `Qwen/Qwen2.5-3B-Instruct`
- **Architecture**: Qwen2ForCausalLM (3.09B parameters)
- **Quantization**: Q4_K_M (fused via llama.cpp / soup-cli)
- **Training Data**: 557 samples (542 Phase 9 anchors + 15 verified RLVR golden trajectories)
- **Context Window**: 4,096 tokens
- **Invariants**: 109/109 Verification Invariants Passed (100% pass rate)

## Empirical Benchmarks & Hardware Envelopes

| Metric / Benchmark | Result | Environment / Method |
| :--- | :--- | :--- |
| **Phase 10 Training Loss** | **0.8113 -> 0.0812** | 557 Samples · 753 Steps · 3 Epochs |
| **Mean Token Accuracy** | **78.7% - 82.3%** | Final Cosine Decay Phase |
| **Edge Hardware Serving Envelope** | **1,436 MiB VRAM · 28.6–40.1 tok/s** | NVIDIA GTX 1650 Mobile (4,096 MiB physical capacity) |
| **System Invariant & Test Suite** | **109 / 109 Passed (100%)** | 48 Invariants + 10 Counterfactual + 8 Harness + RLVR |
| **Reflexion Execution-Guided Repair** | **55.0% Pass Rate · 40.0% Recovery** | +30.0% Absolute Gain over Single-Shot |

## Files in Repository
- `aria_q4.gguf` (1.8 GB): Full fused Q4_K_M quantized model for Ollama and llama.cpp.
- `aria_adapter_v10.gguf` (14.7 MB): Standalone GGUF LoRA adapter for Phase 10.
- `Modelfile`: Ready-to-use Ollama Modelfile.
- `aria-banner.png`: High-resolution emblem banner.
- `aria-emblem-square.png`: Square avatar / icon.

## Quick Start

### Using Ollama
```bash
# Pull and run directly from Hugging Face
ollama run hf.co/zerak12/aria-3b-gguf:aria_q4.gguf
```

### GitHub Repository & Paper
- Codebase & Harness: [github.com/zerakjamil/aria](https://github.com/zerakjamil/aria)
- Academic Paper: [docs/aria_academic_paper.pdf](https://github.com/zerakjamil/aria/blob/main/docs/aria_academic_paper.pdf)
"""

lora_readme = """---
library_name: peft
model_name: aria-3b-lora
tags:
- base_model:adapter:Qwen/Qwen2.5-3B-Instruct
- lora
- rlvr
- grpo
- sft
- transformers
- trl
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
pipeline_tag: text-generation
---

<div align="center">
  <img src="https://huggingface.co/zerak12/aria-3b-lora/resolve/main/aria-banner.png" width="100%" alt="Aria Banner">
</div>

# Aria 3B LoRA Adapter (Phase 10 GRPO & RLVR Self-Evolution)

Official low-rank adapter (rank 16, alpha 32) fine-tuned on `Qwen/Qwen2.5-3B-Instruct` incorporating GRPO advantage weighting and RLVR verified golden trajectories across 557 samples.

- **Developer**: Zerak Jamil (Department of Information System Engineering, Erbil Polytechnic University)
- **Base Model**: `Qwen/Qwen2.5-3B-Instruct`
- **Training Epochs**: 3 (753 total optimization steps)

## Quick Start

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

base_model_name = "Qwen/Qwen2.5-3B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
base_model = AutoModelForCausalLM.from_pretrained(base_model_name, torch_dtype="auto", device_map="auto")
model = PeftModel.from_pretrained(base_model, "zerak12/aria-3b-lora")
```

## System Links
- GGUF Quantized Model: [huggingface.co/zerak12/aria-3b-gguf](https://huggingface.co/zerak12/aria-3b-gguf)
- Full Project Codebase: [github.com/zerakjamil/aria](https://github.com/zerakjamil/aria)
"""

print('--- Uploading Phase 10 Artifacts to zerak12/aria-3b-gguf ---')
with open('/srv/storage/ai-companion/models/README_GGUF_PHASE10.md', 'w') as f:
    f.write(gguf_readme)

api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/README_GGUF_PHASE10.md',
    path_in_repo='README.md',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)
print('GGUF README uploaded.')

api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/aria_q4.gguf',
    path_in_repo='aria_q4.gguf',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)
print('aria_q4.gguf uploaded.')

api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/aria_adapter_v10.gguf',
    path_in_repo='aria_adapter_v10.gguf',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)
print('aria_adapter_v10.gguf uploaded.')

api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/Modelfile.aria',
    path_in_repo='Modelfile',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)
print('Modelfile uploaded.')

print('--- Uploading Phase 10 LoRA Adapter to zerak12/aria-3b-lora ---')
with open('/srv/storage/ai-companion/models/README_LORA_PHASE10.md', 'w') as f:
    f.write(lora_readme)

api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/README_LORA_PHASE10.md',
    path_in_repo='README.md',
    repo_id='zerak12/aria-3b-lora',
    repo_type='model'
)

LORA_DIR = '/srv/storage/ai-companion/training/output'
for filename in ['adapter_model.safetensors', 'adapter_config.json', 'tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja']:
    filepath = os.path.join(LORA_DIR, filename)
    if os.path.exists(filepath):
        print(f'Uploading {filename}...')
        api.upload_file(
            path_or_fileobj=filepath,
            path_in_repo=filename,
            repo_id='zerak12/aria-3b-lora',
            repo_type='model'
        )

print('All Phase 10 Hugging Face assets successfully uploaded!')
