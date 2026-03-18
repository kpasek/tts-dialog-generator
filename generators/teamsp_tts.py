import requests
from typing import Optional
from .tts_base import TTSBase

class TeamSPTTS(TTSBase):
    """
    TTS implementation using the TeamSP API.
    """

    def __init__(self, voice: str = "o2xdfKUpc1Bwq7RchZuW", key: str = "wqpwgoGhADAwIdb1JRNTAEBgg="):
        """
        Initializes the TeamSP TTS generator.

        Args:
            voice: The ID of the voice to use.
            key: API key or authorization token.
        """
        self.voice = voice
        self.key = key
        self.url = "https://teamsp.org/xi/run6.php"

    @property
    def name(self) -> str:
        return "teamsp_tts"

    @property
    def is_online(self) -> bool:
        return True

    @property
    def settings(self) -> dict:
        return {
            "voice": self.voice,
            "key": self.key
        }

    def tts(self, text: str, output_path: str) -> str:
        """
        Generates speech and saves it as an audio file.

        Args:
            text: The text to synthesize.
            output_path: The path to save the output audio file.

        Returns:
            The output_path.
        """
        headers = {
            'accept': '*/*',
            'accept-language': 'pl-PL,pl;q=0.6',
            'origin': 'https://teamsp.org',
            'priority': 'u=1, i',
            'referer': 'https://teamsp.org/xi/line6.html',
        }

        # The request in the curl example was multipart/form-data
        files = {
            'text': (None, text),
            'voice': (None, self.voice),
            'key': (None, self.key),
        }

        response = requests.post(self.url, headers=headers, files=files)
        response.raise_for_status()

        # It's returning an mp3 file based on the curl output test.mp3
        # I'll save to output_path. If output_path is .wav, it might be expected
        # that downstream parts convert it, or I can just write the bytes to output_path.
        
        # Save the audio data
        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path
