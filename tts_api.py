import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import argparse

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- Import modeli TTS ---
from generators.stylish import StylishTTS
from  generators.tts_base import TTSBase
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


# --- Endpoint ogólny ---
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

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    success, msg = initialize_model(model_name.lower(), voice_file)
    if not success:
        return jsonify({"error": msg}), 500

    try:
        print(f"[{model_name}] Generating TTS → {output_file}")
        generated_path = Path(tts_model.tts(text, output_file))
        return_audio = request.args.get("return_audio", "false").lower() == "true"

        if return_audio and generated_path.exists():
            return send_file(generated_path, as_attachment=True, download_name=generated_path.name)
        return jsonify({"message": msg, "output_file": str(generated_path)}), 200
    except Exception as e:
        return jsonify({"error": f"Error during TTS generation: {e}"}), 500


# --- Start serwera ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Model TTS API Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    print(f"🚀 Starting Multi-Model TTS API on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)
