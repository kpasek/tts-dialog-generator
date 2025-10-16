from cleaners.cleaner import Cleaner
from cleaners.crysis1_cleaner import Crysis1Cleaner
from cleaners.crysis2_cleaner import Crysis2Cleaner
from cleaners.crysis3_cleaner import Crysis3Cleaner
from cleaners.da3_cleaner import DA3Cleaner
from cleaners.hogwart_cleaner import HLCleaner

if __name__ == "__main__":
    # cleaner = HLCleaner("dialogs_hogwart/dialogs_hl_ready.txt", 'dialogs_hogwart/dialogs_hl_clean_tts.txt')
    #
    # for pattern, replacement in cleaner.patterns:
    #     cleaner.remove_voice_files_by_regex(pattern, "voices_hl_tts")

    # cleaner.remove_voice_files_by_regex(r"Harlow", 'voices_hl_tts')
    
    # cleaner = Crysis1Cleaner("subtitles\\crysis1\\subtitles_raw.txt", "subtitles\\crysis1\\crysis1.txt")
    # cleaner.clean()
    # cleaner = Crysis2Cleaner("subtitles\\crysis2\\subtitles_raw.txt", "subtitles\\crysis2\\crysis2.txt")
    # cleaner.clean()
    
    # cleaner = Crysis3Cleaner("subtitles\\crysis3\\subtitles.txt", "subtitles\\crysis3\\crysis3.txt")
    # cleaner.clean()
    
    cleaner = DA3Cleaner("subtitles/dragon_age_3/dialogs_da3_ready.txt", "subtitles/dragon_age_3/da3.txt")
# for pattern, replace in cleaner.get_patterns():
#     cleaner.remove_voice_files_by_regex(pattern, "../dialogs/fc3")
    cleaner.clean()
    



