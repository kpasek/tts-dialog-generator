from generators.generator import DialogsGenerator
from generators.xtts import XTTSPolishTTS

if __name__ == "__main__":
    generator = DialogsGenerator()
    tts = XTTSPolishTTS()
    generator.generate(tts)