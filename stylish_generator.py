from generators.generator import DialogsGenerator
from generators.stylish import TTS

if __name__ == "__main__":
    generator = DialogsGenerator()
    tts = TTS()
    generator.generate(tts)