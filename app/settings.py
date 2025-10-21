import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from app.tooltip import CreateToolTip

if TYPE_CHECKING:
    from app.gui import SubtitleStudioApp

DEFAULT_FILTERS = {
    "highpass": "f=70",
    "lowpass": "f=14000",
    "deesser": "i=0.4:m=0.3",
    "acompressor": "threshold=-18dB:ratio=2:attack=5:release=120:makeup=2",
    "loudnorm": "I=-16:TP=-1.5:LRA=11",
    "alimiter": "limit=-1dB"
}

FILTER_DESCRIPTIONS = {
    "highpass": "Filtr górnoprzepustowy.\nUsuwa najniższe częstotliwości (dudnienie, odgłosy 'pop').\n'f=70' oznacza odcięcie pasma poniżej 70Hz.",
    "lowpass": "Filtr dolnoprzepustowy.\nUsuwa najwyższe częstotliwości (szumy, syczenie).\n'f=14000' oznacza odcięcie pasma powyżej 14000Hz.",
    "deesser": "Redukuje sybilanty (głoski 's', 'sz', 'c').\n'i=0.4' (intensity), 'm=0.3' (mode).",
    "acompressor": "Kompresor.\nWyrównuje głośność - ścisza głośne partie i wzmacnia ciche.\n'threshold' (próg zadziałania), 'ratio' (stopień kompresji).",
    "loudnorm": "Normalizacja głośności (EBU R128).\nDopasowuje audio do standardowego poziomu głośności.\n'I=-16' (docelowa głośność), 'TP' (true peak limit).",
    "alimiter": "Limiter.\nZapobiega przesterowaniu (clippingowi), ścinając sygnał powyżej progu.\n'limit=-1dB' (ustawia 'sufit' na -1dB)."
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master: 'SubtitleStudioApp'):
        super().__init__(master)
        self.master = master
        self.title("Ustawienia")
        self.geometry("800x650")
        # =========================================================
        self.transient(master)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.tab_global = self.tabview.add("Globalne")
        self.tab_project = self.tabview.add("Projekt")

        self.global_scroll_frame = ctk.CTkScrollableFrame(self.tab_global)
        self.global_scroll_frame.pack(fill="both", expand=True)
        self.global_scroll_frame.grid_columnconfigure(1, weight=1)

        self._create_global_tab(self.global_scroll_frame)  # Przekaż ramkę
        self._create_project_tab()

        if not self.master.current_project_path:
            self.tabview.set("Globalne")
            self.tab_project.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Anuluj", command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Zapisz i Zamknij", command=self.save_and_close).pack(side="right")

    def _create_global_tab(self, frame: ctk.CTkScrollableFrame):
        # Pobierz aktualne konfiguracje
        filters_config = self.master.global_config.get('ffmpeg_filters', {})

        # --- Sekcja 1: Ustawienia Główne ---
        ctk.CTkLabel(frame, text="Ustawienia Główne", font=("", 16, "bold")).grid(row=0, column=0, columnspan=3,
                                                                                  sticky="w", padx=10, pady=(10, 5))

        # 1. Ścieżka do głosu
        ctk.CTkLabel(frame, text="Ścieżka do głosu (.wav):").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.voice_path_var = tk.StringVar(value=self.master.global_config.get('voice_path', ''))
        entry_voice = ctk.CTkEntry(frame, textvariable=self.voice_path_var)
        entry_voice.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkButton(frame, text="...", width=40, command=self.select_voice_file).grid(row=1, column=2, sticky="e",
                                                                                        padx=10, pady=10)

        # 2. Katalog startowy
        ctk.CTkLabel(frame, text="Startowy katalog:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        self.start_dir_var = tk.StringVar(value=self.master.global_config.get('start_directory', ''))
        entry_dir = ctk.CTkEntry(frame, textvariable=self.start_dir_var)
        entry_dir.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkButton(frame, text="...", width=40, command=self.select_start_dir).grid(row=2, column=2, sticky="e",
                                                                                       padx=10, pady=10)

        # --- Sekcja 2: Filtry FFmpeg ---
        ctk.CTkLabel(frame, text="Filtry Audio (FFmpeg)", font=("", 16, "bold")).grid(row=3, column=0, columnspan=3,
                                                                                      sticky="w", padx=10, pady=(20, 5))


        # 4. Ramka na wszystkie filtry
        self.filters_frame = ctk.CTkFrame(frame)
        self.filters_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        self.filters_frame.grid_columnconfigure(1, weight=1)  # Kolumna na Entry

        # 5. Dynamiczne tworzenie pól dla filtrów
        self.filter_vars = {}
        current_row = 0
        for key, default_value in DEFAULT_FILTERS.items():
            # Wczytaj zapisany stan lub użyj domyślnego
            current_filter_config = filters_config.get(key, {})
            # Domyślnie filtry są WŁĄCZONE, jeśli nie ma zapisu
            enabled = current_filter_config.get("enabled", True)
            # Wartość parametru
            params = current_filter_config.get("params", default_value)

            params_var = tk.StringVar(value=params)
            enabled_var = tk.BooleanVar(value=enabled)

            self.filter_vars[key] = (params_var, enabled_var)

            # Etykieta z Tooltipem
            lbl = ctk.CTkLabel(self.filters_frame, text=f"{key}:")
            lbl.grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
            CreateToolTip(lbl, text=FILTER_DESCRIPTIONS.get(key, "Brak opisu"), wraplength=400)

            # Pole tekstowe
            entry = ctk.CTkEntry(self.filters_frame, textvariable=params_var)
            entry.grid(row=current_row, column=1, sticky="ew", padx=10, pady=5)

            cb_enabled = ctk.CTkCheckBox(self.filters_frame, text="Włącz", variable=enabled_var)
            cb_enabled.grid(row=current_row, column=2, sticky="e", padx=10, pady=5)

            current_row += 1


    def _create_project_tab(self):
        frame = self.tab_project
        frame.grid_columnconfigure(1, weight=1)

        # 1. Bazowe przyspieszenie
        ctk.CTkLabel(frame, text="Bazowe przyspieszenie:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.base_speed_var = tk.StringVar(value=str(self.master.project_config.get('base_audio_speed', 1.1)))
        entry_speed = ctk.CTkEntry(frame, textvariable=self.base_speed_var)
        entry_speed.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkLabel(frame, text="(Domyślnie: 1.1)").grid(row=0, column=2, sticky="w", padx=10, pady=10)

    def select_voice_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik głosu .wav",
            filetypes=[("Wave files", "*.wav")],
            initialdir=self.master.global_config.get('start_directory'),
            parent=self
        )
        if path:
            self.voice_path_var.set(path)

    def select_start_dir(self):
        path = filedialog.askdirectory(
            title="Wybierz startowy katalog",
            initialdir=self.master.global_config.get('start_directory'),
            parent=self
        )
        if path:
            self.start_dir_var.set(path)

    def save_and_close(self):
        # 1. Zapisz ustawienia globalne
        try:
            old_voice_path = self.master.global_config.get('voice_path')
            new_voice_path = self.voice_path_var.get()

            ffmpeg_filters_data = {}
            for key, (params_var, enabled_var) in self.filter_vars.items():
                ffmpeg_filters_data[key] = {
                    "enabled": enabled_var.get(),
                    "params": params_var.get()
                }

            global_data = {
                'voice_path': new_voice_path,
                'start_directory': self.start_dir_var.get(),
                # === ZMIANA: Usunięto 'filters_enabled' ===
                'ffmpeg_filters': ffmpeg_filters_data
            }
            self.master.save_global_config(global_data)

            if old_voice_path != new_voice_path:
                self.master.tts_model = None
                print("Wyczyszczono cache modelu TTS z powodu zmiany głosu.")

        except Exception as e:
            messagebox.showerror("Błąd zapisu globalnego", f"Nie udało się zapisać ustawień globalnych:\n{e}",
                                 parent=self)
            return

        # 2. Zapisz ustawienia projektu (jeśli jest otwarty)
        if self.master.current_project_path:
            try:
                speed_str = self.base_speed_var.get().replace(',', '.')
                speed = float(speed_str)
                self.master.set_project_config('base_audio_speed', speed)
            except ValueError:
                messagebox.showerror("Błędna wartość", "Bazowe przyspieszenie musi być liczbą (np. 1.1).", parent=self)
                return
            except Exception as e:
                messagebox.showerror("Błąd zapisu projektu", f"Nie udało się zapisać ustawień projektu:\n{e}",
                                     parent=self)
                return

        self.destroy()