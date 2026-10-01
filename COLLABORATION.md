# Team Collaboration Setup

This private repository is a source/configuration overlay for the CAE-provided
Merlin transfer package. It intentionally does not redistribute DemoHost/IOS
binaries, CAE documents, recordings, generated datasets, model files, or
Python virtual environments.

## First-time setup

1. Obtain the original CAE transfer package through the sponsor-approved
   channel and extract `IOS.Speech.To.CBD-new-base-code`.
2. Clone this private repository separately.
3. Copy the repository contents over the extracted base-code folder, allowing
   source/configuration files to be replaced.
4. In PowerShell, open the resulting base-code folder and create the test
   environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
python -m pip install -r requirements-test.txt
```

## Running the test environment

1. Start the sponsor-provided `ISSDemoHost.exe`.
2. Manually start `bin\IOS.exe` from inside its `bin` folder.
3. Run typed mock testing:

```powershell
python Pipeline\main.py --mock-llm --text-input --tts windows
```

4. Or run microphone push-to-talk testing:

```powershell
python Pipeline\main.py --mock-llm --push-to-talk --tts windows
```

The first microphone run downloads and caches Faster Whisper `small.en`.

## Command changes

Add approved mock commands to `config/mock_commands.json`. Do not change host
variables or mappings without coordinating with the team and sponsor.

## Restricted content

Do not commit CAE executables, DLLs, transferred documents, archives, models,
checkpoints, recordings, generated datasets, credentials, or `.venv`. Share
those only through the sponsor-approved delivery channel.
