import os
import sys
import shutil
from pathlib import Path
import time
from flask import Flask, request, jsonify, send_file
import argparse
import re
import uuid
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

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
tts_model: TTSBase | None = None
current_model_name: str | None = None
current_voice_path: Path | None = None


def split_text(text: str, max_len: int = 200) -> list[str]:
    """
    Dzieli tekst na fragmenty <= max_len.
    """
    if len(text) <= max_len:
        return [text]

    p1_delims = re.compile(r'([.?!…])')
    p2_delims = re.compile(r'([,-])')
    p3_delims = re.compile(r'( )')
    
    base_units = []
    if p1_delims.search(text):
        parts = p1_delims.split(text)
    elif p2_delims.search(text):
        parts = p2_delims.split(text)
    else:
        parts = p3_delims.split(text)

    temp_units = []
    for i in range(0, len(parts) - 1, 2):
        unit = (parts[i] + parts[i+1]).strip()
        if unit:
            temp_units.append(unit)
    if len(parts) % 2 == 1 and parts[-1].strip():
        temp_units.append(parts[-1].strip())

    final_base_units = []
    for unit in temp_units:
        if len(unit) > max_len:
            if p1_delims.search(text) and p2_delims.search(unit):
                sub_parts = p2_delims.split(unit)
                temp_sub_units = []
                for i in range(0, len(sub_parts) - 1, 2):
                    sub_unit = (sub_parts[i] + sub_parts[i+1]).strip()
                    if sub_unit:
                        temp_sub_units.append(sub_unit)
                if len(sub_parts) % 2 == 1 and sub_parts[-1].strip():
                    temp_sub_units.append(sub_parts[-1].strip())

                for su in temp_sub_units:
                    if len(su) > max_len:
                        final_base_units.extend([su[i:i + max_len] for i in range(0, len(su), max_len)])
                    else:
                        final_base_units.append(su)
            else:
                final_base_units.extend([unit[i:i + max_len] for i in range(0, len(unit), max_len)])
        else:
            final_base_units.append(unit)

    grouped_chunks = []
    current_chunk = ""
    for unit in final_base_units:
        if not current_chunk:
            current_chunk = unit
        elif len(current_chunk) + 1 + len(unit) <= max_len:
            current_chunk += " " + unit
        else:
            grouped_chunks.append(current_chunk)
            current_chunk = unit
    
    if current_chunk:
        grouped_chunks.append(current_chunk)

    return grouped_chunks


def trim_silence(audio: AudioSegment, silence_thresh_db: int = -40, min_silence_ms: int = 1350) -> AudioSegment:
    nonsilent_parts = detect_nonsilent(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_thresh_db
    )
    
    if not nonsilent_parts:
        return audio

    start_trim = nonsilent_parts[0][0]
    end_trim = nonsilent_parts[-1][1]
    
    return audio[start_trim:end_trim] # type: ignore


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


