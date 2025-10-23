import os
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import argparse

# Ensure generators are importable (adjust if your structure differs)
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from generators.xtts import XTTSPolishTTS
    from app.utils import is_installed

    TORCH_INSTALLED = is_installed('torch')
except ImportError as e:
    print(f"Error importing dependencies for API server: {e}")
    print("Make sure 'torch', 'TTS', and 'flask' are installed in the API server's environment.")
    sys.exit(1)

# --- Globals ---
app = Flask(__name__)
tts_model: XTTSPolishTTS | None = None
current_voice_path: Path | None = None


# --- Helper Functions ---
def initialize_tts_model(voice_path_str: str | None) -> tuple[bool, str]:
    """
    Initializes or re-initializes the TTS model if the voice path changes.

    Args:
        voice_path_str: The path to the voice file requested by the client.

    Returns:
        A tuple (success: bool, message: str).
    """
    global tts_model, current_voice_path
    if not TORCH_INSTALLED:
        return False, "Torch is not installed in the API server environment."

    requested_voice_path = Path(voice_path_str) if voice_path_str else None

    # Check if model needs loading/reloading
    if tts_model is None or requested_voice_path != current_voice_path:
        try:
            print(f"Loading XTTS model with voice: {requested_voice_path or 'default'}...")
            tts_model = XTTSPolishTTS(voice_path=requested_voice_path)
            current_voice_path = requested_voice_path
            print("Model loaded successfully.")
            return True, "Model loaded successfully."
        except Exception as e:
            tts_model = None
            current_voice_path = None
            error_message = f"Failed to load XTTS model: {e}"
            print(error_message)
            return False, error_message
    return True, "Model already loaded with the correct voice."


# --- API Endpoint ---
@app.route('/xtts/tts', methods=['POST'])
def generate_tts():
    """
    Flask endpoint to generate TTS using the loaded XTTS model.
    Expects JSON payload: {"text": "...", "output_file": "...", "voice_file": "..."}
    Optional query parameter: ?return_audio=true
    """
    global tts_model
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    text = data.get('text')
    output_file = data.get('output_file')
    voice_file = data.get('voice_file')  # Voice file path passed from client

    if not text or not output_file:
        return jsonify({"error": "Missing 'text' or 'output_file' in JSON payload"}), 400

    # Ensure output directory exists
    try:
        output_dir = Path(output_file).parent
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return jsonify({"error": f"Could not create output directory: {e}"}), 500

    # Initialize model if needed
    success, message = initialize_tts_model(voice_file)
    if not success:
        return jsonify({"error": message}), 500
    if tts_model is None:  # Should be caught by initialize, but belt-and-suspenders
        return jsonify({"error": "TTS Model is not loaded"}), 500

    try:
        # Generate audio
        print(f"Generating TTS for: {output_file}")
        generated_path_str = tts_model.tts(text, output_path=output_file)
        generated_path = Path(generated_path_str)

        # Check if audio should be returned in the response
        return_audio = request.args.get('return_audio', 'false').lower() == 'true'

        if return_audio:
            if generated_path.exists():
                print(f"Returning audio file: {generated_path}")
                return send_file(generated_path, as_attachment=True, download_name=generated_path.name)
            else:
                return jsonify({"error": "Generated file not found, but TTS reported success."}), 500
        else:
            print(f"Successfully saved TTS to: {generated_path}")
            return jsonify({"message": "TTS generated successfully", "output_file": generated_path_str}), 200

    except Exception as e:
        error_message = f"Error during TTS generation: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500


# --- Server Startup ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XTTS API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    # No initial voice path needed here, client sends it
    args = parser.parse_args()

    if not TORCH_INSTALLED:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! PyTorch is not installed. XTTS API Server cannot run. !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    print(f"Starting XTTS API server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port)  # Add debug=True for development