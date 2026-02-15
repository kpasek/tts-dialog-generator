# 🎬 Subtitle Studio – modele lokalne

## 🧩 Instalacja i uruchamianie modelu lokalnego (XTTSv2, STylish)

Zalecane jest uruchomienie projektu w środowisku wirtualnym Pythona.

Instalacja python3.12 dla windows 10/11
```bash
winget install Python.Python.3.12
pip install virtualenv
```

Sklonuj repozytorium:
```bash
git clone https://github.com/kpasek/tts-dialog-generator.git
cd tts-dialog-generator

virtualenv -p python3.12 .venv
source .venv/bin/activate # w linuxie
.\.venv\Scripts\activate.ps1 # windows - powershell
```

Następnie zainstaluj wymagane zależności:
```bash
pip install -r requirements.txt
```

W przypadku posiadania karty NVIDIA i chęci generowania na GPU W pierwszej kolejności należy zainstalować CUDA https://developer.nvidia.com/cuda-12-9-1-download-archive Póki co obsługiwana jest wersji 12 

### UWAGA! instalacja CUDA może nadpisać aktualne sterowniki do karty graficznej!

```bash
pip uninstall torch torchvision torchaudio torchcodec
pip install torch torchaudio --index-url=https://download.pytorch.org/whl/cu129
pip install torchcodec
```

### Tylko STylish
Do katalogu `generators/stylish_model/checkpoint_final` należy pobrać wszystkie pliki z `.bin` z repozytorium twórcy modelu https://huggingface.co/spaces/FashionFlora/STylish-TTS-Pl/tree/main/checkpoint_final

Po udanej instalacji powinno się udać uruchomić model za pomocą (w wirtualnym środowisku):
```bash
python tts_api.py
```

lub uruchom skrypt
```
run_tts.bat
```

💡 Wskazówka:
Jeśli podczas instalacji pojawią się błędy, możesz je skopiować i wkleić do czatu GPT – często potrafi pomóc w ich rozwiązaniu.