def create_app(path_converter, staging_dir: Path | None = None):
    """
    path_converter: funkcja do zmiany ścieżek (Windows -> WSL)
    staging_dir: opcjonalna ścieżka do katalogu szybkiego zapisu (Linux native). 
                 Jeśli None, zapisuje bezpośrednio do celu.
    """
    app = Flask(__name__)

    @app.route("/<model_name>/tts", methods=["POST"])
    def tts_endpoint(model_name: str):
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        text = data.get("text")
        
        # 1. Ustalanie docelowej ścieżki (po konwersji /mnt/d/...)
        output_file_raw = data.get("output_file")
        real_output_file = path_converter(output_file_raw) if output_file_raw else None
        
        voice_file_raw = data.get("voice_file")
        voice_file = path_converter(voice_file_raw) if voice_file_raw else None

        if not text or not real_output_file:
            return jsonify({"error": "Missing 'text' or 'output_file'"}), 400

        real_output_path = Path(real_output_file)
        
        try:
            real_output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Cannot create destination directory: {e}")
            return jsonify({"error": f"Cannot create destination directory: {e}"}), 500

        if staging_dir:
            staging_filename = f"{uuid.uuid4().hex[:8]}_{real_output_path.name}"
            working_path = staging_dir / staging_filename
        else:
            working_path = real_output_path

        success, msg = initialize_model(model_name.lower(), voice_file)
        if not success:
            print(f"Model initialization error: {msg}")
            return jsonify({"error": msg}), 500
        if tts_model is None:
            print("Critical Error: tts_model is None after initialization.")
            return jsonify({"error": "TTS model is not initialized."}), 500
        
        try:
            MAX_CHARS = 200
            generated_path: Path | None = None
            
            start_t = time.time()

            if len(text) <= MAX_CHARS:
                print(f"[{model_name}] Generating single TTS → {working_path}")
                # Model zapisuje do working_path
                generated_path = Path(tts_model.tts(text, str(working_path)))
            else:
                print(f"[{model_name}] Text > {MAX_CHARS} chars. Splitting...")
                text_chunks = split_text(text, MAX_CHARS)
                print(f"[{model_name}] Split into {len(text_chunks)} chunks.")
                
                audio_clips = []
                
                # Temp dir tworzymy względem working_path. 
                # Jeśli working_path jest na Linuxie (staging), temp też tam będzie (SZYBKO!)
                temp_dir = working_path.parent / f"temp_{uuid.uuid4().hex[:8]}"
                temp_dir.mkdir(exist_ok=True)

                file_format = working_path.suffix.lstrip('.')
                if not file_format:
                    file_format = "wav" 

                try:
                    for i, chunk in enumerate(text_chunks):
                        temp_file_name = f"part_{i:03d}_{uuid.uuid4().hex[:6]}.{file_format}"
                        temp_file_path = temp_dir / temp_file_name
                        
                        chunk_path_str = tts_model.tts(chunk, str(temp_file_path))
                        generated_chunk_path = Path(chunk_path_str)
                        
                        if generated_chunk_path.exists():
                            audio_chunk = AudioSegment.from_file(generated_chunk_path, format=file_format)
                            trimmed_chunk = trim_silence(audio_chunk)
                            audio_clips.append(trimmed_chunk)
                        else:
                            print(f"[{model_name}] WARNING: Chunk {i+1} failed.")
                    
                    if not audio_clips:
                        print(f"[{model_name}] ERROR: No audio chunks were generated.")
                        return jsonify({"error": "Failed to generate any audio chunks."}), 500
                    
                    print(f"[{model_name}] Merging {len(audio_clips)} chunks → {working_path}")
                    combined_audio = AudioSegment.empty()
                    for clip in audio_clips:
                        combined_audio += clip
                    
                    combined_audio.export(working_path, format=file_format)
                    generated_path = working_path

                finally:
                    if temp_dir.exists():
                        for f in temp_dir.glob('*'):
                            os.remove(f)
                        temp_dir.rmdir()

            # 3. Finalizacja - Przenoszenie jeśli użyto staging
            final_file_ready = False
            
            if generated_path and generated_path.exists():
                if staging_dir:
                    print(f"📦 Moving from staging to final dest: {real_output_path}")
                    # shutil.move obsługuje przenoszenie między systemami plików (copy+delete)
                    shutil.move(str(generated_path), str(real_output_path))
                    final_file_ready = True
                else:
                    final_file_ready = True
            
            if not final_file_ready:
                print("ERROR: Final audio file was not created.")
                return jsonify({"error": "Final audio file was not created."}), 500

            # Obsługa return_audio (opcjonalne pobieranie)
            return_audio = request.args.get("return_audio", "false").lower() == "true"
            if return_audio:
                return send_file(real_output_path, as_attachment=True, download_name=real_output_path.name)

            print(f"{time.time() - start_t:.2f}: {text}")
            return jsonify({"message": msg, "output_file": str(real_output_path)}), 200
        
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return jsonify({"error": f"Error during TTS generation: {e}", "trace": traceback.format_exc()}), 500

    return app

def run_server(path_converter, staging_path: str | None = None):
    parser = argparse.ArgumentParser(description="Multi-Model TTS API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    staging_dir_obj = Path(staging_path) if staging_path else None
    
    # Jeśli podano staging, upewnij się że istnieje
    if staging_dir_obj:
        staging_dir_obj.mkdir(parents=True, exist_ok=True)
        print(f"✅ Staging enabled. Fast generation at: {staging_dir_obj}")
    else:
        print(f"ℹ️ Staging disabled. Direct write mode.")

    print(f"🚀 Starting Multi-Model TTS API on http://{args.host}:{args.port}")
    app = create_app(path_converter, staging_dir=staging_dir_obj)
    app.run(host=args.host, port=args.port)