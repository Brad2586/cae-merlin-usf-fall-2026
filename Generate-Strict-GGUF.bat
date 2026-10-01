@echo off
python .\LoRA_Training\Strict\RedPajama-INCITE-Base-3B-v1\fine_tune_lora_strict.py
python .\LoRA_Training\Strict\RedPajama-INCITE-Base-3B-v1\LLMLoRAMerge.py
python .\llama.cpp\convert_hf_to_gguf.py "./Models/llamamodel_strict" --outfile "./Models/GGUF-StrictModel.gguf" --outtype f16
.\llama.cpp\build\bin\Release\llama-quantize.exe .\Models\GGUF-StrictModel.gguf .\Models\GGUF-StrictModel.Q4_K_M.gguf Q4_K_M
pause