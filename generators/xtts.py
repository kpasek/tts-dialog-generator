import torch
import os
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig
from pathlib import Path

# Ścieżka do katalogu, w którym znajduje się ten plik (xtts.py)
GENERATOR_DIR = Path(__file__).parent.resolve()


class XTTSPolishTTS:
    def __init__(self, voice_path: str | Path | None = None):
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

        if voice_path is None:
            # Domyślna ścieżka, jeśli nic nie podano
            voice_name = "michal.wav"
            self.voice_path_obj = GENERATOR_DIR / "voices" / voice_name
            print(f"Używam domyślnej ścieżki głosu: {self.voice_path_obj}")
        else:
            # Ścieżka z ustawień
            self.voice_path_obj = Path(voice_path)
            print(f"Używam głosu z ustawień: {self.voice_path_obj}")

        if not self.voice_path_obj.exists():
            print(f"BŁĄD KRYTYCZNY: Nie znaleziono pliku głosu: {self.voice_path_obj}")
            print("Upewnij się, że plik istnieje lub skonfiguruj go w Ustawieniach.")
            raise FileNotFoundError(f"Nie znaleziono pliku głosu: {self.voice_path_obj}")

        self.voice = str(self.voice_path_obj)
        # =====================================

        print(f"Using voice file: {self.voice}")

    def tts(self, text, output_path="output_polish.wav"):

        split = False
        if len(text) >= 200:
            split = True

        self.model.tts_to_file(
            text=text,
            file_path=output_path,
            language="pl",
            speaker_wav=self.voice,
            split_sentences=split
        )
        return output_path