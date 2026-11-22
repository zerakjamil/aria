import os
import sys
from huggingface_hub import HfApi

TOKEN = os.getenv("HF_TOKEN")
if not TOKEN:
    print("Error: HF_TOKEN environment variable not set.")
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
- conversational
- code-repair
pipeline_tag: text-generation
---

<div align="center">
  <img src="https://huggingface.co/zerak12/aria-3b-gguf/resolve/main/aria-banner.png" width="100%" alt="Aria Banner">
</div>

# Aria 3B GGUF (Phase 9 Ultra-Hard Distillation)

**Aria** is a sovereign personal AI companion and sandboxed terminal agent fine-tuned from `Qwen/Qwen2.5-3B-Instruct` on edge hardware (NVIDIA GeForce GTX 1650 Mobile, 4,096 MiB VRAM).

## Model Details
- **Developer**: Zerak Jamil (Department of Information System Engineering)
- **Base Model**: `Qwen/Qwen2.5-3B-Instruct`
- **Architecture**: Qwen2ForCausalLM (3.09B parameters)
- **Quantization**: Q4_K_M (fused via llama.cpp)
- **Training**: 9 iterative phases (542 ultra-hard curated interaction pairs), achieving an all-time low training loss of **0.6143** and peak token accuracy of **91.71%**.
- **Context Window**: 4,096 tokens
- **Invariants**: 48/48 System Invariants Verified (100% pass rate)

## Files in Repository
- `aria_q4.gguf` (1.8 GB): Full fused Q4_K_M quantized model for Ollama and llama.cpp.
- `aria_adapter_v9.gguf` (14.7 MB): Standalone GGUF LoRA adapter (rank 16, alpha 32).
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

# Aria 3B LoRA Adapter (Phase 9 Ultra-Hard Distillation)

Official low-rank adapter (rank 16, alpha 32) fine-tuned on `Qwen/Qwen2.5-3B-Instruct` across 542 ultra-hard curated interaction pairs, achieving an all-time low training loss of **0.6143** and peak token accuracy of **91.71%**.

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
- Academic Paper: [docs/aria_academic_paper.pdf](https://github.com/zerakjamil/aria/blob/main/docs/aria_academic_paper.pdf)
"""

with open('/srv/storage/ai-companion/models/README_GGUF_PHASE9.md', 'w') as f:
    f.write(gguf_readme)

print('Uploading GGUF README...')
api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/README_GGUF_PHASE9.md',
    path_in_repo='README.md',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)

print('Uploading aria_adapter_v9.gguf...')
api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/aria_adapter_v9.gguf',
    path_in_repo='aria_adapter_v9.gguf',
    repo_id='zerak12/aria-3b-gguf',
    repo_type='model'
)

with open('/srv/storage/ai-companion/models/README_LORA_PHASE9.md', 'w') as f:
    f.write(lora_readme)

print('Uploading LoRA README...')
api.upload_file(
    path_or_fileobj='/srv/storage/ai-companion/models/README_LORA_PHASE9.md',
    path_in_repo='README.md',
    repo_id='zerak12/aria-3b-lora',
    repo_type='model'
)

print('All Hugging Face assets successfully finalized!')
