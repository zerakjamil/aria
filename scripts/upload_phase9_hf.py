import os
import sys
from huggingface_hub import HfApi

TOKEN = os.getenv("HF_TOKEN")
if not TOKEN:
    print("Error: HF_TOKEN environment variable not set.")
    sys.exit(1)

api = HfApi(token=TOKEN)

print("=== Uploading Phase 9 GGUF to Hugging Face ===")
GGUF_FILE = "/srv/storage/ai-companion/models/aria_q4.gguf"
print(f"Uploading {GGUF_FILE} to zerak12/aria-3b-gguf...")
api.upload_file(
    path_or_fileobj=GGUF_FILE,
    path_in_repo="aria_q4.gguf",
    repo_id="zerak12/aria-3b-gguf",
    repo_type="model"
)
print("GGUF upload complete!")

print("\n=== Uploading Phase 9 LoRA Adapter to Hugging Face ===")
LORA_DIR = "/srv/storage/ai-companion/training/output"
print(f"Uploading LoRA files from {LORA_DIR} to zerak12/aria-3b-lora...")
for filename in ["adapter_model.safetensors", "adapter_config.json", "tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "README.md"]:
    filepath = os.path.join(LORA_DIR, filename)
    if os.path.exists(filepath):
        print(f"Uploading {filename}...")
        api.upload_file(
            path_or_fileobj=filepath,
            path_in_repo=filename,
            repo_id="zerak12/aria-3b-lora",
            repo_type="model"
        )
print("LoRA adapter upload complete!")
