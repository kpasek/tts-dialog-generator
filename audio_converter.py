from pydub import AudioSegment, effects, silence
import os
from concurrent.futures import ProcessPoolExecutor as Executor
import math


class AudioConverter:

    def calculate_base_speed(self, duration_ms: float) -> float:
        """
        Zwraca współczynnik przyspieszenia w zależności od długości audio.
        - Do 3 sekund: bez zmian (1.0)
        - Powyżej 3 sekund: każde 2 sekundy -> +2% szybkości
        """
        duration_sec = duration_ms / 1000
        if duration_sec < 2:
            return 1.0
        base_speed = 1.0
        if duration_sec <= 3:
            return base_speed
        extra_time = duration_sec - 3
        speed_factor = base_speed + (1.02 * math.ceil(extra_time / 2))
        return min(speed_factor, base_speed * 1.2)

    def parse_ogg(self, input_file: str, output_file: str):
        """
        input_file: ścieżka do pliku wejściowego .wav
        output_file: ścieżka do pliku wyjściowego .wav
        silence_thresh: próg ciszy w dBFS (np. -40 oznacza ciszę poniżej -40 dB)
        keep_silence: ile ms ciszy zostawić przy cięciu
        max_silence: maksymalna długość ciszy do pozostawienia w ms
        """

        input_filename = os.path.basename(input_file)
        input_dir = os.path.dirname(output_file)
        output_path_speed = os.path.join(
            input_dir, "output2 " + input_filename[8:-4] + ".ogg")
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

        filters = (
            "highpass=f=70,"
            "lowpass=f=14000,"
            "deesser=i=0.4:m=0.3,"
            "acompressor=threshold=-18dB:ratio=2:attack=5:release=120:makeup=2,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,"
            "alimiter=limit=-1dB,"
        )

        filter_str = str(filters).strip(',')

        speed_filter = f",atempo={speed}" if speed != 1.0 else ""

        command = f'ffmpeg -i "{temp_file}" -af "{filter_str}{speed_filter}" -y -loglevel error "{output_file}"'
        os.system(command)
        os.remove(temp_file)

    def convert_audio(self):
        for audio_dir in os.listdir("dialogs"):
            audio_dir = os.path.abspath(os.path.join("dialogs", audio_dir))
            if not os.path.isdir(audio_dir):
                continue
            output_dir = os.path.join(audio_dir, "ready")

            self.convert_dir(audio_dir, output_dir)

    def convert_dir(self, audio_dir: str, output_dir: str):
        tasks_ogg = []
        os.makedirs(output_dir, exist_ok=True)

        with Executor(max_workers=os.cpu_count()) as executor:
            for filename in os.listdir(audio_dir):
                if filename.lower().endswith(".wav") or filename.lower().endswith(".ogg"):
                    input_path = os.path.join(audio_dir, filename)
                    ogg_file = filename[:-4] + ".ogg"
                    output_path_ogg = os.path.join(output_dir, ogg_file)

                    tasks_ogg.append(executor.submit(
                        self.parse_ogg, input_path, output_path_ogg))

            for task_ogg in tasks_ogg:
                task_ogg.result()

        print(
            f"✅ Zakończono przetwarzanie wszystkich plików audio dla {audio_dir}")


if __name__ == "__main__":

    c = AudioConverter()
    c.convert_audio()
    # c.convert_dir("dialogs/fc3","dialogs/fc3/ready")
