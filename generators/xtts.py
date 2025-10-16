import torch
import os
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig


class XTTSPolishTTS:
    def __init__(self):
        torch.serialization.add_safe_globals([
            XttsConfig,
            XttsArgs,
            XttsAudioConfig,
            BaseDatasetConfig])
        
        self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        # self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v1.1")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        self.model.to(device)

    def tts(self, text, output_path="output_polish.wav"):
        voice = os.path.abspath(os.path.join("voices", "daniel.wav"))
        voice = "generators\\voices\\daniel.wav"
        import soundfile as sf
        sf.read(voice)

        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            language="pl",
            speaker_wav=voice,
            split_sentences=False
        )
        return output_path
