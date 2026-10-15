# 🎙️ Merlin — Speech-Controlled Simulator Configuration

> Voice-driven interface for real-time simulator control via natural language commands.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-STT-412991?style=for-the-badge&logo=openai&logoColor=white)
![llama.cpp](https://img.shields.io/badge/llama.cpp-LLM-green?style=for-the-badge)
![TCP](https://img.shields.io/badge/TCP-Socket-orange?style=for-the-badge)

---

## Overview

**Merlin** adds voice-controlled configuration to a simulator, allowing users to change settings via spoken commands. It combines wake-word detection, speech-to-text, and natural language processing to communicate with an internal C# host using a custom binary protocol implemented at the application layer over TCP.

---

## Features

- 🎤 **Wake Word Detection** — Say `"Merlin"` to activate voice recording
- 🔇 **Silence Detection** — Automatically stops recording after ~0.3s of quiet
- 📝 **Speech-to-Text** — Converts spoken commands using OpenAI Whisper (`faster-whisper`)
- 🧠 **LLM Command Parsing** — Processes commands via RedPajama for understanding and execution
- 🔌 **TCP Communication** — Sends parsed instructions to a C# host for real-time simulator updates
- 📦 **JSON Output** — Structured, consistent output for easy parsing and dataset use

---

## Technologies Used

| Component | Technology | Notes |
|---|---| --- |
| Language | Python (3.11.9) |  You ***MUST*** be using version 3.11 for this program to run.|
| Speech-to-Text | faster-whisper (OpenAI Whisper) | |
| Wake Word | openWakeWord | |
| Silence Detection | py-webrtcvad | |
| LLM | RedPajama-INCITE-Base-3B-v1 | |
| LLM Runtime | llama.cpp | |
| Host Communication | TCP Sockets | |
| Data Format | JSON | |

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Download Models

**First Option: Run JSON File** (*recommended*)
1. Open the command prompt
2. Run `jf rt dl --spec resolve-spec.json`

    *Note*: you must have JFrog downloaded
- RedPajama, llama binaries, and the Small Faster Whisper version should now be downloaded.
    - RedPajama and faster-whisper-small should be in your Models folder
    - Llama binaries should be in the main project root
- The following models should now be downloaded:
    | Model | Folder | Notes |
    |---|---|---|
    | [`faster-whisper-small.en.zip`] | Root | Smallest size |
    | [`llama-binaries.zip`] | Root | Can delete folder & just put all files directly in project root if preferred |
    | [`llamamodel_lenient.zip`] | Models | |
    | [`llamamodel_strict.zip`] | Models | |
    | [`RedPajama-INCITE-Base-3B-v1.zip`] | Models | RedPajama LLM |
    | [`RedPajama-Lenient` Folder] | LoRA_Training/Lenient | RedPajama LLM for Lenient model|
    | [`RedPajama-Strict` Folder] | LoRA_Training/Strict | RedPajama LLM for Strict model |

3. Download *llama.cpp*
- Download WITHIN your repository-folder
- Clone and build from: [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- Build the binary in the main project root:
  ```
  # Create a build directory
   mkdir build
   cd build
   
   # Configure the project
   cmake ..
   
   # Build the project
   cmake --build . --config Release
   ```
**Second Option: Direct Download**
1. *LLM — RedPajama*
- Download from HuggingFace: [`togethercomputer/RedPajama-INCITE-Base-3B-v1`](https://huggingface.co/togethercomputer/RedPajama-INCITE-Base-3B-v1/tree/main)
- Place in the `models/` folder

2. *Speech-to-Text — faster-whisper*
- Download one of the following models and place in the project root:

    | Model | Size | Notes |
    |---|---|---|
    | [`faster-whisper-small.en`](https://huggingface.co/Systran/faster-whisper-small.en) | Small | Fastest |
    | [`faster-whisper-medium.en`](https://huggingface.co/Systran/faster-whisper-medium.en) | Medium | Balanced |
    | [`faster-whisper-large-v3`](https://huggingface.co/Systran/faster-whisper-large-v3) | Large | Most accurate |

### 3. Install Python Dependencies
**Option 1: Download Dependencies Altogether**
- If you are running on Python 3.11 already, you can install the dependencies by using the commands below:
```bash
pip install faster-whisper
pip install numpy pyaudio webrtcvad openwakeword peft transformers==4.47.1
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```
> ⚠️ Ensure model file paths in the program match the locations where you placed the downloaded models.

**Option 2: Virtual Environment Download**
- If you are NOT already running on Python 3.11 (for example, using Python 3.14), you may need to create a virtual environment to run Python 3.11 and download the dependencies.
- *Note:* Any dependencies downloaded in a virtual environment will need to be redownloaded each time you deactivate and reactivate the virtual environment.
1. Create a virtual environment.
```bash
# Create environment
py -3.11 -m venv .venv

# Activate environment
.\.venv\Scripts\activate

# Deactivate (only when necessary)
deactivate
```
2. Download dependencies (not listed in order, may need to download more as needed based on terminal output).
```bash
faster-whisper==1.2.1
numpy==2.4.6
pyaudio==0.2.14
webrtcvad==2.0.10
openwakeword==0.5.0
peft==0.19.1
transformers==4.47.1
torch==2.5.1 
torchvision==0.20.1
torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
piper-tts==1.4.2
scikit-build-core==0.9.2
cmake==3.21
scipy==1.17.1
sounddevice==0.5.5
```
---

## How to Run

**Step 1** — Generate both the strict and lenient GGUF model files:
```bash
.\generate-strict-gguf.bat
.\generate-lenient-gguf.bat
```

**Step 2** — Launch the ISS Host application. (Folder: `\\rftnfl\data\jobs\DISPLAY GROUP\DemoHost`)

**Step 3** — Start the voice command pipeline:
```bash
python Pipeline/main.py
```

### Companion Dashboard

The sponsor-provided DemoHost and IOS programs are compiled applications, so
their windows cannot be safely restyled without their source code. Merlin
provides a modern companion dashboard that launches those programs and
displays their integration status without modifying either executable.

Start it from the project root:

```bash
python Dashboard/main.py
```

The dashboard shows:

- Merlin, simulator-server, and active-model status
- The latest voice transcription and how it was processed
- Requested variable changes with timestamps and values
- Reconnecting/connected server state
- Buttons for launching Merlin, DemoHost, and IOS

Use **Configure Paths** if the supplied executable locations differ on your
machine. They are saved in `config/dashboard.json`. Dashboard entries are
labeled **Requested** because the current host protocol does not provide
read-back confirmation for every Set Variable operation.

---

## Usage

1. Say **"Merlin"** to activate the system
2. Immediately state your command, for example:
   ```
   "Merlin, activate Engine 1 fire malfunction."
   ```
3. After ~0.75 seconds of silence, the program processes the command
4. The command is parsed by the LLM and sent to the ISS host for execution
5. To close: Use the command: "Merlin, Close the Program"`

After the wake word is detected, Merlin waits up to five seconds for the
command to begin. You may pause between saying **"Merlin"** and the command.
The timings and Whisper accuracy setting can be adjusted in the `audio` block
of `config/config.json`.

### Noise reduction

Merlin measures ambient sound while waiting for the wake word and uses that
measurement to reject low-level interference during command initiation. It
also requires sustained speech before recording, ignores very short noise
events, and filters low-frequency rumble before transcription.

The noise controls are in the `audio` block of `config/config.json`:

- `noise_reduction_enabled`: Enables or disables adaptive filtering.
- `vad_aggressiveness`: WebRTC speech filtering from `0` to `3`; higher values reject more sound.
- `speech_confirmation_frames`: Consecutive 30 ms speech frames required to begin a command.
- `minimum_command_duration`: Rejects events shorter than this number of seconds.
- `noise_gate_multiplier`: Required loudness relative to measured ambient noise.
- `highpass_cutoff_hz`: Removes frequencies below this approximate cutoff.

If background noise still starts commands, increase `noise_gate_multiplier`
gradually (for example, from `1.8` to `2.1`). If Merlin begins missing quiet
speakers, lower it or reduce `vad_aggressiveness`.

### Automatic server reconnection

If the simulator TCP connection is interrupted after startup, Merlin
automatically reconnects, repeats the protocol handshake, recreates the host
update page, refreshes variable indices, and resumes keep-alive requests.
Commands issued while disconnected report an error instead of writing to a
stale socket.

Reconnect behavior is configured in the `communication` block of
`config/config.json`:

- `auto_reconnect`: Enables or disables reconnection.
- `reconnect_initial_delay`: Delay after the first unsuccessful retry.
- `reconnect_max_delay`: Maximum delay between retries.
- `reconnect_backoff`: Multiplier applied to the delay after each failure.
- `reconnect_max_attempts`: Maximum retries; `0` means retry until shutdown.
- `keep_alive_interval`: Seconds between connection health checks.

---

## Add a Custom Voice Command

Run the interactive generator from the project root:

```bash
python Tools/command_generator.py
```

The generator asks for:

- A readable command name
- The simulator variable name
- The value to send
- One or more spoken phrases (separated with `|`)
- The variable type and display name if the variable is new
- Array dimensions and indices when applicable

It updates `config/variables.xml` when a new host variable is needed and stores
the voice command in `config/voice_commands.json`. Generated phrases are matched
after speech-to-text and before the LLM, so retraining the model is not required.
Restart `python Pipeline/main.py` after adding a command.

For example, an Engine 5 toggle request can be generated non-interactively:

```bash
python Tools/command_generator.py --name "Activate Engine 5 Fire" --variable "MALF_IF.TOGGLE_REQ" --value 335 --phrase "activate engine 5 fire malfunction" --phrase "trigger engine 5 fire"
```

The variable must be supported by the connected simulator host. The generator
can configure Merlin, but it cannot create a variable inside the host itself.

---

## Recommendations for Implementation

### 🎯 Speech-to-Text Accuracy

For more accurate transcriptions, consider fine-tuning Whisper (or another STT model) on domain-specific audio — particularly for technical simulator terminology.

> **Suggested approach:** A **LoRA (Low-Rank Adaptation)** fine-tuning strategy allows efficient adaptation of Whisper without retraining the full model. Collect labeled audio samples of actual simulator commands and fine-tune on that dataset to significantly reduce transcription errors.

### 🔑 Wake Word Licensing

> ⚠️ The current `"Merlin"` wake word model files (`.onnx` and `.tflite`) do not have a clear open license available for distribution.

For production or public release, it is recommended to **build a custom wake word model** using the openWakeWord training pipeline:

1. Collect audio clips of the target wake word spoken in various conditions
2. Train a custom `.onnx` / `.tflite` model using the openWakeWord training module
3. Replace the existing model files with your newly trained, properly licensed versions
4. Test across different speakers, accents, and noise environments

---

### Suggested Improvements
- [ ] Clearing Approach Variables, The Strict Model currently sends an empty string to each of the variables for the "Clear Approach" command, but the code cannot currently accept this input. 
- [x] Add a slight sliding audio buffer for the first word after the wake word.
- [ ] Add ability to pull data from the ISS Host. 

### Accuracy Improvement 
- [ ] Use A Larger LLM Model, currently using 3B (Base Version Suggested for LoRA Training)
- [ ] Use A Larger Whisper Model
- [ ] Generate more training dataset lines - Currently use ~2500-3000

---
