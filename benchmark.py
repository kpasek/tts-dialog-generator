import time
import os
import shutil
from pathlib import Path

# Dodajemy katalog bieżący do ścieżki, żeby importy działały
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generators.xtts import XTTSPolishTTS

# Konfiguracja testu
OUTPUT_DIR = Path("bench_output")
if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir()

TEST_SENTENCES = [
    ("Krótkie", "To jest krótki test."),
    ("Średnie",
     "To jest nieco dłuższe zdanie, które ma na celu sprawdzenie jak model radzi sobie ze średnią ilością tekstu."),
    ("Długie",
     "Wczoraj, spacerując po lesie, zauważyłem dziwne ślady, które prowadziły w głąb gęstwiny, ale postanowiłem zawrócić, bo robiło się już ciemno i zaczął padać ulewny deszcz, który przemoczył mnie do suchej nitki.")
]


def run_benchmark():
    print("=" * 50)
    print("ROZPOCZYNAM BENCHMARK XTTS v2")
    print("=" * 50)

    # 1. Pomiar inicjalizacji
    print("1. Inicjalizacja modelu...")
    start_init = time.time()

    # Tu następuje ładowanie modelu i (w nowej wersji) pre-komputacja latentów
    tts_engine = XTTSPolishTTS(voice_path=None)

    end_init = time.time()
    print(f"-> Czas inicjalizacji: {end_init - start_init:.4f} s")
    print("-" * 50)

    # 2. Rozgrzewka (Warm-up)
    # Pierwsze zapytanie do GPU/CUDA jest zawsze wolniejsze przez ładowanie kerneli.
    # Nie wliczamy go do statystyk, żeby wynik był rzetelny dla procesu ciągłego (batch).
    print("2. Rozgrzewka GPU (pomijana w wynikach)...")
    tts_engine.tts("Rozgrzewka silnika.", str(OUTPUT_DIR / "warmup.wav"))
    print("-> Rozgrzewka zakończona.")
    print("-" * 50)

    # 3. Test właściwy
    print("3. Generowanie dialogów...")

    total_duration = 0
    total_chars = 0

    for i in range(10):
        for name, text in TEST_SENTENCES:
            output_file = OUTPUT_DIR / f"{name}.wav"
            print(f"   Generowanie: [{name}] ({len(text)} znaków)...")

            start_gen = time.time()
            tts_engine.tts(text, str(output_file))
            end_gen = time.time()

            duration = end_gen - start_gen
            total_duration += duration
            total_chars += len(text)

            print(f"   -> Czas: {duration:.4f} s | Prędkość: {len(text) / duration:.1f} znaków/s")

    print("=" * 50)
    print("PODSUMOWANIE:")
    print(f"Całkowity czas generowania (bez init): {total_duration:.4f} s")
    print(f"Średnia prędkość: {total_chars / total_duration:.2f} znaków/sekundę")
    print("=" * 50)


if __name__ == "__main__":
    run_benchmark()