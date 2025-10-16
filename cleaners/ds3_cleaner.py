from cleaners.cleaner import Cleaner
import xml.etree.ElementTree as ET
import re, os


class DS3Cleaner(Cleaner):
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
            (r"Hugh", "Hju"),
            (r"Montbarron", "Montbaron"),
            (r"Guiscard", "Giskard"),
            (r"Stephan", "Stefan"),
            (r"dakkenweyrach", "dakenwerach"),
            (r"Lescanzi", "Leskanzi"),
            (r"Meister", "Majster"),
            (r"Rajani", "Radżani"),
            (r"Jeyne", "Dżejni"),
            (r"Kassynder", "Kasynder"),
            (r"Archambaud", "Arszambo"),
            (r"Payen", "Pejen"),
            (r"Wulf", "Wulf"),
            (r"Kassel", "Kasel"),
            (r"Fiddlewick", "Fidylłik"),
            (r"Bassili", "Basili"),
            (r"Leona", "Leona"),
            (r"Roslyn", "Roslin"),
            (r"Devonsey", "Dewonsej"),
            (r"Saraya", "Saraja"),
            (r"Mudgutter", "Madgater"),
            (r"Synod", "Synod"),
            (r"Bisselbergu", "Biselbergu"),
            (r"Dungeon", "Dandżen"),
            (r"Siege", "Sidż"),
            (r"déja", "deża"),
            (r"vu", "wi"),
            (r"Lucas", "Lukas"),
            (r"Anjali", "Andżali"),
            (r"Merika", "Merika"),
            (r"Giles", "Dżajls"),
            (r"Reynald", "Rejnald"),
            (r"Boris", "Boris"),
            (r"Ottokar", "Otokar"),
            (r"Armand", "Armand"),
            (r"Blanc", "Blank"),
            (r"Crespina", "Krespina"),
            (r"Tatyana", "Tatiana"),
            (r"Vaclav", "Wacław"),
            (r"Florinowi", "Florinowi"),
            (r"Yacobie", "Jakobie"),
            (r"Hiramowi", "Hiramowi"),
            (r"vodyanoi", "wodianoj"),
            (r"Bohemund", "Boemund"),
            (r"Garin", "Garin"),
            (r"Marcel", "Marsel"),
            (r"Stonebridge", "Stonbridż"),
            (r"Glitterdelve", "Gliterdelw"),
            (r"Mournweald", "Mornłeld"),
            (r"Hearthfire", "Hartfajer"),
            (r"Phineas", "Fineas"),
            (r"Roderickiem", "Roderikiem"),
            (r"Digglefitz", "Digylfic"),
            (r"Arah", "Ara"),
            (r"Maru-yatum", "Maru-jatum"),
            (r"Maru-yatuma", "Maru-jatuma"),
            (r"Maru-yatumowi", "Maru-jatumowi"),
            (r"Abi-eshu", "Abi-eszu"),
            (r"Abi-Eshu", "Abi-Eszu"),
            (r"Sweatcog", "Słitkog"),
            (r"Grimmelhausowi", "Grimelhausowi"),
            (r"Reinhart", "Rajnhart"),
            (r"Manx", "Manks"),
            (r"Giseli", "Gizeli"),
            (r"Rorik", "Rorik"),
            (r"Snellem", "Snelem"),
            (r"Ergometheusa", "Ergometeusa"),
            (r"Wenzel", "Wencel"),
            (r"Frederica", "Frederika"),
            (r"Pratza", "Praca"),
            (r"Rudolf", "Rudolf"),
            (r"Maxwell", "Maksłel"),
            (r"Sigismundem", "Zigismundem"),
            (r"Gibberghast", "Gibergast"),
            (r"Septimus", "Septimus"),
            (r"Numeriusz", "Numeriusz"),
            (r"Tyberia", "Tyberia"),
            (r"Varus", "Warus"),
            (r"Azunai", "Azunaj"),
            (r"Azunaia", "Azunaja"),
            (r"Azunaiowi", "Azunajowi"),
            (r"Zaramoth", "Zaramot"),
            (r"Etienne", "Etien"),
            (r"Marnaya", "Marneja"),
            (r"Aridai", "Aridaj"),
            (r"Zakkaeusa", "Zakeusa"),
            (r"Marlowe'a", "Marloła"),
            (r"Jenna", "Dżena"),
            (r"Corneliusie", "Korneliusie"),
            (r"Molochi", "Moloki"),
            (r"Hathra'unoka", "Hatraunoka"),
            (r"Jabberhacka", "Dżaberhaka"),
            (r"Svarbog", "Swarbog"),
            (r"Zarii", "Zarii"),
            (r"Schnaus", "Sznaus"),
            (r"Gunter", "Gunter"),
            (r"Holtzman", "Holcman"),
            (r"Fitcha", "Ficza"),
            (r"Ibsenem", "Ibsenem"),
            (r"Yamas", "Jamas"),
            (r"Aegis", "Edżis"),
            (r"Bay", "Bej"),
            (r"Jhereb", "Dżereb"),
            (r"10\. Legionu", "dziesiątego Legionu"),
            (r"10\. Legion", "dziesiątym Legion"),
            (r"Rukkenvahl", "Rukenwal"),
            (r"pl_[\d]+", " "),
        ]


# cleaner = DS3Cleaner('../dialogs_DS3/global/strings/characters.xml', "../dialogs_DS3/names.txt")
# cleaner.extract("../dialogs_DS3/global/strings/characters.xml")

cleaner = DS3Cleaner("../subtitles/dungeon_siege_3/subtitles.txt", "../subtitles/dungeon_siege_3/ds3_ready.txt")
cleaner.clean()

