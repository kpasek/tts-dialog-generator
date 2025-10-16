from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class Crysis3Cleaner(Cleaner):
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        super().__init__(input_file, output_file)


    def clean_line(self, line: str) -> str:
        line = re.sub(r".*[tT]rigge[rd].*", "", line)
        line = re.sub(r"##.*", "", line)
        return super().clean_line(line)

    def get_patterns(self):
        return [
            (r"Barnes", "barns"),
            (r"Blacktail", "blakteil"),
            (r"Bravo", "brawo"),
            (r"Broadway", "brodłej"),
            (r"C.E.L.L", "si i el el"),
            (r"CDZ", "ce de zet"),
            (r"Charlie", "czarli"),
            (r"Claire", "kler"),
            (r"DNA", "de-en-a"),
            (r"Delta", "delta"),
            (r"EMP", "i em pi"),
            (r"Foxtrot", "fokstrot"),
            (r"Fulton", "fulton"),
            (r"GSR", "gie es er"),
            (r"Gomez", "gomez"),
            (r"Hitman", "hitmen"),
            (r"NAX", "en ej eks"),
            (r"Orka", "orka"),
            (r"Romeo", "romeo"),
            (r"X", "iks"),
            (r"Rasch", "Rasz"),
            (r"Laurence", "Lorens"),
            (r"Hunter", "Hanter"),
            (r"Lingshan", "Lingszan"),
            (r"Sherman", "Szerman"),
            (r"Barclay", "Barklej"),
            (r"Marshall", "Marszal"),
        ]


# cleaner = Crysis3Cleaner("../subtitles/crysis3/subtitles.txt", "../subtitles/crysis3/crysis3.txt")
# cleaner.clean()
