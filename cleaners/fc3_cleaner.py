from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class FC3Cleaner(Cleaner):
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
  (r"ABC", "A Be Ce"),
  (r"baby", "bejbi"),
  (r"Bangau", "Bangał"),
  (r"Baguslah", "Bagusla"),
  (r"Benjamin", "Bendżamin"),
  (r"Benny", "Beni"),
  (r"Blitzkrieg", "Blitskrik"),
  (r"Bowa-Seko", "Boła Seko"),
  (r"BTS", "bi ti es"),
  (r"Buck", "Bak"),
  (r"buona", "błona"),
  (r"C4", "ce cztery"),
  (r"California", "Kalifornia"),
  (r"Call", "Kol"),
  (r"Callum", "Kalum"),
  (r"Capisce", "Kapiszi"),
  (r"Challenger", "Czalendżer"),
  (r"cheer", "czir"),
  (r"Churchtown", "Czercztałn"),
  (r"Coco", "Koko"),
  (r"Colby", "Kolbi"),
  (r"con", "kon"),
  (r"cool", "kul"),
  (r"DARE", "der"),
  (r"Daisy", "Dejzi"),
  (r"David", "Dejwid"),
  (r"Dayum", "dejm"),
  (r"Deepsea", "Dipsi"),
  (r"Deutschland", "Dojczland"),
  (r"Disco", "Disko"),
  (r"DJ", "didżej"),
  (r"Doug", "Dag"),
  (r"drei", "draj"),
  (r"Drive", "Drajw"),
  (r"Duty", "Djuti"),
  (r"ein", "ajn"),
  (r"erledigt", "erledikt"),
  (r"Forrest", "Forest"),
  (r"fuck", "fak"),
  (r"George", "Dżordż"),
  (r"Gott", "Got"),
  (r"hello", "heloł"),
  (r"Hector", "Hektor"),
  (r"Himmel", "Himel"),
  (r"holla", "hola"),
  (r"Hollywood", "Holiłud"),
  (r"Hoyt", "Hojt"),
  (r"Hurk", "Herk"),
  (r"J ", "dżej "),
  (r"jalan", "dżalan"),
  (r"Jalak", "Dżalak"),
  (r"jangalah", "dżangala"),
  (r"Jason", "Dżejson"),
  (r"jumpa", "dżumpa"),
  (r"Kasih", "Kasi"),
  (r"Keith", "Kif"),
  (r"kia", "kija"),
  (r"L.A.", "El Ej"),
  (r"Labah-labah", "Laba laba"),
  (r"Langley", "Langlej"),
  (r"Liza", "Lajza"),
  (r"LSD", "el es de"),
  (r"Luke", "Luk"),
  (r"M9", "em dziewięć"),
  (r"Macarena", "Makarena"),
  (r"Mai", "Maj"),
  (r"mayday", "mejdej"),
  (r"Mike", "Majk"),
  (r"Monica", "Monika"),
  (r"Mulholland", "Malholand"),
  (r"Navy", "Nejwi"),
  (r"nein", "najn"),
  (r"New", "Niu"),
  (r"okay", "okej"),
  (r"Oliver", "Oliwer"),
  (r"ora", "ora"),
  (r"Oscar", "Oskar"),
  (r"P.C.", "Pi Si"),
  (r"PETA", "Peta"),
  (r"Raiden", "Rajden"),
  (r"Rapture", "Rapczer"),
  (r"Riley", "Rajli"),
  (r"Sally", "Sali"),
  (r"Scheiße", "Szajse"),
  (r"Schweinhund", "Szwajnhund"),
  (r"Seabiscuit", "Sibiskit"),
  (r"SEALS", "Sils"),
  (r"show", "szoł"),
  (r"Siam", "Sajam"),
  (r"sorry", "sory"),
  (r"SS", "es es"),
  (r"Steve", "Stiw"),
  (r"Street", "Strit"),
  (r"Stücke", "Sztyke"),
  (r"Tahoe", "Tahoł"),
  (r"Tai", "Taj"),
  (r"team", "tim"),
  (r"tengahari", "tengahari"),
  (r"tiempo", "tjempo"),
  (r"Town", "Tałn"),
  (r"Vaas", "Waas"),
  (r"Vaya", "Waja"),
  (r"Volker", "Wolker"),
  (r"Wall", "Łol"),
  (r"Willkommen", "Wilkomen"),
  (r"Willis", "Łillis"),
  (r"Ya", "Ja"),
  (r"yant", "jant"),
  (r"Yorku", "Jorku"),
  (r"zwei", "cfaj"),
  (r"Rook", "Ruk"),
  (r"Island", "ajlend"),
  (r"Doctor", "Doktor"),
  (r"Earnhardt", "Ernard"),
  (r"Earhardt", "Ernard"),
  (r"Crazy", "Krejzi"),
]

cleaner = FC3Cleaner("../subtitles/far_cry_3/subtitles.txt", "../subtitles/far_cry_3/fc3.txt")
for pattern in [r"Doctor",r"Earhardt",r"Earnhardt", r"[ ]*-",r"Crazy", r"J"]:
    cleaner.remove_voice_files_by_regex(pattern, "../dialogs/fc3")
cleaner.clean()

