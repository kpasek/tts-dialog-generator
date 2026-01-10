import os
import wave
import logging

from piper import SynthesisConfig

# Próba importu biblioteki piper.
# Użytkownik musi zainstalować: pip install piper-tts
try:
    from piper.voice import PiperVoice
except ImportError:
    PiperVoice = None

# Import klasy bazowej (dostosuj, jeśli TTSBase jest w innym miejscu lub plik jest pusty)
try:
    from .tts_base import TTSBase
except ImportError:
    # Fallback jeśli tts_base jest pusty/niedostępny
    class TTSBase:
        pass


class PiperTTS(TTSBase):
    def __init__(self, model_path: str, config_path: str = None, use_cuda: bool = True):
        """
        Inicjalizacja silnika Piper TTS.
        Model jest ładowany do pamięci przy starcie.
        """
        if PiperVoice is None:
            raise ImportError(
                "Biblioteka 'piper-tts' nie jest zainstalowana. Zainstaluj ją komendą: pip install piper-tts")
        print(model_path)
        self.model_path = model_path
        # Jeśli config_path nie jest podany, zakładamy, że to plik .onnx.json obok modelu
        self.config_path = config_path if config_path else f"{model_path}.json"

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Nie znaleziono modelu Piper: {self.model_path}")
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Nie znaleziono pliku konfiguracyjnego Piper: {self.config_path}")

        logging.info(f"Ładowanie modelu Piper z: {self.model_path}")
        self.voice = PiperVoice.load(self.model_path, use_cuda=use_cuda)
        logging.info("Model Piper załadowany pomyślnie.")

    def tts(self, text: str, output_path: str) -> str:
        """
        Generuje audio z tekstu i zapisuje do pliku output_path (format WAV).
        """
        # Upewnij się, że katalog wyjściowy istnieje
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        syn_config = SynthesisConfig(
            volume=1,
            length_scale=1.0,
            normalize_audio=False,
        )
        try:

            # Piper generuje audio bezpośrednio do obiektu wave
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                rate = self.voice.config.sample_rate
                wav_file.setframerate(rate)

                # Teraz możemy bezpiecznie generować audio
                self.voice.synthesize_wav(text, wav_file)
        except Exception as e:
            print(f"Piper generate error: {e}")
            raise e
        return output_path

    @property
    def name(self) -> str:
        return "Piper"

    @property
    def is_online(self) -> bool:
        return False