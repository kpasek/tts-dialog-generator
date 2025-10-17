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
        voice_name = "daniel.wav"
        voice_path = os.path.join("generators", "voices", voice_name)
        voice = os.path.abspath(voice_path)
        if os.name == "nt":
            voice = f"generators\\voices\\{voice_name}"
        split = False
        if len(text) >= 224:
            split = True

        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            language="pl",
            speaker_wav=voice,
            split_sentences=split
        )
        return output_path
