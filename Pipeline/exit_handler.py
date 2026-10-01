from logger import log
class ExitHandler:
    def __init__(self, tts, audio_pipeline, model_llm, lenient_model_llm, communication_client):
        self.tts = tts
        self.audio_pipeline = audio_pipeline
        self.model_llm = model_llm
        self.communication_client = communication_client
        self.exit_requested = False
    
    def exit_program(self):
        try:
            self.audio_pipeline.close()
            log("[EXIT_HANDLER]", "Audio pipeline closed successfully.")
            print("Audio pipeline closed successfully.")
        except Exception:
            pass
        try:
            self.model_llm.close()
            log("[EXIT_HANDLER]", "LLM model closed successfully.")
            print("LLM model closed successfully.")
        except Exception:
            pass
        try:
            self.communication_client.exit()
            log("[EXIT_HANDLER]", "Communication client exited successfully.")
            print("Communication client exited successfully.")
        except Exception:
            pass
        try:
            self.tts.close()
            log("[EXIT_HANDLER]", "TTS engine closed successfully.")
            print("TTS engine closed successfully.")
        except Exception:
            pass

        import os
        os._exit(0)