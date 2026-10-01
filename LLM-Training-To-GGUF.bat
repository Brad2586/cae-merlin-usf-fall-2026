@echo off
python .\LoRA_Training\RedPajama-INCITE-Base-3B-v1\fine_tune_lora.py
python .\LoRA_Training\LLMLoRAMerge.py
python .\llama.cpp\convert_hf_to_gguf.py ".\Models\llamamodel" --outfile ".\Models\gguf-model-q8_0.gguf" --outtype q8_0
python .\Tests\validateTests.py
pause