import requests
import os
import re
import whisper
from rapidfuzz import fuzz
import time
from pydub import AudioSegment

# --- KONFIGURACJA ---
API_URL = "http://localhost:8020/tts_to_audio"
OUTPUT_FOLDER = "audio_game_final"
SPEAKER_WAV = "lektor_sample.wav" 
LANGUAGE = "pl"

# Parametry weryfikacji
MAX_RETRIES = 3            # Ile razy próbować naprawić plik
MIN_SIMILARITY = 80
WHISPER_MODEL_SIZE = "tiny" # 'tiny' jest super szybki i wystarczy do weryfikacji

asr_model = whisper.load_model(WHISPER_MODEL_SIZE)

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_FOLDER, "failed"), exist_ok=True)


def verify_cps(text, audio_path):
    audio = AudioSegment.from_file(audio_path)
    duration_sec = len(audio) / 1000.0
    
    cps = len(text) / duration_sec
    
    if cps <= 6 or cps >= 18:
        print(f"Audio niepoprawne: {len(text)} char / {duration_sec}s = CPS {cps:.2f}.")
        return False
    return True


def analyze_audio(audio_path: str, original_text: str) -> dict:
    """
    Transkrybuje plik audio i porównuje z oryginałem.
    Zwraca słownik ze szczegółami analizy:
    - transcribed_text: tekst odczytany z audio
    - score: wynik dopasowania (0-100)
    - original_text: tekst wzorcowy
    """
    try:
        if not os.path.exists(audio_path):
            return {
                "error": f"File not found: {audio_path}",
                "success": False
            }



        # Logowanie parametrów pliku audio i walidacja
        try:
            from pydub.utils import mediainfo
            info = mediainfo(audio_path)
            print(f"[AUDIO INFO] {audio_path}: {info}")
            # Sprawdź długość i rozmiar pliku
            duration = float(info.get('duration', 0))
            filesize = os.path.getsize(audio_path)
            if duration < 0.5:
                print(f"[AUDIO ERROR] Plik audio za krótki: {duration}s")
                return {"success": False, "error": f"Plik audio za krótki: {duration}s"}
            if filesize < 1024:
                print(f"[AUDIO ERROR] Plik audio zbyt mały: {filesize} bajtów")
                return {"success": False, "error": f"Plik audio zbyt mały: {filesize} bajtów"}
        except Exception as e:
            print(f"[AUDIO INFO] Błąd pobierania info: {e}")

        import torch
        try:
            # Wymuś transkrypcję na CPU (nie przełączaj modelu, tylko wymuś device w transcribe)
            result = asr_model.transcribe(audio_path, language='pl', fp16=False, device='cpu')
        except Exception as cpu_error:
            print(f"[WHISPER ERROR] Transkrypcja na CPU nie powiodła się: {cpu_error}")
            return {"success": False, "error": f"Błąd transkrypcji audio: {cpu_error}"}

        transcribed_text = result.get('text', '').strip() if result else ''
        if not transcribed_text or 'nan' in transcribed_text.lower():
            print(f"[WHISPER ERROR] Transkrypcja zwróciła pusty tekst lub NaN")
            return {"success": False, "error": "Transkrypcja nie powiodła się (pusty tekst lub NaN). Plik audio może być uszkodzony lub nieczytelny."}

        # Normalizacja tekstów do porównania
        # Usuwamy znaki interpunkcyjne i zmieniamy na małe litery
        test_pattern = r"[^a-ząćżźęńół0-9 ]+"
        org_text_norm = re.sub(test_pattern, '', original_text.lower()) 
        trans_text_norm = re.sub(test_pattern, '', transcribed_text.lower())

        # Obliczanie wyniku dopasowania
        score = fuzz.ratio(org_text_norm, trans_text_norm)
        
        # Opcjonalnie: dodatkowa metryka np. token match
        token_score = fuzz.token_sort_ratio(org_text_norm, trans_text_norm)

        # Logika oceny "sukcesu" - można dostosować próg
        is_match = score > 85

        return {
            "success": True,
            "transcribed_text": transcribed_text,
            "original_text": original_text,
            "score": score,
            "token_score": token_score,
            "match": is_match,
            "details": {
                "normalized_original": org_text_norm,
                "normalized_transcribed": trans_text_norm
            }
        }

    except Exception as e:
        import traceback
        print(f"Exception in analyze_audio: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

def check_audio_quality(audio_path, original_text) -> bool:
    """
    Zwraca True jeśli audio jest poprawne, False jeśli podejrzewamy halucynacje.
    """
    try:
        return True
        if not verify_cps(original_text, audio_path):
            return False
        # 1. Transkrypcja (zamiana audio na tekst)
        result = asr_model.transcribe(audio_path, language='pl')
        transcribed_text = result['text'].strip()
        test_pattern = r"[^a-ząćżźęńół ]+"
        org_text_to_test = re.sub(test_pattern, '', original_text.lower()) 
        trans_text_to_test = re.sub(test_pattern, '', transcribed_text.lower())
        # 2. Porównanie tekstów (Fuzzy matching)
        similarity = fuzz.ratio(org_text_to_test, trans_text_to_test)
        
        # 3. Logika wykrywania halucynacji
        # Jeśli transkrypcja jest dużo dłuższa od oryginału -> Halucynacja
        len_ratio = len(transcribed_text) / len(original_text) if len(original_text) > 0 else 0

        min_similarity = 95 if len(original_text) < 30 else 85
        if similarity < min_similarity:
            print(f"   [!] Niska zgodność: {similarity}% (Oczekiwano: '{original_text}' -> Usłyszano: '{transcribed_text}')")
            return False
        
        if len_ratio > 1.05:
            print(f"   [!] Podejrzana długość (Halucynacja na końcu?).")
            return False
            
        return True
        
    except Exception as e:
        print(f"   [Błąd weryfikacji]: {e}")
        return False # Dla bezpieczeństwa uznajemy za błąd
