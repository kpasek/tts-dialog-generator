# 🎬 Subtitle Studio

**Subtitle Studio** to narzędzie desktopowe (Python + CustomTkinter) do czyszczenia, przetwarzania i zarządzania napisami dialogowymi w grach i projektach lektorskich.  
Aplikacja została zaprojektowana z myślą o prostocie obsługi oraz integracji z narzędziami TTS / dubbingu.

---

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

## ⚙️ Wymagania techniczne

- **Python 3.10+**
- Zależności (instalacja):  
  ```bash
  pip install -r requirements.txt
