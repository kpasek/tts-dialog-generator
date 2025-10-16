from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class AsterixCleaner(Cleaner):
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        super().__init__(input_file, output_file)

    def extract(self, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        for text_block in root.findall(".//block"):
            text_elem = text_block.find("Original")

            if text_elem is not None and text_elem.text and "\n" in text_elem.text:
                continue

            if text_elem is not None and text_elem.text:
                for res in text_block.findall(".//Original"):
                    with open(self.output_file, "a", encoding="utf-8") as f:
                        f.write(text_elem.text.strip() + "\n")

    def extractAll(self, xml_dir):
        for filename in os.listdir(xml_dir):
            if filename.lower().endswith(".xml"):
                xml_file = os.path.join(xml_dir, filename)
                self.extract(xml_file)

    def clean_line(self, line: str) -> str:
        line = re.sub(r"^pl_\d+$", "", line)
        return super().clean_line(line)

    def get_patterns(self):
        return [
            (r"Athenry", "Atenraj"),
            (r"Cranberriksów", "Kranberisów"),
            (r"hat-tryk", "hat-trik"),
            (r"Whiskitoniks", "Łiskitoniks"),
            (r"Quo", "Kwo"),
            (r"vadis", "wadis"),
            (r"Drogheda", "Droheda"),
            (r"Autofokus", "Ałtofokus"),
            (r"Béal", "Bejl"),
            (r"Bocht", "Bokt"),
            (r"Eriu", "Eiru"),
            (r"Vae", "We"),
            (r"victis", "wiktis"),
            (r"Quid", "Kwid"),
            (r"Exercitus", "Ekscercitus"),
            (r"viam", "wiam"),
            (r"O'Kejdokis", "Okej-dokis"),
            (r"O'Keja", "Okeja"),
            (r" 50 ", " pięćdziesiąty "),
        ]


cleaner = AsterixCleaner("../subtitles/asterix/subtitles.txt", "../subtitles/asterix/asterix.txt")
# for pattern in cleaner.get_patterns():
cleaner.remove_voice_files_by_regex(r" 50 ","../dialogs/asterix")
cleaner.clean()
