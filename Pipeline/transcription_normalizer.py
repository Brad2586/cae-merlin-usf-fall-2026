import re

class TranscriptNormalizer:
    def __init__(self, variations_dict):
        self.lookup = {}
        
        for canonical, variants in variations_dict["variations"].items():
            for v in variants:
                self.lookup[v.lower()] = canonical.lower()

        # Sort by length (longer phrases first to avoid partial overwrite issues)
        self.sorted_variants = sorted(self.lookup.keys(), key=len, reverse=True)

    def normalize(self, text: str) -> str:
        text = text.lower()

        for variant in self.sorted_variants:
            canonical = self.lookup[variant]

            # replace whole words / phrases only
            pattern = r'\b' + re.escape(variant) + r'\b'
            text = re.sub(pattern, canonical, text)

        return text