from generators.stylish_model.app import synthesize_text
from gradio import processing_utils

class TTS:
    def tts(self, text, output_path):
        [hr, audio] = synthesize_text(text, speed=1)
        processing_utils.audio_to_file(hr, audio, output_path)
        return output_path