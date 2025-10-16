
from cleaners.cleaner import Cleaner
import re

class ACOCleaner(Cleaner):

    def __init__(self, input_file: str, output_file: str | None):
        super().__init__(input_file, output_file)
        self.patterns = [
            (r"Aleksios", "Aleksjos"),
        ]

    def tts_line(self, text):
        text = super().clean_line(text)

        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)
        return text.strip()
