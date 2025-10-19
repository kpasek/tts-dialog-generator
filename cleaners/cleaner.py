import re
import os


class Cleaner:
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        self.input_file = input_file
        self.output_file = output_file
        self.pattern = r'\b([1-9]|[12][0-9]|3[01])\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia|styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)\b'
        self.pattern2 = r'\b([1-9]|[12][0-9]|3[01])\s+(styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)\b'

        self.days_pl = {
            1: "pierwszy", 2: "drugi", 3: "trzeci", 4: "czwarty", 5: "piąty",
            6: "szósty", 7: "siódmy", 8: "ósmy", 9: "dziewiąty", 10: "dziesiąty",
            11: "jedenasty", 12: "dwunasty", 13: "trzynasty", 14: "czternasty",
            15: "piętnasty", 16: "szesnasty", 17: "siedemnasty", 18: "osiemnasty",
            19: "dziewiętnasty", 20: "dwudziesty", 21: "dwudziesty pierwszy",
            22: "dwudziesty drugi", 23: "dwudziesty trzeci", 24: "dwudziesty czwarty",
            25: "dwudziesty piąty", 26: "dwudziesty szósty", 27: "dwudziesty siódmy",
            28: "dwudziesty ósmy", 29: "dwudziesty dziewiąty", 30: "trzydziesty",
            31: "trzydziesty pierwszy"
        }
        self.patterns = []

    def clean_line(self, line: str) -> str:
        line = re.sub(r"^\[.*?]$", "", line)
        line = re.sub(r"^<.*?>$", "", line)
        line = re.sub(r"^\(.*?\)$", "", line)
        line = re.sub(r"^\{.*?\}$", "", line)
        # line = re.sub(r"^[A-Z0-9óążźćęńł\"]{1,5}[?!.,]*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^[0-9]+$", "", line)
        line = re.sub(r" ", "", line)
        no_special_chars = line.lower().rstrip(",.?! ")
        if re.match(r"^\S+$", no_special_chars) and len(no_special_chars) <= 3 and no_special_chars not in ["tak", "nie"]:
            return ""
        return line.strip()

    def tts_line(self, text: str) -> str:
        for pattern in self.get_patterns():
            ignore_case = pattern[2] if len(pattern) > 2 else True
            kwargs = {
                "pattern": pattern[0],
                "repl": pattern[1],
                "string": text,
                "flags": re.IGNORECASE if ignore_case else 0
            }
            text = re.sub(**kwargs)
        text = self.tts_date(text)
        text = re.sub(r"\[.*?]+", "", text)
        text = re.sub(r"\<.*?\>", " ", text)
        text = re.sub(r"\(.*?\)", " ", text)
        text = re.sub(r"\{\/?i\}", "", text)
        text = re.sub(r"\{.*?\}", " ", text)
        text = re.sub(r"…", "...", text)
        text = re.sub(r"\.{2,}", ".", text)
        text = re.sub(r"\?!", "?", text)
        text = re.sub(r"\?{2,}", "?", text)
        text = re.sub(r"#+", "", text)
        text = re.sub(r" ", " ", text)
        text = re.sub(r" {2,}", " ", text)

        text = text.strip('.').strip('–').strip('"').strip()
        return text

    def get_patterns(self):
        return self.patterns

    def tts_date(self, line):
        def change_date(match):
            number = int(match.group(1))
            month = match.group(2)
            return f"{self.days_pl[number]} {month}"

        def change_date2(match):
            number = int(match.group(1))
            month = match.group(2)
            return f"{self.days_pl[number]} {month}"

        line = re.sub(self.pattern, change_date, line)
        return re.sub(self.pattern2, change_date2, line)

    def process_file(self, fn, add_always=False):
        seen = set()
        with open(self.input_file, "r", encoding="utf-8") as f_in, open(str(self.output_file), "w", encoding="utf-8") as f_out:
            for line in f_in:
                clean = fn(line)
                if add_always or (clean and clean not in seen):
                    seen.add(clean)
                    f_out.write(clean + "\n")

        print(f"Przetworzono plik {self.input_file} na {self.output_file}")

    def sort_file(self, reverse=False):
        lines = set()
        with open(self.input_file, "r", encoding="utf-8") as f_in:
            for line in f_in:
                if line and line not in lines:
                    lines.add(line.strip())

        lines = sorted(lines, key=len, reverse=reverse)
        with open(str(self.output_file), "w", encoding="utf-8") as f_out:
            for line in lines:
                f_out.write(line + "\n")

    def clean_file(self):
        self.process_file(self.clean_line)

    def tts_file(self):
        self.process_file(self.tts_line, True)

    def remove_voice_files_by_regex(self, regex_pattern: str, voices_dir=None, ignore_case=False):
        pattern = re.compile(
            regex_pattern, flags=re.IGNORECASE if ignore_case else 0)
        if voices_dir is None:
            voices_dir = "voices" + self.input_file[7:-4]
        with open(self.input_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if pattern.search(line):
                    wav_path = os.path.join(voices_dir, f"output1 ({i}).wav")
                    ogg_org_path = os.path.join(
                        voices_dir, f"output1 ({i}).ogg")
                    ogg_path = os.path.join(
                        voices_dir, "ready", f"output1 ({i}).ogg")
                    ogg2_path = os.path.join(
                        voices_dir, "ready", f"output2 ({i}).ogg")
                    for path in [wav_path, ogg_path, ogg2_path, ogg_org_path]:
                        if os.path.exists(path):
                            print(f"Usuwam: {i} -> {path}")
                            os.remove(path)

    def compare_files(self, limit: int = 10) -> list[int]:
        diffs = []
        with open(self.input_file, "r", encoding="utf-8") as f1, open(str(self.output_file), "r", encoding="utf-8") as f2:
            for i, (line1, line2) in enumerate(zip(f1, f2), 1):
                if line1.strip() != line2.strip():
                    # Read next lines
                    next_line1 = f1.readline()
                    next_line2 = f2.readline()
                    if not next_line1 or not next_line2:
                        break
                    if next_line1.strip() != next_line2.strip():
                        diffs.append(i)
                        if len(diffs) >= limit:
                            break
        return diffs

    def clean(self):
        out = str(self.output_file)
        self.output_file = f"{out[:-4]}_subtitles.txt"
        if os.path.exists(self.output_file):
            os.rename(self.output_file,
                      f"{self.output_file[:-4]}_old.{self.output_file[-3:]}")
        self.clean_file()
        self.input_file = self.output_file
        self.output_file = out
        if os.path.exists(self.output_file):
            os.rename(self.output_file,
                      f"{self.output_file[:-4]}_old.{self.output_file[-3:]}")
        self.tts_file()
