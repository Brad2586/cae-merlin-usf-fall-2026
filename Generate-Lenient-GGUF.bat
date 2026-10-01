@echo off
python .\LoRA_Training\Lenient\RedPajama-INCITE-Base-3B-v1\fine_tune_lora_lenient.py
python .\LoRA_Training\Lenient\RedPajama-INCITE-Base-3B-v1\LLMLoRAMerge.py lenient
python .\llama.cpp\convert_hf_to_gguf.py "./Models/llamamodel_lenient" --outfile "./Models/GGUF-LenientModel.gguf" --outtype f16
.\llama.cpp\build\bin\Release\llama-quantize.exe .\Models\GGUF-LenientModel.gguf .\Models\GGUF-LenientModel.Q4_K_M.gguf Q4_K_M
pause