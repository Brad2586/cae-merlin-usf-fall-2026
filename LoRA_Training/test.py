from transformers import AutoModelForCausalLM, AutoTokenizer

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.load_paths import load_paths

paths = load_paths()

model_path = paths["BASE_MODEL_PATH"] 
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, device_map="auto", load_in_8bit=True)

# Print all module names
for name, module in model.named_modules():
    print(name)
