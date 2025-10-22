from typing import Optional
from .tts_base import TTSBase
import google.cloud.texttospeech as tts


class GeminiTTS(TTSBase):
    def __init__(self, credentials_path: str, voice_name: Optional[str] = None, language_code: str = "pl-PL"):
        self.credentials_path = credentials_path
        self.voice_name = voice_name
        self.language_code = language_code
        self.client = tts.TextToSpeechClient.from_service_account_file(
            credentials_path)

    @property
    def name(self) -> str:
        return "Google Cloud TTS"

    @property
    def is_online(self) -> bool:
        return True

    @property
    def settings(self) -> dict:
        return {
            "credentials_path": self.credentials_path,
            "voice_name": self.voice_name,
            "language_code": self.language_code
        }

    def get_available_voices(self):
        response = self.client.list_voices(language_code=self.language_code)
        return response.voices

    def tts(self, text: str, output_path: str) -> str:
        synthesis_input = tts.SynthesisInput(text=text)

        voice = tts.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice_name
        )

        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16,
            speaking_rate=1.0
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        return output_path
