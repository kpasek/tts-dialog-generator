import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from app.tooltip import CreateToolTip
from app.utils import is_installed  # Import do sprawdzenia

if TYPE_CHECKING:
    from app.gui import SubtitleStudioApp

# Domyślne wartości dla filtrów
DEFAULT_FILTERS = {
    "highpass": {"enabled": True, "params": "f=70"},
    "lowpass": {"enabled": True, "params": "f=14000"},
    "deesser": {"enabled": True, "params": "i=0.4:m=0.3"},
    "acompressor": {"enabled": True, "params": "threshold=-18dB:ratio=2:attack=5:release=120:makeup=2"},
    "loudnorm": {"enabled": True, "params": "I=-16:TP=-1.5:LRA=11"},
    "alimiter": {"enabled": True, "params": "limit=-1dB"}
}

# Opisy filtrów
FILTER_DESCRIPTIONS = {
    "highpass": "Filtr górnoprzepustowy.\nUsuwa najniższe częstotliwości (dudnienie, odgłosy 'pop').\n'f=70' oznacza odcięcie pasma poniżej 70Hz.",
    "lowpass": "Filtr dolnoprzepustowy.\nUsuwa najwyższe częstotliwości (szumy, syczenie).\n'f=14000' oznacza odcięcie pasma powyżej 14000Hz.",
    "deesser": "Redukuje sybilanty (głoski 's', 'sz', 'c').\n'i=0.4' (intensity), 'm=0.3' (mode).",
    "acompressor": "Kompresor.\nWyrównuje głośność - ścisza głośne partie i wzmacnia ciche.\n'threshold' (próg zadziałania), 'ratio' (stopień kompresji).",
    "loudnorm": "Normalizacja głośności (EBU R128).\nDopasowuje audio do standardowego poziomu głośności.\n'I=-16' (docelowa głośność), 'TP' (true peak limit).",
    "alimiter": "Limiter.\nZapobiega przesterowaniu (clippingowi), ścinając sygnał powyżej progu.\n'limit=-1dB' (ustawia 'sufit' na -1dB)."
}


