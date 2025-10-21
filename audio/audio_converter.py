from pydub import AudioSegment
import os
from concurrent.futures import ProcessPoolExecutor as Executor
import math
from typing import Dict, Optional


class AudioConverter:

    def __init__(self, base_speed: float = 1.1, filter_settings: Optional[Dict[str, str]] = None):
        self.base_speed = base_speed
        self.filter_settings = filter_settings if filter_settings is not None else {}

        print(f"AudioConverter zainicjowany z bazową prędkością: {self.base_speed}")
        print(f"Ustawienia filtrów: {self.filter_settings}")


    def calculate_base_speed(self, duration_ms: float) -> float:
        """
        Zwraca współczynnik przyspieszenia w zależności od długości audio.
        """
        duration_sec = duration_ms / 1000
        if duration_sec < 2:
            return 1.0

        if duration_sec <= 3:
            return self.base_speed
        extra_time = duration_sec - 3
        multiplier = (0.02 * math.ceil(extra_time / 2))
        speed_factor = self.base_speed + multiplier
        return min(speed_factor, self.base_speed * 1.2)

    def parse_ogg(self, input_file: str, output_file: str):
        """
        input_file: ścieżka do pliku wejściowego .wav
        output_file: ścieżka do pliku wyjściowego .wav
        """

        input_filename = os.path.basename(input_file)
        input_dir = os.path.dirname(output_file)

        # Zakładamy, że nazwa pliku to "output1 (IDENTIFIER).wav"
        base_name_match = os.path.splitext(input_filename)[0]  # np. "output1 (123)"

        # Na wypadek gdyby nazwa była inna, próbujemy wyciąć "output1 "
        if base_name_match.startswith("output1 "):
            base_name = base_name_match[8:]  # np. "(123)"
        else:
            base_name = base_name_match  # Zachowaj co jest

        output_path_speed = os.path.join(
            input_dir, f"output2 {base_name}.ogg")

        if os.path.exists(output_path_speed) and os.path.exists(output_file):
            return

        print(f"Przetwarzam: {input_file} -> {output_file}")

        try:
            if input_file.lower().endswith('.ogg'):
                audio = AudioSegment.from_ogg(input_file)
            else:
                audio = AudioSegment.from_wav(input_file)

            base_speed = self.calculate_base_speed(len(audio))

            if not os.path.exists(output_file):
                self.export_file(audio, output_file, base_speed)

            if not os.path.exists(output_path_speed):
                speed = 1.10 if (len(audio) / 1000) > 2 else 1
                self.export_file(audio, output_path_speed, base_speed * speed)

        except Exception as e:
            print(f"Błąd podczas przetwarzania pliku {input_file}: {e}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                    print(f"Usunięto plik wyjściowy: {output_file}")
                except Exception as remove_err:
                    print(
                        f"Nie udało się usunąć pliku {output_file}: {remove_err}")

    def export_file(self, audio: AudioSegment, output_file: str, speed: float):
        """
        Eksportuje AudioSegment do pliku OGG i przepuszcza przez zestaw filtrów ffmpeg
        zoptymalizowanych pod męski głos lektora.
        """
        temp_file = output_file + ".temp.ogg"
        audio.export(temp_file, format="ogg")

        filter_str = ""

        filter_list = []
        # Ważna jest kolejność!
        filter_order = ['highpass', 'lowpass', 'deesser', 'acompressor', 'loudnorm', 'alimiter']

        for filter_name in filter_order:
            # self.filter_settings to teraz {'highpass': {'enabled': True, 'params': 'f=70'}, ...}
            config = self.filter_settings.get(filter_name)

            # Sprawdź, czy filtr istnieje ORAZ czy jest włączony
            if config and config.get("enabled", False):
                params = config.get("params")
                if params:  # Dodaj filtr tylko jeśli ma zdefiniowane parametry
                    filter_list.append(f"{filter_name}={params}")

        filter_str = ",".join(filter_list)

        speed_filter = f"atempo={speed}" if speed != 1.0 else ""

        # Połącz filtry (jeśli są) z przyspieszeniem
        if filter_str and speed_filter:
            final_filter_chain = f"{filter_str},{speed_filter}"
        elif filter_str:
            final_filter_chain = filter_str
        elif speed_filter:
            final_filter_chain = speed_filter
        else:
            final_filter_chain = ""  # Brak filtrów i brak przyspieszenia

        if final_filter_chain:
            command = f'ffmpeg -i "{temp_file}" -af "{final_filter_chain}" -y -loglevel error "{output_file}"'
        else:
            # Jeśli nie ma żadnych filtrów, po prostu skopiuj plik
            command = f'ffmpeg -i "{temp_file}" -c copy -y -loglevel error "{output_file}"'

        # print(f"Executing FFmpeg: {command}") # Do debugowania
        os.system(command)
        os.remove(temp_file)

    def convert_audio(self):
        # Ta metoda jest teraz głównie do testowania, główna logika jest w convert_dir
        for audio_dir in os.listdir("dialogs"):
            audio_dir = os.path.abspath(os.path.join("dialogs", audio_dir))
            if not os.path.isdir(audio_dir):
                continue
            output_dir = os.path.join(audio_dir, "ready")

            self.convert_dir(audio_dir, output_dir)

    def convert_dir(self, audio_dir: str, output_dir: str):
        tasks_ogg = []
        os.makedirs(output_dir, exist_ok=True)

        # Musimy przekazać instancję, aby worker znał ustawienia filtrów.
        # Robimy to, przekazując self.parse_ogg jako callable.

        with Executor(max_workers=os.cpu_count()) as executor:
            for filename in os.listdir(audio_dir):
                if filename.lower().endswith(".wav") or filename.lower().endswith(".ogg"):
                    if filename.lower().endswith(".temp.ogg"):  # Pomiń pliki tymczasowe
                        continue

                    input_path = os.path.join(audio_dir, filename)

                    base_name_match = os.path.splitext(filename)[0]
                    if base_name_match.startswith("output1 "):
                        base_name = base_name_match[8:]
                    else:
                        base_name = base_name_match

                    output_file_name = f"output1 {base_name}.ogg"
                    output_path_ogg = os.path.join(output_dir, output_file_name)

                    tasks_ogg.append(executor.submit(
                        self.parse_ogg, input_path, output_path_ogg))

            for task_ogg in tasks_ogg:
                task_ogg.result()

        print(f"✅ Zakończono przetwarzanie wszystkich plików audio dla {audio_dir}")