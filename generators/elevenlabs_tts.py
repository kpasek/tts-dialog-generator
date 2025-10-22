from typing import Optional, List
from .tts_base import TTSBase
from app.utils import is_installed


from elevenlabs.client import ElevenLabs


if is_installed('elevenlabs'):
    from elevenlabs import Voice
else:
    # Zapewnij typy zastępcze, jeśli pakiet nie jest zainstalowany
    Voice = None
    generate = None
    set_api_key = None
    voices = None


class ElevenLabsTTS(TTSBase):
    """
    TTS implementation using the ElevenLabs API.
    """

    def __init__(self, api_key: str, voice_id: Optional[str] = None):
        """
        Initializes the ElevenLabs client.

        Args:
            api_key: The ElevenLabs API key.
            voice_id: The ID of the voice to use.
        """

        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)

        self.voice_id = voice_id
        self._voices = None

    @property
    def name(self) -> str:
        return "ElevenLabs"

    @property
    def is_online(self) -> bool:
        return True

    @property
    def settings(self) -> dict:
        return {
            "api_key": self.api_key,
            "voice_id": self.voice_id
        }

    @property
    def available_voices(self) -> List[Voice]:
        """Lazily fetches the list of available voices from the API."""
        if self._voices is None:
            response = self.client.voices.search()
            self._voices = response.voices
        return self._voices

    def tts(self, text: str, output_path: str) -> str:
        """
        Generates speech and saves it as a .wav file. (ElevenLabs domyślnie generuje mp3,
        ale nasz konwerter i tak to obsłuży, jeśli zapiszemy z rozszerzeniem .wav,
        choć idealnie byłoby zapisać jako mp3 i zmienić logikę w browser.py.
        Dla spójności z XTTS, zapisujemy jako .wav, co jest mylące, ale pydub to obsłuży)

        Poprawka: `generate` zwraca bytes (audio), które zapisujemy.
        `output_path` jest oczekiwane jako .wav, więc to zrobimy.
        AudioConverter i Pygame/Pydub poradzą sobie z formatem wewnątrz.

        Args:
            text: The text to synthesize.
            output_path: The path to save the output audio file.

        Returns:
            The output_path.
        """
        if not self.voice_id:
            raise ValueError("Voice ID not set for ElevenLabs")

        audio = self.client.text_to_speech.convert(
            text=text,
            voice_id=self.voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        with open(output_path, 'wb') as f:
            f.write(audio)

        return output_path