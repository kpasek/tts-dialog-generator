import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import argparse
import re  # <-- Nowy import
import uuid  # <-- Nowy import
from pydub import AudioSegment  # <-- Nowy import
from pydub.silence import detect_nonsilent  # <-- Nowy import

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- Import modeli TTS ---
from generators.stylish import StylishTTS
from generators.tts_base import TTSBase
from generators.xtts import XTTSPolishTTS


# --- Rejestr modeli ---
MODEL_REGISTRY = {
    "xtts": lambda voice: XTTSPolishTTS(voice_path=voice),
    "stylish": lambda voice: StylishTTS(),
}

# --- Globals ---
app = Flask(__name__)
tts_model: TTSBase | None = None
current_model_name: str | None = None
current_voice_path: Path | None = None

# --- Nowa funkcja pomocnicza: Dzielenie tekstu ---
def split_text(text: str, max_len: int = 200) -> list[str]:
    """
    Dzieli tekst na fragmenty <= max_len, szanując granice zdań i fraz.
    Implementuje logikę "minimalnej liczby podziałów".
    """
    if len(text) <= max_len:
        return [text]

    # 1. Zdefiniuj delimitery
    # Priorytet 1: Znaki końca zdania
    p1_delims = re.compile(r'([.?!…])')
    # Priorytet 2: Przecinki i myślniki
    p2_delims = re.compile(r'([,-])')
    
    base_units = []
    
    # 2. Spróbuj podzielić wg Priorytetu 1
    if p1_delims.search(text):
        parts = p1_delims.split(text)
    # 3. Jeśli brak P1, spróbuj podzielić wg Priorytetu 2
    elif p2_delims.search(text):
        parts = p2_delims.split(text)
    # 4. Jeśli brak jakichkolwiek delimiterów, podziel "na twardo"
    else:
        return [text[i:i + max_len] for i in range(0, len(text), max_len)]
    
    # 5. Złóż części z powrotem ( ['Tekst', '.'] -> ['Tekst.'] )
    temp_units = []
    for i in range(0, len(parts) - 1, 2):
        unit = (parts[i] + parts[i+1]).strip()
        if unit:
            temp_units.append(unit)
    if len(parts) % 2 == 1 and parts[-1].strip():
        temp_units.append(parts[-1].strip())

    # 6. Sprawdź, czy któraś jednostka bazowa nadal jest za długa
    final_base_units = []
    for unit in temp_units:
        if len(unit) > max_len:
            # Ta jednostka jest za długa. Spróbuj ją podzielić wg P2 (jeśli użyliśmy P1)
            if p1_delims.search(text) and p2_delims.search(unit):
                sub_parts = p2_delims.split(unit)
                temp_sub_units = []
                for i in range(0, len(sub_parts) - 1, 2):
                    sub_unit = (sub_parts[i] + sub_parts[i+1]).strip()
                    if sub_unit:
                        temp_sub_units.append(sub_unit)
                if len(sub_parts) % 2 == 1 and sub_parts[-1].strip():
                    temp_sub_units.append(sub_parts[-1].strip())
                
                # Sprawdź te pod-jednostki (na wypadek bardzo długiej frazy)
                for su in temp_sub_units:
                    if len(su) > max_len:
                        # Ostateczność: twarde cięcie
                        final_base_units.extend([su[i:i + max_len] for i in range(0, len(su), max_len)])
                    else:
                        final_base_units.append(su)
            else:
                # Brak P2 lub P2 już użyte, twarde cięcie
                final_base_units.extend([unit[i:i + max_len] for i in range(0, len(unit), max_len)])
        else:
            final_base_units.append(unit)
            
    # 7. Grupuj jednostki bazowe (implementacja "jak najmniej podziałów")
    grouped_chunks = []
    current_chunk = ""
    for unit in final_base_units:
        if not current_chunk:
            current_chunk = unit
        elif len(current_chunk) + 1 + len(unit) <= max_len: # +1 dla spacji
            current_chunk += " " + unit
        else:
            grouped_chunks.append(current_chunk)
            current_chunk = unit
    
    if current_chunk:
        grouped_chunks.append(current_chunk)

    return grouped_chunks

# --- Nowa funkcja pomocnicza: Przycinanie ciszy ---


def trim_silence(audio: AudioSegment, silence_thresh_db: int = -40, min_silence_ms: int = 1350) -> AudioSegment:
    """
    Przycina ciszę z początku i końca segmentu audio.
    Domyślny próg -40dB i 100ms ciszy.
    """
    nonsilent_parts = detect_nonsilent(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_thresh_db
    )
    
    if not nonsilent_parts:
        return audio # Zwróć oryginał, jeśli wszystko jest ciszą

    start_trim = nonsilent_parts[0][0]
    end_trim = nonsilent_parts[-1][1]
    
    return audio[start_trim:end_trim] # type: ignore


