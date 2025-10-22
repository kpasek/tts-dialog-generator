# 🎬 Subtitle Studio

**Subtitle Studio** to narzędzie desktopowe (Python + CustomTkinter) do czyszczenia, przetwarzania i zarządzania napisami dialogowymi w grach i projektach lektorskich.  
Aplikacja została zaprojektowana z myślą o prostocie obsługi oraz integracji z narzędziami TTS / dubbingu.

---

## ⚙️ Wymagania techniczne

- **Python 3.10+**
- Zależności (instalacja):  
  ```bash
  pip install -r requirements.txt


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

## 🚀 Funkcje główne

### 🧹 1. Czyszczenie napisów
- Usuń zbędne elementy z plików `.txt` (np. znaczniki `[NPC]`, `<html>`, `{TAGI}` itp.)
- Używaj **wbudowanych filtrów** lub definiuj własne wyrażenia regularne.
- Podgląd zmian w czasie rzeczywistym.
- Eksportuj oczyszczone napisy jako:
  - Napisy dla **Game Readera**,
  - Napisy dla **TTS (Text-to-Speech)**.

---

### 🔄 2. Własne wzorce
- Dodawaj własne **reguły zamiany i usuwania tekstu**.
- Możesz zaimportować wzorce z pliku `.csv`.
- Każdy wzorzec obsługuje:
  - wyrażenie regularne (`regex`),
  - tekst zastępczy (`replace`),
  - opcję rozróżniania wielkości liter (`Aa`).

---

### 💬 3. Przeglądanie dialogów
Po przetworzeniu napisów możesz:
- Otworzyć **okno podglądu dialogów** (`Dialogi → Przeglądaj dialogi`),
- W lewej kolumnie przeglądać listę wszystkich linii dialogowych (z wyszukiwaniem),
- W prawej części widzieć przypisane pliki audio dla każdej linii.

#### 💡 Możliwości:
- Dwuklik na dialog → natychmiastowe odtworzenie pierwszego przypisanego pliku audio,  
- Odtwarzanie plików `.wav` / `.ogg` z poziomu aplikacji,  
- Wybór katalogu audio,  
- Usuwanie pojedynczych lub wszystkich plików,  
- Placeholder do generowania brakujących nagrań (np. z TTS).  

---

### 🧩 4. System projektów
- Wszystkie ustawienia możesz zapisać jako projekt `.json`.  
- Projekt przechowuje:
  - aktywne filtry i reguły,
  - ścieżkę do pliku z napisami,
  - katalog audio.  
- Przy kolejnym uruchomieniu aplikacja automatycznie ładuje ostatni projekt.

---

## 🖼️ Przykładowy workflow

1. **Wczytaj plik napisów**
   - Menu: `Projekt → Otwórz projekt` lub przycisk **Wczytaj**.
2. **Zastosuj filtry i wzorce**
   - Wybierz, które wzorce mają być aktywne.
   - Kliknij **Zastosuj**.
3. **Podgląd wyników**
   - Po prawej stronie zobaczysz przetworzone dialogi.
   - Możesz wyszukiwać po słowach kluczowych.
4. **Zapisz efekt**
   - `Pobierz - napisy dla Game Reader`  
     → wersja “czysta”, gotowa do użycia w grze.
   - `Pobierz - napisy dla TTS`  
     → wersja z poprawkami dla syntezatora mowy.
5. **Przeglądaj dialogi i pliki audio**
   - Menu: `Dialogi → Przeglądaj dialogi`
   - Sprawdź, które dialogi mają przypisane pliki `.wav / .ogg`.

---

## 🧠 Przykłady użycia

### 🔸 Przykład 1: Czyszczenie znaczników z napisów
**Wejście:**

`[NPC] <em>Hecat</em>: Welcome to the city!`

**Reguły aktywne:**
- Usuń zawartość w `[]`
- Usuń zawartość w `<>`

**Wynik:**

`Hecat: Welcome to the city!`

---

### 🔸 Przykład 2: Zamiana znaków specjalnych
**Wejście:**

`Hello?!?!`

**Reguły aktywne:**
- `?!` → `?`
- `?{2,}` → `?`

**Wynik:**

`Hello?`


---

### 🔸 Przykład 3: Przegląd dialogów z plikami audio

| Dialog ID | Tekst dialogu              | Pliki audio                            |
|------------|----------------------------|----------------------------------------|
| 001        | Hello, traveler!          | `output1 (1).ogg`, `ready/output1 (1).ogg` |
| 002        | Welcome to the guild.     | *(Brak plików — przycisk Generuj)*     |

---
