from app.utils import is_installed

if is_installed('torch'):
    import torch
else:
    torch = None  # Zapewnij placeholder

import os
from pathlib import Path

if is_installed('TTS'):
    from TTS.api import TTS
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
    from TTS.config.shared_configs import BaseDatasetConfig
else:
    TTS = None
    XttsConfig = None
    XttsAudioConfig = None
    XttsArgs = None
    BaseDatasetConfig = None


# Ścieżka do katalogu, w którym znajduje się ten plik (xtts.py)
GENERATOR_DIR = Path(__file__).parent.resolve()


class XTTSPolishTTS:
    """
    TTS implementation using the local Coqui XTTS v2 model.
    """

    def __init__(self, voice_path: str | Path | None = None):
        """
        Initializes and loads the XTTS model into VRAM.

        Args:
            voice_path: Path to the .wav file to be used for voice cloning.
        """
        if not is_installed('torch') or TTS is None:
            raise ImportError("Pakiety 'torch' lub 'TTS' nie są zainstalowane. XTTS jest niedostępny.")

        torch.serialization.add_safe_globals([
            XttsConfig,
            XttsArgs,
            XttsAudioConfig,
            BaseDatasetConfig])

        self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
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
        print(f"Using voice file: {self.voice}")

    @property
    def name(self) -> str:
        return "XTTS"

    @property
    def is_online(self) -> bool:
        return False

    def tts(self, text, output_path="output_polish.wav"):
        """
        Generates speech and saves it as a .wav file.

        Args:
            text: The text to synthesize.
            output_path: The path to save the output .wav file.

        Returns:
            The output_path.
        """
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