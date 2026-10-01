import argparse
import json
import os
import sys
import warnings

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from parse_llm_output import LLMOutputParser
from communication_client import CommunicationClient
from generate_llm import GenerateLLM
from exit_handler import ExitHandler
from logger import log
from mock_llm import DatasetMockModel
from text_input import ConsoleTTS, TextInputPipeline

from config.load_paths import load_paths


paths = load_paths()

THRESHOLDS = {
    "merlin": 0.5,
    "merlin2": 0.5,
    "hey_merlin": 0.5,
}

DEBOUNCE_TIME = 0.25


def run_voice_pipeline():
    # llm and parser are set up once in __main__, reuse them
    while True:
        text = audio_pipeline.listen_and_transcribe()
        print("\nTranscription:")
        print(text)

        prompt = f"input: {text}\noutput:"
        llm_output = llm.generate_from_llm(prompt, 150)

        print("Output:\n", llm_output)
        parser.parse_LLM_output(llm_output)


import xml.etree.ElementTree as ET


def load_variables(xml_path):
    """Parse variable metadata from XML, including alias."""

    TYPE_CODE_MAP = {
        "char":      0,
        "int8":      1,
        "int16":     2,
        "int32":     3,
        "int64":     4,
        "float":     5,
        "double":    6,
        "pointer":   7,
        "boolean":   1,
        "integer":   3,
    }

    tree = ET.parse(xml_path)
    root = tree.getroot()
    variables = []

    for var in root.iter("variable"):
        name = var.get("name")
        if not name:
            continue

        type_str = (var.get("type") or "").lower()
        type_code = TYPE_CODE_MAP.get(type_str, 0)  # fallback = Character/unknown
        common_name = var.get("common_name", name)

        # NEW: get alias from XML if present
        alias = var.get("alias")
        # If missing alias, default to name (or you can leave as None)
        if alias is None:
            alias = name

        # Dimensions: dims="4" or dims="3 4" etc.
        dims_attr = (var.get("dims") or "").strip()
        if dims_attr:
            dim_tokens = dims_attr.replace(",", " ").split()
            try:
                dimensions = [int(tok) for tok in dim_tokens]
            except ValueError:
                dimensions = []
        else:
            dimensions = []

        num_dims = len(dimensions)

        # Default values
        default_raw = (var.get("default") or "").strip()
        if default_raw:
            default_tokens = default_raw.split()
            default_values = default_tokens
        else:
            default_values = None

        variables.append({
            "name": name,
            "type_code": type_code,
            "common_name": common_name,
            "num_dims": num_dims,
            "dimensions": dimensions,
            "default": default_values,
            "alias": alias,
        })

    return variables


def load_mappings(mapping_xml_path):
    tree = ET.parse(mapping_xml_path)
    root = tree.getroot()

    mappings = []

    for cmd in root.iter("command"):
        command_name = (cmd.findtext("name") or "").strip()
        variable = (cmd.findtext("variable") or "").strip()
        common_name = (cmd.findtext("common_name") or "").strip()
        alias = (cmd.findtext("alias") or "").strip()
        value_text = (cmd.findtext("value") or "").strip()
        index_text = (cmd.findtext("index") or "").strip()
        time_text = (cmd.findtext("time") or "").strip()  # NEW

        if not variable:
            continue

        try:
            value = int(value_text) if value_text else None
        except ValueError:
            value = None

        try:
            idx = int(index_text) if index_text else None
        except ValueError:
            idx = None

        try:
            delay = float(time_text) if time_text else None
        except ValueError:
            delay = None

        mappings.append({
            "command_name": command_name,
            "variable": variable,      # "MALF_IF.TOGGLE_REQ"
            "common_name": common_name,
            "alias": alias,            # "ENGINE_1_MALF"
            "value": value,            # 331
            "index": idx,              # 0
            "time": delay,             # Per-command delay in seconds, or None
        })

    return mappings

