import os


class DialogsGenerator:
    def __init__(self, subtitles_dir: str = "tts_ready"):
        self.subtitles_dir = subtitles_dir
        self.generated_dialogs_dirs = []

    def generate(self, tts):
        for subtitles in os.listdir(self.subtitles_dir):
            if not subtitles.endswith(".txt"):
                continue

            out_dir = os.path.join("dialogs", subtitles[:-4])
            os.makedirs(out_dir, exist_ok=True)

            with open(os.path.join(self.subtitles_dir, subtitles), "r", encoding="utf-8") as f:
                dialogs = [line.strip() for line in f]

            for idx, dialog in enumerate(dialogs, start=1):
                output_path = os.path.join(out_dir, f"output1 ({idx}).wav")
                if os.path.exists(output_path) or not dialog.strip():
                    continue
                print(f"Generuję: {output_path}")
                try:
                    tts.tts(dialog, output_path=output_path)
                except:
                    print(f"Nie udało się wygenerować pliku: {output_path}")

            self.generated_dialogs_dirs.append(out_dir)
