
from config.config import get_mode
from logger import log
import time
class GenerateLLM:
    def __init__(self, strict_model_llm, lenient_model_llm, model_loader=None):
        self.strict_model_llm = strict_model_llm
        self.lenient_model_llm = lenient_model_llm
        self.model_loader = model_loader

    def _get_active_model(self, mode=None):
        if mode is None:
            mode = get_mode()  # use current global mode
        if mode == "strict":
            if self.strict_model_llm is None and self.model_loader is not None:
                log("[LLM]", "Loading strict model on first use")
                self.strict_model_llm = self.model_loader("strict")
            return self.strict_model_llm
        if self.lenient_model_llm is None and self.model_loader is not None:
            log("[LLM]", "Loading lenient model on first use")
            self.lenient_model_llm = self.model_loader("lenient")
        return self.lenient_model_llm

    def generate_from_llm(self, prompt, max_new_tokens=150, mode=None):
        model = self._get_active_model(mode)
        start_time = time.time()
        result = model(prompt, max_tokens=max_new_tokens, temperature=0.0, echo=False)
        elapsed = time.time() - start_time

        if 'choices' in result and len(result['choices']) > 0:
            text = result['choices'][0].get('text', '')
        else:
            text = str(result)
        usage = result.get('usage', {})
        log(f"[LLM_OUTPUT] ({get_mode()})", f"text={text} | usage={usage}", elapsed)

        return text

    def close(self):
        """Release every model that was loaded during this session."""
        closed_ids = set()
        for model in (self.strict_model_llm, self.lenient_model_llm):
            if model is not None and id(model) not in closed_ids:
                closed_ids.add(id(model))
                close = getattr(model, "close", None)
                if close:
                    close()