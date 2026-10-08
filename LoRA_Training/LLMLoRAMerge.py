from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.load_paths import load_paths

paths = load_paths()

# Accept 'strict' or 'lenient' as CLI arg; default to 'strict' for backward compatibility.
mode = sys.argv[1].lower() if len(sys.argv) > 1 else "strict"
if mode not in ("strict", "lenient"):
    print(f"Unknown mode '{mode}' - expected 'strict' or 'lenient'")
    sys.exit(1)

base_model_path   = paths["BASE_MODEL_PATH"]
lora_model_path   = paths[f"LORA_MODEL_PATH_{mode.upper()}"]
merged_model_path = paths[f"MERGED_MODEL_PATH_{mode.upper()}"]

print(f"Merging {mode} adapter:")
print(f"  base    : {base_model_path}")
print(f"  adapter : {lora_model_path}")
print(f"  output  : {merged_model_path}")

model = AutoModelForCausalLM.from_pretrained(base_model_path, torch_dtype=torch.float16)
model = PeftModel.from_pretrained(model, lora_model_path)

# Merge LoRA weights permanently
model = model.merge_and_unload()
model.save_pretrained(merged_model_path)

# Also save the tokenizer so downstream conversion (convert_hf_to_gguf.py)
# can find it alongside the model weights.
tokenizer = AutoTokenizer.from_pretrained(base_model_path)
tokenizer.save_pretrained(merged_model_path)

print(f"Done. Merged {mode} model saved to {merged_model_path}")
