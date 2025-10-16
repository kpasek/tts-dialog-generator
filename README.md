# 🎙️ Generator dialogów z wykorzystaniem modelu Stylish-TTS-PL

Repozytorium zawiera zestaw narzędzi do generowania głosów lektorskich w języku polskim z wykorzystaniem modelu **Stylish-TTS-PL**.  
Projekt został przygotowany z myślą o integracji z programem **Game Reader**, służącym do automatycznego odczytywania dialogów w grach.

---

## 📦 Modele referencyjne

Model STylish-TTS:  
🔗 [https://huggingface.co/FashionFlora/StylishTTS-Pl](https://huggingface.co/FashionFlora/StylishTTS-Pl)

Model XTTS_v2:  
🔗 [https://huggingface.co/coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)

---

## ⚙️ Instalacja

Zalecane jest uruchomienie projektu w środowisku wirtualnym Pythona.

```bash
virtualenv -p python3.11 .venv
source .venv/bin/activate # w linuxie
.\.venv\Scripts\activate.ps1 # windows - powershell
```

Następnie zainstaluj wymagane zależności:
```shell
pip install -r requirements.txt
```

W przypadku posiadania karty NVIDIA i chęci generowania na GPU
W pierwszej kolejności należy zainstalować CUDA
`https://developer.nvidia.com/cuda-12-9-1-download-archive`
Póki co obsługiwana jest wersji 12
    UWAGA! instalacja CUDA może nadpisać aktualne sterowniki do karty graficznej!
```shell
pip uninstall torch torchvision torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu129
```

Do katalogu `generators/stylish_model/checkpoint_final` należy przekopiować wszystkie pliki `.bin` z repozytorium twórcy modelu
`https://huggingface.co/spaces/FashionFlora/STylish-TTS-Pl/tree/main/checkpoint_final`

### 💡 Wskazówka:
Jeśli podczas instalacji pojawią się błędy, możesz je skopiować i wkleić do czatu GPT – często potrafi pomóc w ich rozwiązaniu.
## ▶️ Użycie

Do generowania głosów służą skrypty:
```shell
python stylish_generator.py # w celu skorzystania z modelu STylish
python xtts_generator.py # w celu skorzystania z modelu XTTS_v2
```

Skrypt będzie wczytywał wszystkie pliki `.txt` z katalogu `./tts_ready` a następnie wygeneruje dialogi do katalogu `dialogs/[nazwa_pliku_txt]`

Dialogi zostaną wygenerowane do nowego katalogu w postaci surowych plików `.wav`.
Po zakończeniu generacji należy uruchomić skrypt 

```shell
python audio_converter.py
``` 

który rozpocznie proces przetwarzania audio — gotowe pliki dla programu Game Reader znajdziesz w podkatalogu:

`.dialogs/[nazwa]/ready/*`

Skrypt sprawdza, które dialogi zostały już wygenerowane, i pomija istniejące pliki.
Dzięki temu możesz szybko poprawiać wybrane kwestie, po prostu usuwając błędne pliki i ponownie uruchamiając generację.

## 🧹 Czyszczenie napisów i dialogów

W katalogu `cleaners/` znajdują się klasy ułatwiające czyszczenie dialogów z niepotrzebnych fragmentów, takich jak `(kaszel)` czy `(śmiech)`.

Dodatkowo, w pliku `cleaners/cleaner.py -> remove_voice_files_by_regex` znajduje się metoda do usuwania plików audio na podstawie wyrażenia regularnego, odpowiadającego treści dialogu.

### Przykład użycia:
```python
from cleaners.cleaner import Cleaner

cleaner = Cleaner("dialogs_hogwart/hl_ready.txt")

# Masowe usuwanie dialogów według zdefiniowanych wzorców
for pattern, replacement in cleaner.patterns:
    cleaner.remove_voice_files_by_regex(pattern, "dialogs/hogwart")

# Usuwa wszystkie dialogi zawierające imię "Harlow"
cleaner.remove_voice_files_by_regex(r"Harlow", "dialogs_hl_tts")
```

## 🎧 Przetwarzanie audio (.wav → .ogg)

Do konwersji oraz przetwarzania dźwięku można użyć klasy AudioConverter.

Proces obejmuje:

    usuwanie cichych fragmentów,

    normalizację głośności,

    przyspieszenie dialogów w zależności od ich długości.

Zasada przyspieszenia:

    audio do 3 sekund – bez zmian,

    powyżej 3 s – co 2 sekundy długości zwiększają szybkość o 3%,

    maksymalne przyspieszenie: 20%,

    dodatkowo, wersja output2 jest przyspieszana o kolejne 10% względem output1.

    Przyspieszanie audio wykonywane jest przez program ffmpeg i należy mieć go zainstalowany w systemie
    Instalacja ubuntu:
    sudo apt install ffmpeg
    Instalacja Windows:
    winget install Gyan.FFmpeg
    
Przykład użycia:

```python
from audio_converter import AudioConverter

converter = AudioConverter()
# wszystkie pliki audio w katalogu dialogs/*
converter.convert_audio()
# lub
converter.convert_dir("dialogs/fc3","dialogs/fc3/ready") # ręczne ustawienie katalogu wejściowego i wyjściowego
```

Wynikowe pliki .ogg zostaną zapisane w katalogu:

`ready/*.ogg`

### 🗣️ Uwagi końcowe

    Projekt jest wciąż rozwijany – celem jest pełna automatyzacja generowania lektora dla gier.

    Przy długich sesjach generowania warto obserwować wykorzystanie GPU/CPU – model Stylish-TTS-PL potrafi być zasobożerny.

    Jeśli chcesz dodać własne reguły czyszczenia lub modyfikacji dźwięku, wystarczy rozszerzyć odpowiednie klasy w katalogu cleaners/ lub audio_converter.py.

### 📄 Licencja

Projekt udostępniany jest na licencji MIT, o ile nie zaznaczono inaczej.
Model Stylish-TTS-PL jest własnością autora z repozytorium Hugging Face i podlega jego warunkom licencyjnym.