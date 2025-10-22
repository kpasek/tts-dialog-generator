from typing import Optional
from .tts_base import TTSBase
from elevenlabs import generate, set_api_key, voices, Voice


class ElevenLabsTTS(TTSBase):
    def __init__(self, api_key: str, voice_id: Optional[str] = None):
        self.api_key = api_key
        set_api_key(api_key)
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
    def available_voices(self) -> list[Voice]:
        if self._voices is None:
            self._voices = voices()
        return self._voices

    def tts(self, text: str, output_path: str) -> str:
        if not self.voice_id:
            raise ValueError("Voice ID not set")

        audio = generate(
            text=text,
            voice=self.voice_id,
            model="eleven_multilingual_v2"
        )

        with open(output_path, 'wb') as f:
            f.write(audio)

        return output_path
