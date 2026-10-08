import os
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))
from config.load_paths import load_paths

paths = load_paths()

# -----------------------------
# 1. Model & Tokenizer
# -----------------------------
MODEL_PATH = paths["BASE_MODEL_PATH"]  
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# Ensure padding token exists
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",      # automatically chooses GPU/CPU
    load_in_8bit=True       # optional quantization
)

# -----------------------------
# 2. LoRA Configuration
# -----------------------------
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["query_key_value"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

# -----------------------------
# 3. Load Dataset
# -----------------------------
data_files = {"train": paths["DATASET_PATH_LENIENT"]}
if os.path.exists("val.jsonl"):
    data_files["validation"] = "val.jsonl"

dataset = load_dataset("json", data_files=data_files)

# -----------------------------
# 4. Tokenize Dataset
# -----------------------------
def tokenize_function(example):
    # Convert dict to JSON string
    output_json = json.dumps(example['output'])
    text = f"Input: {example['input']}\nOutput: {output_json}"
    
    return tokenizer(
        text,
        truncation=True,
        max_length=128,  # increase if needed
        padding="max_length"
    )

tokenized_dataset = dataset.map(tokenize_function, batched=False)

# -----------------------------
# 5. Set Labels
# -----------------------------
def add_labels(example):
    # For causal LM, labels = input_ids
    example["labels"] = example["input_ids"].copy()
    return example

tokenized_dataset = tokenized_dataset.map(add_labels)

# -----------------------------
# 6. Training Arguments
# -----------------------------
training_args = TrainingArguments(
    output_dir=paths["TRAINING_OUTPUT_DIR_LENIENT"],  # save both LoRA weights and tokenizer here
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=3e-4,
    num_train_epochs=3,
    logging_steps=10,
    save_steps=50,
    save_total_limit=2,
    fp16=True,
    report_to=[],  # disables W&B logging
)

# -----------------------------
# 7. Trainer
# -----------------------------
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"] if "validation" in tokenized_dataset else None,
)

# -----------------------------
# 8. Train
# -----------------------------
trainer.train()

# -----------------------------
# 9. Save LoRA Weights and Tokenizer
# -----------------------------
os.makedirs(training_args.output_dir, exist_ok=True)
model.save_pretrained(training_args.output_dir)
tokenizer.save_pretrained(training_args.output_dir)

print(f"LoRA fine-tuning complete. Weights saved to {training_args.output_dir}")
