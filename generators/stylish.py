from generators.stylish_model.app import synthesize_text
from generators.tts_base import TTSBase
from gradio import processing_utils


class StylishTTS(TTSBase):
    def tts(self, text: str, output_path: str) -> str:
        [hr, audio] = synthesize_text(text, speed=1)
        processing_utils.audio_to_file(hr, audio, output_path)
        return output_path
    
    @property
    def name(self) -> str:
        return "STylish"

    @property
    def is_online(self) -> bool:
        return False

