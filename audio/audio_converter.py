from pydub import AudioSegment
import os
from concurrent.futures import ProcessPoolExecutor as Executor
import math
from typing import Dict, Optional, Any


class AudioConverter:
    """
    Handles audio conversion, applying speed changes and FFmpeg filters.
    """

    def __init__(self, base_speed: float = 1.1, filter_settings: Optional[Dict[str, Any]] = None):
        """
        Initializes the converter.

        Args:
            base_speed: The base speed multiplier for audio (e.g., 1.1).
            filter_settings: A dictionary of filter configurations from global settings.
        """
        self.base_speed = base_speed
        self.filter_settings = filter_settings if filter_settings is not None else {}

        print(f"AudioConverter zainicjowany z bazową prędkością: {self.base_speed}")
        print(f"Ustawienia filtrów: {self.filter_settings}")

    def calculate_base_speed(self, duration_ms: float) -> float:
        """
        Calculates a dynamic speed multiplier based on audio duration.
        Longer files are sped up slightly more.

        Args:
            duration_ms: The duration of the audio in milliseconds.

        Returns:
            The calculated speed multiplier.
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
        Converts a single audio file (.wav, .mp3, .ogg) to two .ogg files
        in the /ready/ directory (output1 and output2) with filters applied.

        Args:
            input_file: Path to the source audio file.
            output_file: Path for the 'output1' (base speed) .ogg file.
        """

        input_filename = os.path.basename(input_file)
        input_dir = os.path.dirname(output_file)

        base_name_match = os.path.splitext(input_filename)[0]
        if base_name_match.startswith("output1 "):
            base_name = base_name_match[8:]
        else:
            base_name = base_name_match

        output_path_speed = os.path.join(
            input_dir, f"output2 {base_name}.ogg")

        if os.path.exists(output_path_speed) and os.path.exists(output_file):
            return

        print(f"Przetwarzam: {input_file} -> {output_file}")

        try:
            # Pydub radzi sobie z różnymi formatami na wejściu
            if input_file.lower().endswith('.ogg'):
                audio = AudioSegment.from_ogg(input_file)
            elif input_file.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(input_file)
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
        Exports an AudioSegment to a temporary .ogg file, then runs FFmpeg
        to apply filters and speed changes, saving the final .ogg file.

        Args:
            audio: The Pydub AudioSegment.
            output_file: The final destination path for the .ogg file.
            speed: The speed multiplier (atempo) to apply.
        """
        temp_file = output_file + ".temp.ogg"
        # Eksportuj do ogg (pydub użyje libvorbis)
        audio.export(temp_file, format="ogg")

        filter_list = []
        filter_order = ['highpass', 'lowpass', 'deesser', 'acompressor', 'loudnorm', 'alimiter']

        for filter_name in filter_order:
            config = self.filter_settings.get(filter_name)
            if config and config.get("enabled", False):
                params = config.get("params")
                if params:
                    filter_list.append(f"{filter_name}={params}")

        filter_str = ",".join(filter_list)
        speed_filter = f"atempo={speed}" if speed != 1.0 else ""

        if filter_str and speed_filter:
            final_filter_chain = f"{filter_str},{speed_filter}"
        elif filter_str:
            final_filter_chain = filter_str
        elif speed_filter:
            final_filter_chain = speed_filter
        else:
            final_filter_chain = ""

        if final_filter_chain:
            # Użyj -c:a libvorbis dla pewności, chociaż ffmpeg powinien to wykryć
            command = f'ffmpeg -i "{temp_file}" -af "{final_filter_chain}" -c:a libvorbis -y -loglevel error "{output_file}"'
        else:
            # Jeśli nie ma filtrów, po prostu skopiuj plik (szybciej)
            command = f'ffmpeg -i "{temp_file}" -c copy -y -loglevel error "{output_file}"'

        os.system(command)

        try:
            os.remove(temp_file)
        except Exception as e:
            print(f"Ostrzeżenie: Nie udało się usunąć pliku tymczasowego {temp_file}: {e}")

    def convert_dir(self, audio_dir: str, output_dir: str):
        """
        Converts all audio files in `audio_dir` (excluding /ready/)
        and saves them to `output_dir` using a process pool.

        Args:
            audio_dir: Source directory with raw .wav/.mp3/.ogg files.
            output_dir: Target directory (usually '.../ready/').
        """
        tasks_ogg = []
        os.makedirs(output_dir, exist_ok=True)

        with Executor(max_workers=os.cpu_count()) as executor:
            for filename in os.listdir(audio_dir):
                if filename.lower().endswith((".wav", ".ogg", ".mp3")):
                    if filename.lower().endswith(".temp.ogg"):
                        continue

                    input_path = os.path.join(audio_dir, filename)
                    output_path_ogg = self.build_output_file_path(filename, output_dir)

                    tasks_ogg.append(executor.submit(
                        self.parse_ogg, input_path, output_path_ogg))

            for task_ogg in tasks_ogg:
                task_ogg.result()

        print(f"✅ Zakończono przetwarzanie wszystkich plików audio dla {audio_dir}")

    def build_output_file_path(self, filename: str, output_dir: str) -> str:
        """
        Constructs the standard 'output1 (ID).ogg' path.

        Args:
            filename: The source filename (e.g., "output1 (123).wav").
            output_dir: The target directory.

        Returns:
            The full path for the 'output1' file.
        """
        base_name_match = os.path.splitext(filename)[0]
        if base_name_match.startswith("output1 "):
            base_name = base_name_match[8:]
        else:
            base_name = base_name_match

        output_file_name = f"output1 {base_name}.ogg"
        output_path_ogg = os.path.join(output_dir, output_file_name)
        return output_path_ogg