class SettingsWindow(ctk.CTkToplevel):
    """
    A window for managing global application settings and project-specific settings.
    """

    # === ZMIANA: Dodano torch_installed ===
    def __init__(self, master: 'SubtitleStudioApp', torch_installed: bool):
        super().__init__(master)
        self.master = master
        self.torch_installed = torch_installed
        # ===================================
        self.title("Ustawienia")
        self.geometry("800x750")  # Zwiększone okno
        self.transient(master)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.tab_global = self.tabview.add("Globalne")
        self.tab_project = self.tabview.add("Projekt")

        # --- Zakładka Globalne ---
        self.global_scroll_frame = ctk.CTkScrollableFrame(self.tab_global)
        self.global_scroll_frame.pack(fill="both", expand=True)
        self.global_scroll_frame.grid_columnconfigure(0, weight=1)

        self._create_global_tab(self.global_scroll_frame)  # Przekaż ramkę

        # --- Zakładka Projekt ---
        self.project_frame = ctk.CTkFrame(self.tab_project)
        self.project_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.project_frame.grid_columnconfigure(1, weight=1)

        self._create_project_tab(self.project_frame)

        if not self.master.current_project_path:
            self.tabview.set("Globalne")
            self.tab_project.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Anuluj", command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btn_frame, text="Zapisz i Zamknij", command=self.save_and_close).pack(side="right")

    def _create_global_tab(self, frame: ctk.CTkScrollableFrame):
        """Populates the 'Global' settings tab."""

        # --- Sekcja 1: Ustawienia Główne Aplikacji ---
        ctk.CTkLabel(frame, text="Ustawienia Główne", font=("", 16, "bold")).grid(row=0, column=0, columnspan=3,
                                                                                  sticky="w", padx=10, pady=(10, 5))
        frame_main = ctk.CTkFrame(frame)
        frame_main.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        frame_main.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_main, text="Startowy katalog:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.start_dir_var = tk.StringVar(value=self.master.global_config.get('start_directory', ''))
        entry_dir = ctk.CTkEntry(frame_main, textvariable=self.start_dir_var)
        entry_dir.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkButton(frame_main, text="...", width=40, command=self.select_start_dir).grid(row=0, column=2, sticky="e",
                                                                                            padx=10, pady=10)

        # --- Sekcja 2: Modele TTS ---
        ctk.CTkLabel(frame, text="Modele TTS", font=("", 16, "bold")).grid(row=2, column=0, columnspan=3,
                                                                           sticky="w", padx=10, pady=(15, 5))
        tts_tabview = ctk.CTkTabview(frame)
        tts_tabview.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

        # === Zakładka XTTS ===
        tab_xtts = tts_tabview.add("XTTS (Lokalny)")
        tab_xtts.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab_xtts, text="Ścieżka do głosu (.wav):").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.voice_path_var = tk.StringVar(value=self.master.global_config.get('xtts_voice_path', ''))
        entry_voice = ctk.CTkEntry(tab_xtts, textvariable=self.voice_path_var)
        entry_voice.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkButton(tab_xtts, text="...", width=40, command=self.select_voice_file).grid(row=0, column=2, sticky="e",
                                                                                           padx=10, pady=10)
        if not self.torch_installed:
            tab_xtts.configure(state="disabled")

        # === Zakładka ElevenLabs ===
        tab_eleven = tts_tabview.add("ElevenLabs (Online)")
        tab_eleven.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab_eleven, text="Klucz API:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        self.el_api_key_var = tk.StringVar(value=self.master.global_config.get('elevenlabs_api_key', ''))
        ctk.CTkEntry(tab_eleven, textvariable=self.el_api_key_var, show="*").grid(row=0, column=1, sticky="ew", padx=10,
                                                                                  pady=(10, 5))

        ctk.CTkLabel(tab_eleven, text="Voice ID:").grid(row=1, column=0, sticky="w", padx=10, pady=(5, 10))
        self.el_voice_id_var = tk.StringVar(value=self.master.global_config.get('elevenlabs_voice_id', ''))
        ctk.CTkEntry(tab_eleven, textvariable=self.el_voice_id_var).grid(row=1, column=1, sticky="ew", padx=10,
                                                                         pady=(5, 10))
        CreateToolTip(tab_eleven.winfo_children()[2], "ID głosu z Twojego konta ElevenLabs.", wraplength=300)

        # === Zakładka Google Cloud TTS ===
        tab_google = tts_tabview.add("Google Cloud TTS (Online)")
        tab_google.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab_google, text="Credentials (.json):").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.gcp_creds_var = tk.StringVar(value=self.master.global_config.get('google_credentials_path', ''))
        entry_gcp = ctk.CTkEntry(tab_google, textvariable=self.gcp_creds_var)
        entry_gcp.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
        ctk.CTkButton(tab_google, text="...", width=40, command=self.select_gcp_creds).grid(row=0, column=2, sticky="e",
                                                                                            padx=10, pady=10)

        ctk.CTkLabel(tab_google, text="Nazwa głosu:").grid(row=1, column=0, sticky="w", padx=10, pady=(5, 10))
        self.gcp_voice_name_var = tk.StringVar(
            value=self.master.global_config.get('google_voice_name', 'pl-PL-Wavenet-B'))
        ctk.CTkEntry(tab_google, textvariable=self.gcp_voice_name_var).grid(row=1, column=1, sticky="ew", padx=10,
                                                                            pady=(5, 10))
        CreateToolTip(tab_google.winfo_children()[3], "Np. pl-PL-Wavenet-B (męski) lub pl-PL-Wavenet-C (damski)",
                      wraplength=300)

        # --- Sekcja 3: Filtry FFmpeg ---
        ctk.CTkLabel(frame, text="Filtry Audio (FFmpeg)", font=("", 16, "bold")).grid(row=4, column=0, columnspan=3,
                                                                                      sticky="w", padx=10, pady=(20, 5))
        self.filters_frame = ctk.CTkFrame(frame)
        self.filters_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        self.filters_frame.grid_columnconfigure(1, weight=1)  # Kolumna na Entry

        self.filter_vars = {}
        current_row = 0

        # Wczytaj filtry z configu lub użyj domyślnych
        filters_config = self.master.global_config.get('ffmpeg_filters', DEFAULT_FILTERS)

        for key, default_config in DEFAULT_FILTERS.items():
            current_config = filters_config.get(key, default_config)
            enabled = current_config.get("enabled", True)
            params = current_config.get("params", default_config["params"])

            params_var = tk.StringVar(value=params)
            enabled_var = tk.BooleanVar(value=enabled)
            self.filter_vars[key] = (params_var, enabled_var)

            lbl = ctk.CTkLabel(self.filters_frame, text=f"{key}:")
            lbl.grid(row=current_row, column=0, sticky="w", padx=10, pady=5)
            CreateToolTip(lbl, text=FILTER_DESCRIPTIONS.get(key, "Brak opisu"), wraplength=400)

            entry = ctk.CTkEntry(self.filters_frame, textvariable=params_var)
            entry.grid(row=current_row, column=1, sticky="ew", padx=10, pady=5)

            cb_enabled = ctk.CTkCheckBox(self.filters_frame, text="Włącz", variable=enabled_var)
            cb_enabled.grid(row=current_row, column=2, sticky="e", padx=10, pady=5)

            current_row += 1

    def _create_project_tab(self, frame: ctk.CTkFrame):
        """Populates the 'Project' settings tab."""

        # --- Sekcja 1: Ustawienia Projektu ---
        ctk.CTkLabel(frame, text="Ustawienia Projektu", font=("", 16, "bold")).grid(row=0, column=0, columnspan=3,
                                                                                    sticky="w", padx=10, pady=(10, 5))

        # 1. Bazowe przyspieszenie
        ctk.CTkLabel(frame, text="Bazowe przyspieszenie:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.base_speed_var = tk.StringVar(value=str(self.master.project_config.get('base_audio_speed', 1.1)))
        entry_speed = ctk.CTkEntry(frame, textvariable=self.base_speed_var)
        entry_speed.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=10)
        CreateToolTip(entry_speed, "Domyślna prędkość dla audio (np. 1.1 = 10% szybciej).", wraplength=300)

        # 2. Wybór modelu TTS
        ctk.CTkLabel(frame, text="Aktywny model TTS:").grid(row=2, column=0, sticky="w", padx=10, pady=10)

        # === ZMIANA: Dynamiczna lista modeli ===
        available_models = []
        if self.torch_installed:
            available_models.append("XTTS")
        available_models.extend(["ElevenLabs", "Google Cloud TTS"])

        # Ustaw domyślny, jeśli zapisany jest niedostępny
        saved_model = self.master.project_config.get('active_tts_model')
        if saved_model not in available_models:
            saved_model = available_models[0]  # Wybierz pierwszy dostępny
        # ======================================

        self.active_model_var = tk.StringVar(value=saved_model)
        model_menu = ctk.CTkOptionMenu(frame, variable=self.active_model_var, values=available_models)
        model_menu.grid(row=2, column=1, sticky="w", padx=10, pady=10)
        CreateToolTip(model_menu, "Wybierz model, który będzie używany do generowania audio w tym projekcie.",
                      wraplength=300)

    def select_voice_file(self):
        """Opens a file dialog to select the XTTS .wav voice file."""
        path = filedialog.askopenfilename(
            title="Wybierz plik głosu .wav",
            filetypes=[("Wave files", "*.wav")],
            initialdir=self.master.global_config.get('start_directory'),
            parent=self
        )
        if path:
            self.voice_path_var.set(path)

    def select_gcp_creds(self):
        """Opens a file dialog to select the Google Cloud .json credentials file."""
        path = filedialog.askopenfilename(
            title="Wybierz plik credentials .json",
            filetypes=[("JSON files", "*.json")],
            initialdir=self.master.global_config.get('start_directory'),
            parent=self
        )
        if path:
            self.gcp_creds_var.set(path)

    def select_start_dir(self):
        """Opens a directory dialog to select the default starting directory."""
        path = filedialog.askdirectory(
            title="Wybierz startowy katalog",
            initialdir=self.master.global_config.get('start_directory'),
            parent=self
        )
        if path:
            self.start_dir_var.set(path)

    def save_and_close(self):
        """Saves all global and project settings and closes the window."""
        # 1. Zapisz ustawienia globalne
        try:
            old_voice_path = self.master.global_config.get('xtts_voice_path')
            new_voice_path = self.voice_path_var.get()

            ffmpeg_filters_data = {}
            for key, (params_var, enabled_var) in self.filter_vars.items():
                ffmpeg_filters_data[key] = {
                    "enabled": enabled_var.get(),
                    "params": params_var.get()
                }

            global_data = {
                'start_directory': self.start_dir_var.get(),
                'xtts_voice_path': new_voice_path,
                'elevenlabs_api_key': self.el_api_key_var.get(),
                'elevenlabs_voice_id': self.el_voice_id_var.get(),
                'google_credentials_path': self.gcp_creds_var.get(),
                'google_voice_name': self.gcp_voice_name_var.get(),
                'ffmpeg_filters': ffmpeg_filters_data
            }
            self.master.save_global_config(global_data)

            # Wyczyść cache modelu XTTS jeśli zmieniono głos
            if old_voice_path != new_voice_path and hasattr(self.master, 'tts_model'):
                self.master.tts_model = None
                print("Wyczyszczono cache modelu TTS (XTTS) z powodu zmiany głosu.")

            # Wyczyść cache modeli online jeśli zmieniono klucze
            # (Prostsza logika: po prostu czyścimy model, załaduje się na nowo)
            if hasattr(self.master, 'tts_model'):
                self.master.tts_model = None
                print("Wyczyszczono cache modelu TTS z powodu zapisu ustawień.")

        except Exception as e:
            messagebox.showerror("Błąd zapisu globalnego", f"Nie udało się zapisać ustawień globalnych:\n{e}",
                                 parent=self)
            return

        # 2. Zapisz ustawienia projektu (jeśli jest otwarty)
        if self.master.current_project_path:
            try:
                # Przyspieszenie
                speed_str = self.base_speed_var.get().replace(',', '.')
                speed = float(speed_str)
                self.master.set_project_config('base_audio_speed', speed)

                # Aktywny model
                self.master.set_project_config('active_tts_model', self.active_model_var.get())

            except ValueError:
                messagebox.showerror("Błędna wartość", "Bazowe przyspieszenie musi być liczbą (np. 1.1).", parent=self)
                return
            except Exception as e:
                messagebox.showerror("Błąd zapisu projektu", f"Nie udało się zapisać ustawień projektu:\n{e}",
                                     parent=self)
                return

        self.destroy()