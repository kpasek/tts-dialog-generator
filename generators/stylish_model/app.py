import gradio as gr
import torch
import numpy as np
import os
import random
import librosa
import phonemizer
from stylish_model.config_loader import load_model_config_yaml
from stylish_model.models.export_model import ExportModel
from stylish_model.models.models import build_model
from stylish_model.text_utils import TextCleaner
from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.set_library("C:\\Program Files\\eSpeak NG\\libespeak-ng.dll")
# Set random seeds for reproducibility
torch.manual_seed(0)
random.seed(0)
np.random.seed(0)

# Initialize global variables
global_phonemizer = None
text_cleaner = None
model = None
device = "cpu"

# Local tts_model files
CHECKPOINT_DIR = "tts_model/checkpoint_final"
MODEL_CONFIG_PATH = "tts_model/model.yml"

# Define examples for the interface
examples = [
    ["Witaj świecie! Jak się masz dzisiaj?", 1.0],
    ["Dziękuję bardzo za pomoc w tym projekcie.", 0.8],
    ["Polska jest pięknym krajem z bogatą historią i kulturą.", 1.2],
    ["Dzisiaj jest piękna pogoda na spacer.", 1.0],
    ["Czy możesz mi pomóc z tym zadaniem?", 0.9],
    ["Świetnie się bawię, ucząc się nowych rzeczy.", 1.1],
]


def initialize_model():
    global text_cleaner, model, global_phonemizer, device

    print("🔄 Loading tts_model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"📱 Using device: {device}")

    # Initialize phonemizer
    global_phonemizer = phonemizer.backend.EspeakBackend(
        language="pl", preserve_punctuation=True, with_stress=True
    )

    # Load config once
    model_config = load_model_config_yaml(MODEL_CONFIG_PATH)
    
    # Initialize text cleaner once
    text_cleaner = TextCleaner(model_config.symbol)
    
    # Build and load tts_model
    model_dict = build_model(model_config)
    
    # Load tts_model checkpoints efficiently
    for idx, key in enumerate(model_dict.keys()):
        model_path = os.path.join(
            CHECKPOINT_DIR, 
            "pytorch_model.bin" if idx == 0 else f"pytorch_model_{idx}.bin"
        )
        
        state_dict = torch.load(model_path, map_location=device)
        model_dict[key].load_state_dict(state_dict, strict=False)
        model_dict[key].to(device).eval()  # Set to eval mode immediately
        print(f"✅ Loaded {key}")

    # Create export tts_model
    model = ExportModel(**model_dict, device=device).eval()

    print("🎉 Model initialized successfully!")
    return "Model załadowany pomyślnie!"


def split_text(text, max_length=150):
    """Simple text splitting function"""
    sentences = []
    current = ""
    
    for char in text:
        current += char
        if char in ".?!;":
            if current.strip():
                sentences.append(current.strip())
            current = ""
    
    if current.strip():
        sentences.append(current.strip())
    
    # Split long sentences
    final_sentences = []
    for sentence in sentences:
        if len(sentence) <= max_length:
            final_sentences.append(sentence)
        else:
            words = sentence.split()
            chunk = ""
            for word in words:
                if len(chunk + " " + word) <= max_length:
                    chunk += " " + word if chunk else word
                else:
                    if chunk:
                        final_sentences.append(chunk)
                    chunk = word
            if chunk:
                final_sentences.append(chunk)
    
    return [s for s in final_sentences if s.strip()]


def synthesize_chunk(text_chunk):
    """Synthesize a single text chunk"""
    global text_cleaner, model, global_phonemizer, device

    if not text_chunk.strip():
        return np.array([], dtype=np.int16)

    # Clean text
    text_chunk = text_chunk.strip().replace('"', "")
    
    # Get phonemes
    phonemes_list = global_phonemizer.phonemize([text_chunk])
    if not phonemes_list or not phonemes_list[0]:
        return np.array([], dtype=np.int16)
    
    # Convert to tokens
    phoneme_ids = text_cleaner(phonemes_list[0])
    if not phoneme_ids:
        return np.array([], dtype=np.int16)

    # Prepare tts_model input
    tokens = torch.tensor(phoneme_ids).unsqueeze(0).to(device)
    texts = torch.zeros([1, tokens.shape[1] + 2], dtype=torch.long).to(device)
    texts[0][1:tokens.shape[1] + 1] = tokens
    text_lengths = torch.tensor([tokens.shape[1] + 2]).to(device)

    # Generate audio
    with torch.no_grad():
        outputs = model(texts, text_lengths)

    if outputs.numel() == 0:
        return np.array([], dtype=np.int16)

    # Simple audio processing with tanh
    audio = torch.tanh(outputs).cpu().numpy().squeeze()
    
    # Ensure 1D array
    if audio.ndim == 0:
        audio = np.array([audio.item()])
    elif audio.ndim > 1:
        audio = audio.flatten()

    if audio.size == 0:
        return np.array([], dtype=np.int16)
    audio = normalize_audio(audio, peak=0.85)

    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16


def synthesize_text(text, speed=1.0, progress=gr.Progress()):
    """Main synthesis function"""
    if not text.strip():
        raise gr.Error("Musisz wprowadzić jakiś tekst")
    if len(text) > 5000:  # Reduced limit for faster processing
        raise gr.Error("Tekst musi być krótszy niż 5k znaków")

    try:
        # Split text into chunks
        chunks = split_text(text, max_length=500)  # Smaller chunks for speed
        if not chunks:
            chunks = [text.strip()]

        # Generate audio segments
        audio_segments = []
        silence = np.zeros(int(24000 * 0.05), dtype=np.int16)  # Shorter silence

        for i, chunk in enumerate(progress.tqdm(chunks, desc="Generowanie...")):
            audio_chunk = synthesize_chunk(chunk)
            if len(audio_chunk) > 0:
                audio_segments.append(audio_chunk)
                if i < len(chunks) - 1:
                    audio_segments.append(silence)

        if not audio_segments:
            raise gr.Error("Nie udało się wygenerować audio")

        # Concatenate audio
        final_audio = np.concatenate(audio_segments)

        # Apply speed adjustment if needed
        if speed != 1.0 and 0.5 <= speed <= 2.0:
            try:
                audio_float = final_audio.astype(np.float32) / 32768.0
                audio_float = librosa.effects.time_stretch(audio_float, rate=speed)
                final_audio = (audio_float * 32767).astype(np.int16)
            except Exception:
                pass  # Use original audio if speed adjustment fails

        return 24000, final_audio

    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(f"Błąd: {str(e)}")

def normalize_audio(audio, peak=0.95):
    if audio.size == 0:
        return audio
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio * (peak / max_val)
    return audio

print("🚀 Starting Polish TTS...")
try:
    status = initialize_model()
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    status = f"Błąd inicjalizacji: {str(e)}"
