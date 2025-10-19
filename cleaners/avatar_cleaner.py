from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re
import os
import csv


class AvatarCleaner(Cleaner):
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        super().__init__(input_file, output_file)

    def clean_line(self, line: str) -> str:
        line = re.sub(r"<[^>]*>", " ", line)
        line = re.sub(r"^ARGH\!$", "", line)

        return super().clean_line(line)

    def get_patterns(self):
        return [
            (r"Na’vi", "Nawi"),
            (r"Na'vi", "Nawi"),
            (r"Buuuum", "Bum"),
            (r"Meh", "Me"),
            (r"Blech", "Ble"),
            (r"Eyw", "Ejł"),
            (r"So'lek", "Solek"),
            (r"Hajira", "Hadżira"),
            (r"Ri'nel", "Rinel"),
            (r"Teylan", "Tejlan"),
            (r"tsahìk", "cahik"),
            (r"ma'yawntu", "majantu"),
            (r"olo’eyktan", "olo’ejktan"),
            (r"niktsyey", "niksyjej"),
            (r"Ka'nat", "Kanat"),
            (r"Priya", "Prija"),
            (r"ZPZ", "Zet'Pe'Zet", False),
            (r"Mercer", "Merser"),
            (r"TAP", "Tap", False),
            (r"SID", "Sid", False),
            (r"Jake", "Dżejk"),
            (r"Billy", "Billi"),
            (r"Jin-Young", "Dżin-Jang"),
            (r"MacKay", "Makaj"),
            (r"John", "Dżon"),
            (r"Angela", "Andżela"),
            (r"Louis", "Luis"),
            (r"Lucą", "Luka"),
            (r"Kady", "Kadi"),
            (r"Winslow", "Łinsloł"),
            (r"Alexander", "Aleksander"),
            (r"Ewan", "Iłan"),
            (r"McStravick", "Makstrawik"),
            (r"Shanaya", "Szanaja"),
            (r"Levin", "Lewin"),
            (r"Clarke'a", "Klarka"),
            (r"Jonesy", "Dżonsi"),
            (r"Mickeyu", "Miki"),
            (r"Charlie", "Czarli"),
            (r"Foxtrot", "Fokstrot"),
            (r"Johnsona", "Dżonsona"),
            (r"Etuwa", "Etuła"),
            (r"Zomey", "Zomej"),
            (r"Ka'natowi", "Kanatowi"),
            (r"Vefilu", "Wefilu"),
            (r"Eetu", "Etu"),
            (r"ma 'eylan", "ma ejlan"),
            (r"P'asuk", "Pasuk"),
            (r"yavä'", "jawa"),
            (r"Vu'an", "Wuan"),
            (r"Neytu", "Nejtu"),
            (r"Anqa", "Anka"),
            (r"Tu'kari", "Tukari"),
            (r"Minang", "Minang"),
            (r"Kin", "Kin"),
            (r"Woai", "Łoaj"),
            (r"tsamsiyu", "camsiju"),
            (r"zangke", "zangke"),
            (r"Ko'akte", "Koakte"),
            (r"Akoray", "Akoraj"),
            (r"Cortez", "Kortez"),
            (r"Aha'ri", "Ahari"),
            (r"Manwe", "Manłe"),
            (r"Ey'teko", "Ejteko"),
            (r"Carol", "Karol"),
            (r"Amay", "Amaj"),
            (r"Fa'zak", "Fazak"),
            (r"Tsu'kiri", "Cukiri"),
            (r"Kayì", "Kaji"),
            (r"Dani", "Dani"),
            (r"Jin", "Dżin"),
            (r"Faiu", "Faju"),
            (r"Novao", "Nowao"),
            (r"Nìwin", "Niłin"),
            (r"Hawm", "Hałm"),
            (r"Ongwi", "Ongłi"),
            (r"Ley'taw", "Lejtał"),
            (r"Aleymun", "Alejmun"),
            (r"Neyan", "Nejan"),
            (r"Lurei", "Lurej"),
            (r"Heykinak", "Hejkinak"),
            (r"Mayday", "Mejdej"),
            (r"Alex", "Aleks"),
            (r"Shanayo", "Szanajo"),
            (r"Reyzu", "Rejzu"),
            (r"Sa'nop", "Sanop"),
            (r"Eylanay", "Ejlanaj"),
            (r"Eywafi", "Ejwafi"),
            (r"PZM", "pe'zet'em", False),
            (r"AD", "a'de", False),
            (r"MTR", "em'te'er", False),
            (r"CO2", "ce'o'dwa", False),
            (r"GAU", "ge'a'u", False),
            (r"TBM", "te'be'em", False),
            (r"VSM", "v'es'em", False),
            (r"ACA", "a'ce'a", False),
            (r"RFID", "er'ef'aj'di", False),
        ]

    def first_run(self):
        with open(self.input_file) as csvfile, open(str(self.output_file), "w") as outfile:
            lines = []
            reader = csv.reader(csvfile)
            for row in reader:
                line = row[5] or None
                if line and line not in lines:
                    lines.append(line)

            for line in lines:
                outfile.write(line + "\n")
