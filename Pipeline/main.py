import json
import os
import sys
import warnings
import time 
import threading

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tts import PiperTTS
from audio_pipeline import AudioPipeline
from openwakeword.model import Model
from llama_cpp import Llama
from parse_llm_output import LLMOutputParser
from communication_client import CommunicationClient
from command_registry import CommandRegistry
from generate_llm import GenerateLLM
from exit_handler import ExitHandler
from transcription_normalizer import TranscriptNormalizer
from logger import log
from runtime_status import runtime_status

from config.load_paths import load_paths
from config.config import get_audio_settings, get_communication_settings, get_mode


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
        runtime_status.update(merlin_state="listening", message="Waiting for wake word")
        text = audio_pipeline.listen_and_transcribe()
        runtime_status.update(
            merlin_state="processing",
            last_transcription=text,
            message="Processing voice command" if text else "No command detected",
        )
        print("\nTranscription:")
        print(text)

        if not text:
            continue

        generated_command = command_registry.match(text)
        if generated_command is not None:
            llm_output = json.dumps(generated_command)
            runtime_status.record_command(
                text,
                generated_command.get("command_name", "Fast command match"),
            )
            print("Matched generated voice command.")
        else:
            prompt = f"input: {text}\noutput:"
            llm_output = llm.generate_from_llm(prompt, 150)
            runtime_status.record_command(text, "language model")

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


voice_model_path = paths["TTS_VOICE_PATH"]
tts = PiperTTS(voice_model_path)

running = True

if __name__ == "__main__":

    runtime_status.reset_session(
        active_model=get_mode(),
        server_endpoint="127.0.0.1:10013",
        message="Starting Merlin",
    )
    runtime_status.start_heartbeat()
    communication_client = CommunicationClient(
        '127.0.0.1',
        10013,
        tts,
        status_store=runtime_status,
        **get_communication_settings(),
    )
    if not communication_client.connect():
        print("Could not connect to server or initialization handshake failed")
        os._exit(1)

    oww = Model(
        wakeword_models=paths["MODEL_PATHS"],
        inference_framework="tflite"
    )
    with open(paths["VARIATIONS_PATH"], "r") as f:
        variations_data = json.load(f)

    normalizer = TranscriptNormalizer(variations_data)
    command_registry = CommandRegistry(
        paths["VOICE_COMMANDS_PATH"],
        mapping_path=paths["MAPPING_PATH"],
    )

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"

    audio_pipeline = AudioPipeline(
        wakeword_model=oww,
        thresholds=THRESHOLDS,
        debounce_time=DEBOUNCE_TIME,
        whisper_processor=None,
        whisper_model=None,
        device=device,
        whisper_name="small.en",
        compute_type="float16" if device == "cuda" else "int8",
        normalizer=normalizer,
        **get_audio_settings(),
    )

    def load_llama_model(mode):
        model_path = (
            paths["GGUF_MODEL_PATH_STRICT"]
            if mode == "strict"
            else paths["GGUF_MODEL_PATH_LENIENT"]
        )
        return Llama(
            model_path=model_path,
            n_ctx=512,
            n_threads=10,
            seed=42,
            n_gpu_layers=-1,
            n_batch=256,
            n_ubatch=256,
            low_vram=False,
            cache=True,
            use_mmap=True,
            use_mlock=True,
            verbose=False,
        )

    # Load only the selected default model. The other model is loaded on demand
    # if the user changes modes, reducing startup time and GPU/RAM usage.
    lenient_model_llm = (
        load_llama_model("lenient") if get_mode() == "lenient" else None
    )
    strict_model_llm = (
        load_llama_model("strict") if get_mode() == "strict" else None
    )
    llm = GenerateLLM(
        strict_model_llm,
        lenient_model_llm,
        model_loader=load_llama_model,
    )
    
    variables_to_track = load_variables(paths["XML_PATH"])

    # Build host dictionary using spec-compliant Add Update Page / Request Update flow.
    host_dict = communication_client.create_update_page(variables_to_track)

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

    # Makes CommunicationClient also use this mapping
    if hasattr(communication_client, "alias_to_name"):
        communication_client.alias_to_name = alias_to_name

    exit_handler = ExitHandler(
        tts,
        audio_pipeline,
        llm,
        communication_client
    )

    # Create shared LLM and parser now that host_dict and aliases are ready
    parser = LLMOutputParser(
        communication_client,
        host_dict,
        llm,
        audio_pipeline,
        tts,
        exit_handler,
        mappings=mappings,
        alias_to_name=alias_to_name,
        status_store=runtime_status,
    )

    runtime_status.update(
        merlin_state="ready",
        server_state="connected",
        active_model=get_mode(),
        message="Merlin is ready",
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
        runtime_status.update(merlin_state="stopping", message="Shutting down")
        runtime_status.stop_heartbeat()
        exit_handler.exit_program()