import re

import torch
import torchaudio
import os
import time
from pathlib import Path

from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

GENERATOR_DIR = Path(__file__).parent.resolve()


class XTTSPolishTTS:
    """
    TTS implementation using XTTS v2.
    Configuration: FP32 (Native) + Cached Latents + No Compilation overhead.
    """

    def __init__(self, voice_path: str | Path | None = None):
        torch.serialization.add_safe_globals([
            XttsConfig, XttsArgs, XttsAudioConfig, BaseDatasetConfig
        ])

        print("Inicjalizacja XTTS v2 (Tryb Czysta Wydajność)...")

        # 1. Ładujemy model klasycznie (FP32)
        # To jest najstabilniejsza i na Twoim sprzęcie najszybsza opcja.
        self.wrapper = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        self.model = self.wrapper.synthesizer.tts_model

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Urządzenie: {device}")
        self.wrapper.to(device)  # Domyślnie float32

        # 2. Ładujemy ścieżkę głosu
        if voice_path is None:
            voice_name = "piotr.wav"
            self.voice_path_obj = GENERATOR_DIR / "voices" / voice_name
        else:
            self.voice_path_obj = Path(voice_path)

        if not self.voice_path_obj.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku głosu: {self.voice_path_obj}")

        self.voice = str(self.voice_path_obj)
        print(f"Używam pliku głosu: {self.voice}")

        # 3. OPTYMALIZACJA: Cache Latentów
        # To jedyny element, który zostawiamy. Oszczędza ok. 0.5 - 1.0s na każdym pliku
        # poprzez uniknięcie ponownego czytania i analizowania pliku WAV.
        print("Obliczanie parametrów głosu (latents)...")
        try:
            start_t = time.time()
            self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(
                audio_path=[self.voice]
            )
            print(f"Latenty gotowe w {time.time() - start_t:.2f}s")
        except Exception as e:
            print(f"BŁĄD KRYTYCZNY: {e}")
            raise e

            # 4. Wyłączamy torch.compile
        # Na Windowsie przy zmiennej długości tekstu często powoduje więcej szkody niż pożytku.
        # Wracamy do trybu "Eager" (standardowego).

    @property
    def name(self) -> str:
        return "XTTS"

    @property
    def is_online(self) -> bool:
        return False

    def tts(self, text, output_path="output_polish.wav"):
        clean_text = text.replace("...", ".").replace("…", ".")
        if not clean_text.strip():
            return output_path
        if not re.match(r".*[\.\!\?]$", clean_text):
            clean_text += '.'
        try:
            out = self.model.inference(
                text=clean_text,
                language="pl",
                gpt_cond_latent=self.gpt_cond_latent,
                speaker_embedding=self.speaker_embedding,

                # Parametry
                temperature=0.7,
                repetition_penalty=2.0,
                top_p=0.8,
                top_k=50,
                length_penalty=1.0,
                speed=1.0,
                enable_text_splitting=False
            )

            # Zapis wyniku
            wav_tensor = torch.tensor(out["wav"]).unsqueeze(0)
            torchaudio.save(output_path, wav_tensor.cpu(), 24000)

            return output_path

        except Exception as e:
            print(f"Błąd TTS: {e}")
            return output_path