def load_alias_mappings(mapping_xml_path):
    """
    Parse mapping.xml and build an alias_to_name dict of the form:

        ENGINE_1_MALF -> MALF_IF.TOGGLE_REQ
        APPROACH      -> APPROACH
        ...

    We only need variable and alias per command; index/value are handled separately.
    """
    tree = ET.parse(mapping_xml_path)
    root = tree.getroot()

    alias_to_name = {}

    for cmd in root.iter("command"):
        variable = (cmd.findtext("variable") or "").strip()
        # variable = variable.upper()   # normalize
        alias = (cmd.findtext("alias") or "").strip()

        if not variable:
            continue

        # Direct alias -> variable mapping
        if alias:
            alias_to_name[alias] = variable

        # Map canonical variable name to itself
        alias_to_name[variable] = variable

    return alias_to_name


running = True

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Run the Merlin voice-command pipeline."
    )
    argument_parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use deterministic dataset matching instead of unavailable GGUF models.",
    )
    input_group = argument_parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--text-input",
        action="store_true",
        help="Read commands from the console instead of the microphone.",
    )
    input_group.add_argument(
        "--push-to-talk",
        action="store_true",
        help="Press Enter and speak; bypasses the unavailable wake-word model.",
    )
    argument_parser.add_argument(
        "--tts",
        choices=("auto", "windows", "console", "piper"),
        default="auto",
        help=(
            "Response backend. Auto uses console for text input and Windows "
            "speech otherwise (default: auto)."
        ),
    )
    argument_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Simulator communication server address (default: 127.0.0.1).",
    )
    argument_parser.add_argument(
        "--port",
        default=10013,
        type=int,
        help="Simulator communication server port (default: 10013).",
    )
    argument_parser.add_argument(
        "--mock-threshold",
        default=0.78,
        type=float,
        help="Minimum fuzzy-match confidence in mock mode (default: 0.78).",
    )
    args = argument_parser.parse_args()

    if not 0.0 <= args.mock_threshold <= 1.0:
        argument_parser.error("--mock-threshold must be between 0 and 1")

    tts_backend = args.tts
    if tts_backend == "auto":
        tts_backend = "console" if args.text_input else "windows"

    if tts_backend == "console":
        tts = ConsoleTTS()
    elif tts_backend == "windows":
        from windows_tts import WindowsTTS
        tts = WindowsTTS()
    else:
        from tts import PiperTTS
        tts = PiperTTS(paths["TTS_VOICE_PATH"])

    if args.text_input:
        audio_pipeline = TextInputPipeline()

    print(f"Connecting to simulator at {args.host}:{args.port}...")
    communication_client = CommunicationClient(args.host, args.port, tts)
    if not communication_client.connect():
        print("Could not connect to server or initialization handshake failed")
        sys.exit(1)

    if not args.text_input:
        from transcription_normalizer import TranscriptNormalizer

        with open(paths["VARIATIONS_PATH"], "r") as f:
            variations_data = json.load(f)

        normalizer = TranscriptNormalizer(variations_data)

        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

        if args.push_to_talk:
            from push_to_talk import PushToTalkPipeline

            audio_pipeline = PushToTalkPipeline(
                device=device,
                whisper_name="small.en",
                compute_type="float16" if device == "cuda" else "int8",
                normalizer=normalizer,
            )
        else:
            from audio_pipeline import AudioPipeline
            from openwakeword.model import Model

            oww = Model(
                wakeword_models=paths["MODEL_PATHS"],
                inference_framework="tflite"
            )
            audio_pipeline = AudioPipeline(
                wakeword_model=oww,
                thresholds=THRESHOLDS,
                debounce_time=DEBOUNCE_TIME,
                whisper_processor=None,
                whisper_model=None,
                device=device,
                whisper_name="small.en",
                compute_type="float16" if device == "cuda" else "int8",
                normalizer=normalizer
            )

    if args.mock_llm:
        print("Using dataset-backed mock LLM; GGUF files will not be loaded.")
        lenient_model_llm = DatasetMockModel(
            paths["DATASET_PATH_LENIENT"],
            threshold=args.mock_threshold,
            custom_commands_path=paths["MOCK_COMMANDS_PATH"],
        )
        strict_model_llm = DatasetMockModel(
            paths["DATASET_PATH_STRICT"],
            threshold=args.mock_threshold,
            custom_commands_path=paths["MOCK_COMMANDS_PATH"],
        )
    else:
        from llama_cpp import Llama

        lenient_model_llm = Llama(
            model_path=paths["GGUF_MODEL_PATH_LENIENT"],
            n_ctx=2048,
            n_threads=10,
            seed=42,
            n_gpu_layers=-1,
            n_batch=512,
            n_ubatch=512,
            low_vram=False,
            cache=True,
            use_mmap=True,
            use_mlock=True,
            verbose=False
        )

        strict_model_llm = Llama(
            model_path=paths["GGUF_MODEL_PATH_STRICT"],
            n_ctx=2048,
            n_threads=10,
            seed=42,
            n_gpu_layers=-1,
            n_batch=512,
            n_ubatch=512,
            low_vram=False,
            cache=True,
            use_mmap=True,
            use_mlock=True,
            verbose=False
        )
    
    variables_to_track = load_variables(paths["XML_PATH"])

    # DEBUG: print variables in dictionary in requested format
    print("Variables in dictionary:")
    for v in variables_to_track:
        print(
            f"name={v['name']}, "
            f"type_code={v['type_code']}, "
            f"common_name={v['common_name']}, "
            f"num_dims={v['num_dims']}, "
            f"dimension={v['dimensions']}, "
            f"default={v['default']}, "
            f"alias={v['alias']}"
        )

    # Build host dictionary using spec-compliant Add Update Page / Request Update flow.
    host_dict = communication_client.create_update_page(variables_to_track)

    # DEBUG: print host_dict similar to your example
    print("=== HOST DICT ===")
    if isinstance(host_dict, dict):
        for key, meta in host_dict.items():
            # meta expected structure: {"index": int, "type": int, "value": bytes or similar}
            idx = meta.get("index")
            type_code = meta.get("type")
            value = meta.get("value")
            print(f"{key} -> index={idx}, type={type_code}, value={value}")
    else:
        print("HOST DICT is not a dict:", host_dict)
    print("=== END HOST DICT ===")

    # Build keep-alive variable list from host_dict
    keep_alive_vars = []
    for name, meta in host_dict.items():
        keep_alive_vars.append({
            "name": name,
            "index": meta["index"],
            "type": meta.get("type", 0),
            "num_dims": meta.get("num_dims", 0),
            "dimensions": meta.get("dimensions", []),
        })

    # Configure CommunicationClient’s keep-alive
    communication_client.set_keep_alive_variables(keep_alive_vars, list_type=0)

    # Load mappings and alias_to_name from mapping.xml
    mappings = load_mappings(paths["MAPPING_PATH"])
    alias_to_name = load_alias_mappings(paths["MAPPING_PATH"])

    # DEBUG: print all mappings and aliases
    print("=== MAPPINGS ===")
    for m in mappings:
        print(m)
    print("=== ALIAS_TO_NAME ===")
    for alias, full_name in alias_to_name.items():
        print(f"{alias} -> {full_name}")
    print("=== END ALIAS_TO_NAME ===")

    # Makes CommunicationClient also use this mapping
    if hasattr(communication_client, "alias_to_name"):
        communication_client.alias_to_name = alias_to_name

    exit_handler = ExitHandler(
        tts,
        audio_pipeline,
        lenient_model_llm,
        strict_model_llm,
        communication_client
    )

    print("DEBUG main: len(mappings) =", len(mappings))
    print("DEBUG main: first mapping entry:", mappings[0] if mappings else None)

    # Create shared LLM and parser now that host_dict and aliases are ready
    llm = GenerateLLM(strict_model_llm, lenient_model_llm)
    parser = LLMOutputParser(
        communication_client,
        host_dict,
        llm,
        audio_pipeline,
        tts,
        exit_handler,
        mappings=mappings,
        alias_to_name=alias_to_name,
    )

    try:
        while True:
            run_voice_pipeline()
    except KeyboardInterrupt:
        print("Shutting down")
    except Exception as e:
        import traceback
        print("Unhandled exception:", e)
        traceback.print_exc()
    finally:
        exit_handler.exit_program()