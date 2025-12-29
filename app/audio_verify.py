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

    """
    Sprawdza, czy wygenerowane audio pasuje do tekstu.
    Zwraca True, jeśli jest OK, False, jeśli wykryto bełkot.
    """
    try:
        result = validator_model.transcribe(audio_path)
        transcribed_text = result["text"].strip() # type: ignore
        
        # 1. Sprawdzenie długości tekstu (bełkot często generuje dużo nadmiarowego tekstu)
        if len(transcribed_text) > (len(original_text) * 1.2):
            print(f"Błąd: Wygenerowany tekst jest za długi: {transcribed_text}")
            return False

        # 2. Sprawdzenie podobieństwa (opcjonalne, dla precyzji)
        similarity = SequenceMatcher(None, original_text.lower(), transcribed_text.lower()).ratio()
        
        # Jeśli podobieństwo jest poniżej np. 70%, uznajemy to za błąd
        # (Wartość 0.7 trzeba dobrać eksperymentalnie)
        if similarity < 0.7:
            print(f"Błąd: Tekst mało podobny. Oczekiwano: '{original_text}', Otrzymano: '{transcribed_text}'")
            return False
    except Exception as e:
        print(f"Błąd walidacji: {e}")
        return True


def check_audio_quality(audio_path, original_text) -> bool:
    """
    Zwraca True jeśli audio jest poprawne, False jeśli podejrzewamy halucynacje.
    """
    try:
        if not verify_cps(original_text, audio_path):
            return False
        # 1. Transkrypcja (zamiana audio na tekst)
        result = asr_model.transcribe(audio_path, language='pl')
        transcribed_text = result['text'].strip()
        test_pattern = r"[^a-ząćżźęńół ]+"
        org_text_to_test = re.sub(test_pattern, '', original_text.lower()) 
        trans_text_to_test = re.sub(test_pattern, '', transcribed_text.lower())
        # 2. Porównanie tekstów (Fuzzy matching)
        similarity = fuzz.ratio(org_text_to_test[-10:], trans_text_to_test[-10:])
        
        # 3. Logika wykrywania halucynacji
        # Jeśli transkrypcja jest dużo dłuższa od oryginału -> Halucynacja
        len_ratio = len(transcribed_text) / len(original_text) if len(original_text) > 0 else 0
        
        if similarity < MIN_SIMILARITY:
            print(f"   [!] Niska zgodność: {similarity}% (Oczekiwano: '{original_text}' -> Usłyszano: '{transcribed_text}')")
            return False
        
        if len_ratio > 1.05:
            print(f"   [!] Podejrzana długość (Halucynacja na końcu?).")
            return False
            
        return True
        
    except Exception as e:
        print(f"   [Błąd weryfikacji]: {e}")
        return False # Dla bezpieczeństwa uznajemy za błąd
