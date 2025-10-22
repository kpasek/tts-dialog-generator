from abc import ABC, abstractmethod
from typing import Optional


class TTSBase(ABC):
    """Bazowa klasa dla wszystkich modeli TTS"""

    @abstractmethod
    def tts(self, text: str, output_path: str) -> str:
        """
        Generuje mowę z tekstu i zapisuje do pliku.

        Args:
            text: Tekst do wygenerowania
            output_path: Ścieżka do pliku wyjściowego

        Returns:
            str: Ścieżka do wygenerowanego pliku
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nazwa modelu TTS"""
        pass

    @property
    @abstractmethod
    def is_online(self) -> bool:
        """Czy model wymaga połączenia z internetem"""
        pass

    @property
    def settings(self) -> dict:
        """Ustawienia specyficzne dla modelu"""
        return {}