# --- Helper: inicjalizacja modelu ---
def initialize_model(model_name: str, voice_file: str | None):
    global tts_model, current_model_name, current_voice_path

    if model_name not in MODEL_REGISTRY:
        return False, f"Unknown model '{model_name}'"

    requested_voice_path = Path(voice_file) if voice_file else None
    if (
        tts_model is None
        or model_name != current_model_name
        or requested_voice_path != current_voice_path
    ):
        try:
            print(f"Loading model '{model_name}' with voice {requested_voice_path or 'default'}...")
            tts_model = MODEL_REGISTRY[model_name](requested_voice_path)
            current_model_name = model_name
            current_voice_path = requested_voice_path
            return True, f"Model '{model_name}' loaded successfully."
        except Exception as e:
            tts_model = None
            current_model_name = None
            return False, f"Failed to load model '{model_name}': {e}"
    return True, f"Model '{model_name}' already loaded."


# --- Endpoint ogólny (ZMODYFIKOWANY) ---
@app.route("/<model_name>/tts", methods=["POST"])
def tts_endpoint(model_name: str):
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    text = data.get("text")
    output_file = data.get("output_file")
    voice_file = data.get("voice_file")

    if not text or not output_file:
        return jsonify({"error": "Missing 'text' or 'output_file'"}), 400

    final_output_path = Path(output_file)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    success, msg = initialize_model(model_name.lower(), voice_file)
    if not success:
        return jsonify({"error": msg}), 500
    if tts_model is None:
        return jsonify({"error": "TTS model is not initialized."}), 500
    try:
        MAX_CHARS = 200 # Limit znaków
        generated_path: Path | None = None

        if len(text) <= MAX_CHARS:
            # Oryginalne zachowanie dla krótkich tekstów
            print(f"[{model_name}] Generating single TTS → {final_output_path}")

            generated_path = Path(tts_model.tts(text, str(final_output_path)))
        else:
            # Nowa logika dla długich tekstów
            print(f"[{model_name}] Text > {MAX_CHARS} chars. Splitting...")
            text_chunks = split_text(text, MAX_CHARS)
            print(f"[{model_name}] Split into {len(text_chunks)} chunks.")
            
            audio_clips = []
            # Tworzymy tymczasowy folder na części
            temp_dir = final_output_path.parent / f"temp_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(exist_ok=True)
            
            # Domyślny format (jeśli brak rozszerzenia)
            file_format = final_output_path.suffix.lstrip('.')
            if not file_format:
                file_format = "wav" 

            try:
                for i, chunk in enumerate(text_chunks):
                    # Unikalna nazwa pliku tymczasowego
                    temp_file_name = f"part_{i:03d}_{uuid.uuid4().hex[:6]}.{file_format}"
                    temp_file_path = temp_dir / temp_file_name
                    
                    print(f"[{model_name}] Generating chunk {i+1}/{len(text_chunks)} → {temp_file_path}")
                    
                    # Generowanie części
                    chunk_path_str = tts_model.tts(chunk, str(temp_file_path))
                    generated_chunk_path = Path(chunk_path_str)
                    
                    if generated_chunk_path.exists():
                        # Wczytaj, przytnij ciszę i dodaj do listy
                        audio_chunk = AudioSegment.from_file(generated_chunk_path, format=file_format)
                        trimmed_chunk = trim_silence(audio_chunk)
                        audio_clips.append(trimmed_chunk)
                    else:
                        print(f"[{model_name}] WARNING: Chunk {i+1} failed to generate or path was not returned.")
                
                if not audio_clips:
                    return jsonify({"error": "Failed to generate any audio chunks."}), 500
                
                # Łączenie klipów
                print(f"[{model_name}] Merging {len(audio_clips)} chunks → {final_output_path}")
                combined_audio = AudioSegment.empty()
                for clip in audio_clips:
                    combined_audio += clip # Pydub łączy segmenty operatorem +
                
                # Eksport finalnego pliku
                combined_audio.export(final_output_path, format=file_format)
                generated_path = final_output_path

            finally:
                # Sprzątanie plików tymczasowych
                if temp_dir.exists():
                    for f in temp_dir.glob('*'):
                        os.remove(f)
                    temp_dir.rmdir()

        # Reszta funkcji bez zmian
        return_audio = request.args.get("return_audio", "false").lower() == "true"

        if return_audio and generated_path and generated_path.exists():
            return send_file(generated_path, as_attachment=True, download_name=generated_path.name)
        
        if not generated_path or not generated_path.exists():
             return jsonify({"error": "Final audio file was not created."}), 500

        return jsonify({"message": msg, "output_file": str(generated_path)}), 200
    
    except Exception as e:
        # Zwróć szczegółowy błąd (pomocne przy debugowaniu Pydub/ffmpeg)
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Error during TTS generation: {e}", "trace": traceback.format_exc()}), 500


# --- Start serwera ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Model TTS API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    print(f"🚀 Starting Multi-Model TTS API on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)