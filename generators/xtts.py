import re

import torch
import torchaudio
import os
import time
from pathlib import Path

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts, XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

GENERATOR_DIR = Path(__file__).parent.resolve()
TRAINED_MODEL_PATH = (
    Path.home()
    / ".local"
    / "share"
    / "tts"
    / "tts_models--multilingual--multi-dataset--exported_xtts_finet"
)
# TRAINED_MODEL_PATH = Path.home() / ".local" / "share" / "tts" / "tts_models--multilingual--multi-dataset--xtts_v2"


class XTTSPolishTTS:
    """
    TTS implementation using XTTS v2 with locally trained model.
    Configuration: FP32 (Native) + Cached Latents + No Compilation overhead.
    """

    _shared_model = None
    _latents_cache = {}
    _MAX_CACHED_VOICES = 5  # Limit cached voice latents to prevent VRAM leak

    def __init__(self, voice_path: str | Path | None = None):
        torch.serialization.add_safe_globals(
            [XttsConfig, XttsArgs, XttsAudioConfig, BaseDatasetConfig]
        )

        # 1. Ładujemy wytrenowany model - TYLKO RAZ
        if XTTSPolishTTS._shared_model is None:
            print("Inicjalizacja XTTS v2 - Ładowanie wytrenowanego modelu...")

            # Sprawdzamy, czy katalog modelu istnieje
            if not TRAINED_MODEL_PATH.exists():
                raise FileNotFoundError(f"Model nie znaleziony w: {TRAINED_MODEL_PATH}")

            print(f"Załadowanie modelu z: {TRAINED_MODEL_PATH}")

            # Ładujemy konfigurację
            config_path = TRAINED_MODEL_PATH / "config.json"
            config = XttsConfig()
            config.load_json(str(config_path))

            # Inicjalizujemy model z konfiguracji
            self.model = Xtts.init_from_config(config)

            # Ładujemy wytrenowane wagi
            self.model.load_checkpoint(
                config=config,
                checkpoint_path=str(TRAINED_MODEL_PATH / "model.pth"),
                vocab_path=str(TRAINED_MODEL_PATH / "vocab.json"),
                speaker_file_path=str(TRAINED_MODEL_PATH / "speakers_xtts.pth"),
                eval=True,
                strict=False,
            )

            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Urządzenie: {device}")
            self.model.to(device)  # Domyślnie float32

            XTTSPolishTTS._shared_model = self.model
        else:
            print("XTTS v2: Używam załadowanego modelu z cache.")
            self.model = XTTSPolishTTS._shared_model  # type: ignore

        # 2. Ładujemy ścieżkę głosu
        if voice_path is None:
            voice_name = "michal.wav"
            self.voice_path_obj = GENERATOR_DIR / "voices" / voice_name
        else:
            self.voice_path_obj = Path(voice_path)

        if not self.voice_path_obj.exists():
            raise FileNotFoundError(
                f"Nie znaleziono pliku głosu: {self.voice_path_obj}"
            )

        self.voice = str(self.voice_path_obj)
        print(f"Używam pliku głosu: {self.voice}")

        # 3. OPTYMALIZACJA: Cache Latentów
        # Sprawdzamy, czy mamy już policzone parametry dla tego pliku
        voice_key = str(self.voice_path_obj.resolve())

        if voice_key in XTTSPolishTTS._latents_cache:
            print(
                f"XTTS v2: Używam zagregowanych parametrów głosu z cache dla: {self.voice_path_obj.name}"
            )
            self.gpt_cond_latent, self.speaker_embedding = XTTSPolishTTS._latents_cache[
                voice_key
            ]
        else:
            # To jedyny element, który zostawiamy. Oszczędza ok. 0.5 - 1.0s na każdym pliku
            # poprzez uniknięcie ponownego czytania i analizowania pliku WAV.
            print(
                f"Obliczanie parametrów głosu (latents) dla {self.voice_path_obj.name}..."
            )
            try:
                start_t = time.time()
                self.gpt_cond_latent, self.speaker_embedding = (
                    self.model.get_conditioning_latents(  # type: ignore
                        audio_path=[self.voice]
                    )
                )

                # Zapisujemy do cache
                XTTSPolishTTS._latents_cache[voice_key] = (
                    self.gpt_cond_latent,
                    self.speaker_embedding,
                )
                print(
                    f"Latenty gotowe w {time.time() - start_t:.2f}s i zapisane w cache."
                )
            except Exception as e:
                print(f"BŁĄD KRYTYCZNY: {e}")
                raise e

    @property
    def name(self) -> str:
        return "XTTS"

    @property
    def is_online(self) -> bool:
        return False

    def tts(self, text, output_path="output_polish.wav"):
        import gc

        clean_text = text.replace("...", ".").replace("…", ".")
        clean_text = clean_text.strip(".")
        if not clean_text.strip():
            return output_path
        if not re.match(r".*[\.\!\?]$", clean_text):
            clean_text += "."
        clean_text += " "
        wav_tensor = None
        out = None
        try:
            out = self.model.inference(  # type: ignore
                text=clean_text,  # type: ignore
                language="pl",  # type: ignore
                gpt_cond_latent=self.gpt_cond_latent,  # type: ignore
                speaker_embedding=self.speaker_embedding,  # type: ignore
                temperature=0.25,  # type: ignore
                repetition_penalty=6.0,  # type: ignore
                top_p=0.5,  # type: ignore
                top_k=50,  # type: ignore
                length_penalty=1.0,  # type: ignore
                speed=1.0,  # type: ignore
                enable_text_splitting=False,  # type: ignore
            )
            wav_tensor = torch.tensor(out["wav"]).unsqueeze(0)
            torchaudio.save(output_path, wav_tensor.cpu(), 22050)
            return output_path
        except Exception as e:
            print(f"Błąd TTS: {e}")
            return output_path
        finally:
            # Jawne czyszczenie pamięci po generacji
            if wav_tensor is not None:
                del wav_tensor
            if out is not None:
                del out
            gc.collect()
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    @classmethod
    def clear_latents_cache(cls) -> int:
        """
        Czyści cache zagtępnych latensów głosu.
        Zwraca liczbę usuniętych wpisów.
        """
        cleared = len(cls._latents_cache)
        for key in list(cls._latents_cache.keys()):
            latent, embedding = cls._latents_cache[key]
            del latent
            del embedding
        cls._latents_cache.clear()
        import gc

        gc.collect()
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        print(f"[XTTS] Cache latensów wyczyszczony. Usunięto {cleared} wpisów.")
        return cleared
