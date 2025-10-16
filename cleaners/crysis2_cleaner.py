from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class Crysis2Cleaner(Cleaner):
    def __init__(self, input_file: str = 'input.txt', output_file: str | None = 'output.txt'):
        super().__init__(input_file, output_file)

    def clean_line(self, line: str) -> str:
        line = re.sub(r".*[tT]rigge[rd].*", "", line)
        return super().clean_line(line)


    def get_patterns(self):
        return [
            (r"Angeles", "Andżeles"),
            (r"Barclay", "Barklej"),
            (r"Barnes", "Barns"),
            (r"Broadway", "Brodłej"),
            (r"Carren", "Karen"),
            (r"Central", "Sentral"),
            (r"Charlie", "Czarli"),
            (r"Chicago", "Czikago"),
            (r"Chino", "Czino"),
            (r"CIA", "Si-Aj-Ej"),
            (r"CryNet", "Krajnet"),
            (r"Dickerson", "Dikerson"),
            (r"Force", "Fors"),
            (r"Francisco", "Francisko"),
            (r"GPS", "Dżi-Pi-Es"),
            (r"Gould", "Guld"),
            (r"Greenwich", "Grinłicz"),
            (r"Hargreave", "Hargriw"),
            (r"Hendrix", "Hendriks"),
            (r"Hicks", "Hiks"),
            (r"Jack", "Dżak"),
            (r"Jacob", "Dżejkob"),
            (r"Jeff", "Dżef"),
            (r"Joe", "Dżo"),
            (r"Lancaster", "Lankaster"),
            (r"Laurence", "Lorens"),
            (r"Life", "Lajf"),
            (r"Lights", "Lajts"),
            (r"Lingshan", "Lingszan"),
            (r"Lockhart", "Lokhart"),
            (r"Manhattan", "Manhatan"),
            (r"marines", "marins"),
            (r"Max", "Maks"),
            (r"McGuire", "MakGłajer"),
            (r"McMullen", "Makmulen"),
            (r"Mitchell", "Miczel"),
            (r"Navy", "Nejwi"),
            (r"New", "Niu"),
            (r"Newton", "Niuton"),
            (r"ONYX", "Oniks"),
            (r"Queensboro", "Kłinsboro"),
            (r"Rainer", "Rajner"),
            (r"Rasch", "Rasz"),
            (r"Reeves", "Riwz"),
            (r"Roosevelt", "Ruzwelt"),
            (r"SEALs", "Sils"),
            (r"Sherman", "Szerman"),
            (r"Station", "Stejszyn"),
            (r"Street", "Strit"),
            (r"Strickland", "Strikland"),
            (r"Torres", "Tores"),
            (r"Tramarovax", "Tramarowaks"),
            (r"Village", "Wilidż"),
            (r"Wall", "Łol"),
            (r"York", "Jork"),
            (r"2020", "dwutysięcznego dwudziestego"),
        ]


# cleaner = Crysis2Cleaner("../subtitles/crysis2/subtitles.txt", "../subtitles/crysis2/crysis2.txt")
# for pattern in cleaner.get_patterns():
#     cleaner.remove_voice_files_by_regex(pattern, "../dialogs/asterix")
# cleaner.clean()
# def skroc_tekst(line: str) -> str:
#     return ((line[:85]) if len(line) > 85 else line).rstrip("\n")




# c = Cleaner("../subtitles/crysis2/crysis2_subtitles.txt", "../subtitles/crysis2/crysis2_subtitles2.txt")
# c.process_file(skroc_tekst)
