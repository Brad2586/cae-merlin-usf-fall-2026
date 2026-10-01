"""Console adapters used by Merlin's dependency-light text test mode."""


class TextInputPipeline:
    """Provide the AudioPipeline interface using console input."""

    def listen_and_transcribe(self) -> str:
        while True:
            text = input("\nMerlin command (Ctrl+C to stop): ").strip()
            if text:
                return text

    def close(self) -> None:
        pass


class ConsoleTTS:
    """Provide the PiperTTS interface without loading an audio model."""

    def say(self, message, priority="normal", **_kwargs) -> None:
        print(f"[TTS:{priority}] {message}")

    def close(self) -> None:
        pass

