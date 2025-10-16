from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class Crysis1Cleaner(Cleaner):
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        super().__init__(input_file, output_file)

    def clean_line(self, line: str) -> str:
        line = re.sub(r".*[tT]rigge[rd].*", "", line)
        line = re.sub(r"##.*", "", line)
        line = re.sub(r"\\n.*", "", line)
        return super().clean_line(line)
    
    def tts_line(self, text: str) -> str:
        line = re.sub(r"##", " ", text)
        line = re.sub(r"\\n", " ", text)
        return super().tts_line(text)

    def get_patterns(self):
        return [
    (r"Andrew","Endrju"),
    (r"Badowsky","Badowski"),
    (r"Barnes","Barns"),
    (r"Bornheim","Bornhajm"),
    (r"Bradley","Bradlej"),
    (r"C4","Ce-cztery"),
    (r"Collins","Kolins"),
    (r"Constitution","Konstituszyn"),
    (r"Cooper","Kuper"),
    (r"David","Dejwid"),
    (r"Davis","Dejwis"),
    (r"Douglas","Daglas"),
    (r"Eddie","Edi"),
    (r"Gauss","Gałss"),
    (r"Gillespie","Gilespi"),
    (r"Hongzhou","Hongdżou"),
    (r"Idaho","Ajdaho"),
    (r"Joe","Dżo"),
    (r"Joey","Dżoi"),
    (r"Johnson","Dżonson"),
    (r"Jones","Dżons"),
    (r"Joseph","Dżozef"),
    (r"JSOC","Dżejsok"),
    (r"Keegan","Kigen"),
    (r"Kjong","Kiong"),
    (r"Lancaster","Lankaster"),
    (r"Langley","Langlej"),
    (r"Lexington","Leksington"),
    (r"Lingshan","Lingszan"),
    (r"Manhattan","Manhatan"),
    (r"Mike","Majk"),
    (r"Morrison","Morison"),
    (r"Partlett","Partlet"),
    (r"Patton","Paton"),
    (r"PDA","Pe-de-a"),
    (r"Rhee","Ri"),
    (r"Rosenthal","Rozental"),
    (r"Silver","Silwer"),
    (r"Skychief","Skajczif"),
    (r"Strickland","Striklend"),
    (r"USS","Ju-es-es"),
    (r"VTOL","Witol"),
    (r"Wen","Łen"),
    (r"Whiskey","Łiski"),
    (r"Xiaoping","Siao-ping"),
    (r"Xray","Iksrej"),
    (r"Yaobang","Jaobang"),
    (r"K\*\*\*a\!?","kurwa"),
    (r"K\*\*\*y\!?","kurwy"),
    (r"popiep\*\*one","popierdolone"),
    (r"piep\*\*yć","pieprzyć"),
    (r"poj\*\*\*e","pojebie"),
    (r"wpier\*\*\*","wpierdol"),
    (r"skurw\*\*l","skurwiel"),
    (r"piep\*\*enia","pieprzenia"),
    (r"kur\*stwo","kurestwo"),
    (r"pier\*\*[\*l]on","pierdolon"),
    (r"Zajeb\*\*cie","zajebiście"),
    (r"piep\*\*ony","pieprzony"),
]


# cleaner = Crysis1Cleaner("../subtitles/crysis1/crysis1_subtitles.txt", "../subtitles/crysis1/crysis1.txt")
# for pattern in cleaner.get_patterns():
#     cleaner.remove_voice_files_by_regex(r"Nomad", "../dialogs/crysis1")

# cleaner = Crysis1Cleaner("../subtitles/crysis1/subtitles_raw.txt", "../subtitles/crysis1/crysis1.txt")
# cleaner.clean()
