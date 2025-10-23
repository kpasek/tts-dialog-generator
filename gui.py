from __future__ import annotations

import os.path
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import csv
import json
import sys
import os
from typing import List, Optional, Tuple
from pathlib import Path
import threading
import queue

import requests
from customtkinter import CTkFrame, CTkScrollableFrame

from app.settings import SettingsWindow
from app.utils import apply_remove_patterns, apply_replace_patterns, resource_path, is_installed
from app.entity import PatternItem
from app.tooltip import CreateToolTip

from audio.deleter import AudioDeleterWindow
from audio.progress import GenerationProgressWindow  # Potrzebne do paska postępu

# --- TTS Model Imports ---
from generators.google_cloud_tts import GoogleCloudTTS
from generators.elevenlabs_tts import ElevenLabsTTS
from generators.tts_base import TTSBase

APP_TITLE = "Subtitle Studio"
APP_CONFIG = Path.cwd() / ".subtitle_studio_config.json"
MAX_COL_WIDTH = 450

BUILTIN_REMOVE = [
    (PatternItem(r"^\[[^\]]*\]+$", "", True), "Usuń całe linie [.*]"),
    (PatternItem(r"^\<[^\>]*\>+$", "", True), "Usuń całe linie <.*>"),
    (PatternItem(r"^\{[^\}]*\}+$", "", True), "Usuń całe linie {.*}"),
    (PatternItem(r"^\([^\)]*\)+$", "", True), "Usuń całe linie (.*)"),
    (PatternItem(r"^[A-Z\?\!\.]{,4}$", "", True), None),
    (PatternItem(r" ", "", True), "Usuń niektóre niewidoczne znaki"),
]
BUILTIN_REPLACE = [
    (PatternItem(r"\[[^\]]*\]+", "", True), "Usuń treść [.*]"),
    (PatternItem(r"\<[^\>]*\>+", "", True), "Usuń treść <.*>"),
    (PatternItem(r"\{[^\}]*\}+", "", True), "Usuń treść {.*}"),
    (PatternItem(r"\([^\)]*\)}+", "", True), "Usuń treść (.*)"),
    (PatternItem(r"…", "...", True), "Popraw trójkropek"),
    (PatternItem(r"\.{2,}", ".", True), "Trójkropek > kropka"),
    (PatternItem(r"\?!", "?", True), "?! -> ?"),
    (PatternItem(r"\?{2,}", "?", True), "?(?)+ -> ?"),
    (PatternItem(r"[@#$^&*\(\)\{\}]+", " ", True), "Usuń znaki specjalne jak @#$"),
    (PatternItem(r"\s{2,}", " ", True), "Zamień białe znaki na spacje"),
    (PatternItem(r"^[-.\"\']", "", True), "Usuń wiodące znaki specjalne (-.\"')"),
    (PatternItem(r"[-\.\"\']$", "", True), "Usuń kończące znaki specjalne (-.\"')"),
]

try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except (ImportError, pygame.error) as e:
    print(f"Ostrzeżenie: Pygame mixer nie mógł zostać zainicjowany ({e}). Odtwarzanie audio będzie niedostępne.")
    PYGAME_AVAILABLE = False


class SubtitleStudioApp(ctk.CTk):
    """
    Main application class for Subtitle Studio.
    Handles the main window, UI, file operations, project management, and audio interactions.
    """

    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.has_unsaved_changes = False

        self.title(APP_TITLE)
        self.geometry("1700x1000")
        try:
            self.iconphoto(False, tk.PhotoImage(file=resource_path("assets/icon512.png")))
        except Exception:
            pass

        self.loaded_path: Optional[Path] = None
        self.original_lines: List[str] = []
        self.processed_clean: List[str] = []
        self.processed_replace: List[str] = []

        self.builtin_remove = [PatternItem(p.pattern, p.replace, p.ignore_case, name) for p, name in BUILTIN_REMOVE]
        self.builtin_replace = [PatternItem(p.pattern, p.replace, p.ignore_case, name) for p, name in BUILTIN_REPLACE]
        self.builtin_remove_state = [tk.BooleanVar(value=True, name=f"br_{i}") for i, _ in
                                     enumerate(self.builtin_remove)]
        self.builtin_replace_state = [tk.BooleanVar(value=True, name=f"bp_{i}") for i, _ in
                                      enumerate(self.builtin_replace)]
        for var in self.builtin_remove_state + self.builtin_replace_state:
            var.trace_add("write", self.mark_as_unsaved)
        self.custom_remove: List[PatternItem] = []
        self.custom_replace: List[PatternItem] = []

        self.current_project_path: Optional[Path] = None
        self.project_config = {}
        self.global_config = {}
        self.torch_installed = is_installed('torch')

        self.tts_model: Optional[TTSBase | requests.Session] = None
        self.active_model_name: str | None = None
        self.generation_lock = threading.Lock()
        self.cancel_generation_event = threading.Event()
        self.queue = queue.Queue()

        self.audio_dir: Optional[Path] = None
        self.selected_line_index: Optional[int] = None

        self._create_menu()
        self._create_widgets()
        self._load_app_config()
        self.check_queue()

    def mark_as_unsaved(self, *args):
        """Flags the current project as having unsaved changes and updates status."""
        if self.current_project_path: # Tylko jeśli projekt jest załadowany/zapisany
            self.has_unsaved_changes = True
            if "Gotowy" in self.status.cget("text") and "niezapisane" not in self.status.cget("text"):
                self.set_status(f"{self.status.cget('text')} (niezapisane zmiany)")

    def _create_menu(self):
        """Creates the main application menu bar."""
        menubar = tk.Menu(self)

        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Wczytaj napisy (.txt)...", command=self.load_file)
        config_menu.add_separator()
        config_menu.add_command(label="Otwórz projekt (.json)...", command=self.open_project)
        config_menu.add_command(label="Zapisz projekt", command=self.save_project)
        config_menu.add_command(label="Zapisz jako...", command=self.save_project_as)
        config_menu.add_separator()
        config_menu.add_command(label="Zamknij projekt", command=self.close_project)
        config_menu.add_separator()
        # === ZMIANA: Wywołania oddzielnych funkcji ===
        config_menu.add_command(label="Ustawienia Globalne...", command=self.open_global_settings)
        config_menu.add_command(label="Ustawienia Projektu...", command=self.open_project_settings)
        # ============================================
        config_menu.add_separator()
        config_menu.add_command(label="Zamknij", command=self.on_close)
        menubar.add_cascade(label="Projekt", menu=config_menu)

        gen_menu = tk.Menu(menubar, tearoff=0)
        gen_menu.add_command(label="Wybierz katalog audio...", command=self.choose_audio_dir)
        gen_menu.add_command(label="Generuj wszystkie brakujące", command=self.start_generate_all)
        gen_menu.add_separator()
        gen_menu.add_command(label="Masowe usuwanie dialogów...", command=self.open_audio_deleter)
        menubar.add_cascade(label="Dialogi", menu=gen_menu)

        self.config(menu=menubar)

    def _create_widgets(self):
        """Creates and places all main UI widgets in the window."""
        root_grid = ctk.CTkFrame(self)
        root_grid.pack(fill="both", expand=True, padx=10, pady=10)
        root_grid.grid_rowconfigure(0, weight=1)
        root_grid.grid_columnconfigure(2, weight=1)

        # --- LEFT: Built-in Patterns ---
        left = ctk.CTkFrame(root_grid, width=MAX_COL_WIDTH)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        left.grid_rowconfigure(4, weight=1)

        self.lbl_filename = ctk.CTkLabel(left, text="Brak wczytanego pliku")
        self.lbl_filename.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=5)

        ctk.CTkLabel(left, text="Wbudowane wzorce wycinające").grid(row=1, column=0, sticky="we", padx=6)
        self._create_builtin_list(left, self.builtin_remove, self.builtin_remove_state, 2)

        ctk.CTkLabel(left, text="Wbudowane wzorce podmieniające").grid(row=3, column=0, sticky="we", padx=6)
        self._create_builtin_list(left, self.builtin_replace, self.builtin_replace_state, 4)

        # --- CENTER: Custom Patterns ---
        self.center_frame = ctk.CTkFrame(root_grid, width=500)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_rowconfigure(4, weight=1) # Zmieniono z 5 na 4

        ctk.CTkLabel(self.center_frame, text="Własne wzorce wycinające").grid(row=0, column=0, sticky="w", padx=6)
        self.custom_remove_frame = ctk.CTkScrollableFrame(self.center_frame)
        self.custom_remove_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 6))

        clean_inline_frame = self.build_clean_list_frame(self.center_frame, 2)
        self.ent_remove_pattern = ctk.CTkEntry(clean_inline_frame, placeholder_text="regexp")
        self.ent_remove_pattern.pack(side="left", fill="x", expand=True, padx=(4, 2))
        self.ent_remove_replace = ctk.CTkEntry(clean_inline_frame, placeholder_text="zamień na")
        self.ent_remove_replace.pack(side="left", fill="x", expand=True, padx=(2, 2))
        self.var_remove_ignore = tk.BooleanVar(value=False)
        checkbox_rem = ctk.CTkCheckBox(clean_inline_frame, text="Aa", variable=self.var_remove_ignore)
        checkbox_rem.pack(side="left", padx=(2, 4))
        CreateToolTip(checkbox_rem, 'Uwzględnij wielkość znaków')
        ctk.CTkButton(clean_inline_frame, text="Dodaj", command=self.add_inline_remove).pack(side="left", padx=2)

        replace_top_frame = ctk.CTkFrame(self.center_frame)
        replace_top_frame.grid(row=3, column=0, sticky="ew", pady=(4, 4))
        lab_rep = ctk.CTkLabel(replace_top_frame, text="Własne wzorce podmieniające")
        lab_rep.pack(side="left", anchor="w", fill="x", expand=False, padx=6)
        ctk.CTkButton(replace_top_frame, text="Importuj CSV...", command=self.import_patterns_from_csv).pack(
            side="right")

        self.custom_replace_frame = ctk.CTkScrollableFrame(self.center_frame)
        self.custom_replace_frame.grid(row=4, column=0, sticky="nsew", padx=6, pady=(2, 6))

        replace_inline_frame = self.build_clean_list_frame(self.center_frame, 5) # Row 5
        self.ent_replace_pattern = ctk.CTkEntry(replace_inline_frame, placeholder_text="regexp")
        self.ent_replace_pattern.pack(side="left", fill="x", expand=True, padx=(4, 2))
        self.ent_replace_replace = ctk.CTkEntry(replace_inline_frame, placeholder_text="zamień na")
        self.ent_replace_replace.pack(side="left", fill="x", expand=True, padx=(2, 2))
        self.var_replace_ignore = tk.BooleanVar(value=False)
        ignore_checkbox = ctk.CTkCheckBox(replace_inline_frame, text="Aa", variable=self.var_replace_ignore)
        ignore_checkbox.pack(side="left", padx=(2, 4))
        CreateToolTip(ignore_checkbox, 'Uwzględnij wielkość znaków')
        ctk.CTkButton(replace_inline_frame, text="Dodaj", command=self.add_inline_replace).pack(side="left", padx=2)

        # --- RIGHT: Preview & Actions ---
        right = ctk.CTkFrame(root_grid)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        # Stats and Apply button
        stats_frame = ctk.CTkFrame(right)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(stats_frame, text="Zastosuj wzorce", command=self.apply_processing).pack(side="left", padx=5)

        self.lbl_count_orig = ctk.CTkLabel(stats_frame, text="Linie org.: 0")
        self.lbl_count_orig.pack(side="left", anchor="w", padx=5)
        self.lbl_count_after = ctk.CTkLabel(stats_frame, text="Linie po: 0")
        self.lbl_count_after.pack(side="left", anchor="w", padx=5)


        self.btn_download_clean = ctk.CTkButton(stats_frame, text="Pobierz - napisy dla Game Reader",
                                                command=self.download_clean)
        self.btn_download_replace = ctk.CTkButton(stats_frame, text="Pobierz - napisy dla TTS",
                                                  command=self.download_replace)
        self.btn_download_clean.pack(side="right", padx=5)
        self.btn_download_replace.pack(side="right", padx=5)

        # Audio buttons
        audio_btn_frame = ctk.CTkFrame(right)
        audio_btn_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5), padx=5) # Row 2

        self.play_button = ctk.CTkButton(audio_btn_frame, text="▶️ Odtwórz", width=80, command=self.play_selected_audio,
                                         state="disabled")
        self.play_button.pack(side="left", padx=(0, 4))
        if not PYGAME_AVAILABLE:
            self.play_button.configure(state="disabled", text="N/A Pygame")

        self.generate_button = ctk.CTkButton(audio_btn_frame, text="⚙️ Generuj", width=80,
                                             command=self.generate_selected_audio, state="disabled")
        self.generate_button.pack(side="left", padx=4)

        self.delete_button = ctk.CTkButton(audio_btn_frame, text="❌ Usuń", width=80, command=self.delete_selected_audio,
                                           state="disabled")
        self.delete_button.pack(side="left", padx=4)

        self.delete_all_button = ctk.CTkButton(audio_btn_frame, text="🗑️ Usuń Wsz.", width=80,
                                               command=self.delete_all_selected_audio, state="disabled")
        self.delete_all_button.pack(side="left", padx=4)

        # Search bar
        search_frame = ctk.CTkFrame(right)
        search_frame.grid(row=3, column=0, sticky="ew", pady=(0, 5), padx=5) # Row 3
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Przeszukaj podgląd")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda event: self.apply_patterns())
        self.search_entry.bind("<Control-BackSpace>", lambda event: self.search_entry.delete(0, tk.END))

        self.search_button = ctk.CTkButton(search_frame, text="Szukaj", command=self.apply_patterns)
        self.search_button.grid(row=0, column=1, padx=(6, 0))

        # Preview Textbox
        self.txt_preview = ctk.CTkTextbox(right)
        self.txt_preview.grid(row=4, column=0, sticky="nsew", padx=5, pady=(0, 5)) # Row 4
        self.txt_preview.configure(state=tk.DISABLED)
        self.txt_preview.tag_config("selected_line", background="gray25")
        self.txt_preview.bind("<ButtonRelease-1>", self.on_preview_click)
        self.txt_preview.bind("<Double-Button-1>", self.play_selected_audio)

        # --- Status Bar ---
        self.status = ctk.CTkLabel(self, text="Gotowy", anchor="w")
        self.status.pack(fill="x", side="bottom", padx=10, pady=(0, 5))

    def build_clean_list_frame(self, parent_frame, row_nr) -> CTkFrame:
        """Helper to create a standard input frame for patterns."""
        frame = ctk.CTkFrame(parent_frame)
        frame.grid(row=row_nr, column=0, sticky="ew", pady=(4, 4))
        return frame

    def build_scroll_list_frame(self, parent_frame, row_nr) -> CTkScrollableFrame:
        """Helper to create a standard scrollable frame."""
        frame = ctk.CTkScrollableFrame(parent_frame)
        frame.grid(row=row_nr, column=0, sticky="nsew", padx=6, pady=(2, 6))
        return frame

    def _create_builtin_list(self, parent, patterns, states, row_nr):
        """Populates a scrollable frame with built-in pattern checkboxes."""
        sc = ctk.CTkScrollableFrame(parent)
        sc.grid(row=row_nr, column=0, sticky="nsew", padx=6, pady=(0, 6))
        for i, p in enumerate(patterns):
            text = f"{p.pattern} -> {p.replace}" if p.name is None else p.name
            cb = ctk.CTkCheckBox(sc, text=text, variable=states[i])
            cb.pack(anchor="w", pady=2)

    def add_inline_remove(self):
        """Adds a new custom 'remove' pattern from the input fields."""
        pattern = self.ent_remove_pattern.get()
        replace = self.ent_remove_replace.get()
        case_sensitive = self.var_remove_ignore.get()
        if not pattern: return

        new_pattern = PatternItem(pattern, replace, not case_sensitive)
        self.custom_remove.append(new_pattern)
        self.add_row(self.custom_remove_frame, new_pattern, self.custom_remove)
        self.mark_as_unsaved()
        self.ent_remove_pattern.delete(0, "end")
        self.ent_remove_replace.delete(0, "end")

    def add_inline_replace(self):
        """Adds a new custom 'replace' pattern from the input fields."""
        pattern = self.ent_replace_pattern.get()
        replace = self.ent_replace_replace.get()
        case_sensitive = self.var_replace_ignore.get()
        if not pattern: return

        new_pattern = PatternItem(pattern, replace, not case_sensitive)
        self.custom_replace.append(new_pattern)
        self.add_row(self.custom_replace_frame, new_pattern, self.custom_replace)
        self.mark_as_unsaved()
        self.ent_replace_pattern.delete(0, "end")
        self.ent_replace_replace.delete(0, "end")

    def add_row(self, frame, pattern_item: PatternItem, target_list: List[PatternItem]):
        """Adds a UI row for a pattern."""
        row = ctk.CTkFrame(frame)
        row.pack(fill="x", pady=2, padx=2)
        lbl_text = f"[{pattern_item.pattern}] -> [{pattern_item.replace}] {'' if pattern_item.ignore_case else '(Aa)'}"
        lbl = ctk.CTkLabel(row, text=lbl_text)
        lbl.pack(side="left", fill="x", expand=False, padx=4)
        def on_delete():
            try: target_list.remove(pattern_item)
            except ValueError: pass
            row.destroy()
            self.mark_as_unsaved()
        btnX = ctk.CTkButton(row, text="X", width=60, command=on_delete)
        btnX.pack(side="right", padx=4)

    def load_file(self, path: Optional[str] = None, bypass_save_check: bool = False):
        """Loads a subtitle .txt file."""
        if not path:
            initial_dir = self.global_config.get('start_directory') or self._get_save_dir()
            path = filedialog.askopenfilename(title="Wybierz plik napisów",
                                              filetypes=[("Text files", "*.txt"), ("All files", "*")],
                                              initialdir=initial_dir)
        if not path: return
        if not bypass_save_check and not self._check_unsaved_changes(): return

        self.loaded_path = Path(path)
        self.lbl_filename.configure(text=str(self.loaded_path.name))
        try:
            with open(self.loaded_path, "r", encoding="utf-8", errors="replace") as f:
                self.original_lines = f.read().splitlines()
            self.apply_patterns()
            self.set_status(f"Wczytano {len(self.original_lines)} linii")
            # Po wczytaniu pliku nie ma niezapisanych zmian *projektu*
            self.has_unsaved_changes = False
            # Zaktualizuj ścieżkę w configu projektu, jeśli jest otwarty
            if self.current_project_path:
                 self.set_project_config('subtitle_path', str(self.loaded_path)) # To wywoła zapis

        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{e}")

    def open_project(self, path: str | None = None):
        """Opens a .json project file."""
        if path is None:
            if not self._check_unsaved_changes(): return
            initial_dir = self.global_config.get('start_directory') or str(Path.cwd())
            path = filedialog.askopenfilename(title="Otwórz projekt",
                                              filetypes=[("JSON", "*.json"), ("All", "*")],
                                              initialdir=initial_dir)
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: cfg = json.load(f)
            self.current_project_path = Path(path)
            self.project_config = cfg

            # === POPRAWKA: Użyj var._name jako klucza ===
            all_vars = self.builtin_remove_state + self.builtin_replace_state
            traces = {}
            for var in all_vars:
                 if var.trace_info():
                     trace_id = var.trace_info()[0][1]
                     traces[var._name] = (var, trace_id) # Zapisz var i trace_id pod nazwą
                     var.trace_remove("write", trace_id)

            for i, val in enumerate(cfg.get("builtin_remove_state", [])):
                if i < len(self.builtin_remove_state): self.builtin_remove_state[i].set(bool(val))
            for i, val in enumerate(cfg.get("builtin_replace_state", [])):
                if i < len(self.builtin_replace_state): self.builtin_replace_state[i].set(bool(val))

            for name, (var, trace_id) in traces.items():
                var.trace_add("write", self.mark_as_unsaved)
            # ============================================

            self.custom_remove = [PatternItem.from_json(x) for x in cfg.get("custom_remove", [])]
            self.custom_replace = [PatternItem.from_json(x) for x in cfg.get("custom_replace", [])]
            self._refresh_custom_lists()

            subtitle_path = cfg.get("subtitle_path")
            if subtitle_path and Path(subtitle_path).exists():
                self.load_file(subtitle_path, bypass_save_check=True)
            else:
                 self.original_lines = []
                 self.apply_patterns()
                 self.lbl_filename.configure(text="Brak wczytanego pliku")

            audio_path_str = cfg.get("audio_path")
            self.audio_dir = Path(audio_path_str) if audio_path_str else None

            self.set_status(f"Wczytano projekt: {self.current_project_path.name}")
            self.save_app_setting('last_project', path)
            self.has_unsaved_changes = False # Świeżo załadowany

        except Exception as e:
            messagebox.showerror("Błąd wczytywania projektu", f"Nie udało się wczytać konfiguracji:\n{e}")
            self.current_project_path = None
            self.project_config = {}
            self.has_unsaved_changes = False

    def close_project(self):
        """Closes the current project and restarts."""
        if not self._check_unsaved_changes(): return
        try:
            self.save_app_setting('last_project', None)
            self._reset_app_state()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            messagebox.showerror("Błąd restartu", f"Nie udało się zrestartować aplikacji:\n{e}")

    def _reset_app_state(self):
        """Resets the application state to default."""
        self.current_project_path = None
        self.project_config = {}
        self.original_lines = []
        self.processed_clean = []
        self.processed_replace = []
        self.custom_remove = []
        self.custom_replace = []
        self.loaded_path = None
        self.audio_dir = None
        self.has_unsaved_changes = False
        self._refresh_custom_lists()
        self.apply_patterns()
        self.lbl_filename.configure(text="Brak wczytanego pliku")
        # Zresetuj wbudowane checkboxy (opcjonalne)
        for var in self.builtin_remove_state + self.builtin_replace_state: var.set(True)


    def set_project_config(self, param, value):
        """Saves a single key-value pair to the current project config."""
        if self.project_config is None: self.project_config = {}
        if self.project_config.get(param) != value: # Zapisuj tylko jeśli jest zmiana
            self.project_config[param] = value
            self.mark_as_unsaved()
            if self.current_project_path: self.save_project()

    def save_project(self, cfg: dict | None = None):
        """Saves the current config to the loaded project file."""
        if not self.current_project_path: return self.save_project_as()

        final_cfg = self._gather_project_config()
        if cfg: final_cfg.update(cfg)
        self.project_config = final_cfg

        try:
            with open(self.current_project_path, "w", encoding="utf-8") as f:
                json.dump(final_cfg, f, indent=2, ensure_ascii=False)
            self.set_status(f"Zapisano projekt: {self.current_project_path.name}")
            self.has_unsaved_changes = False
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać konfiguracji:\n{e}")

    def save_project_as(self):
        """Saves the current configuration to a new .json project file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=self.global_config.get('start_directory') or str(
                self.current_project_path.parent if self.current_project_path else Path.cwd())
        )
        if not path:
            return
        self.current_project_path = Path(path)
        self.save_project()

    def _gather_project_config(self) -> dict:
        """Collects all current project settings."""
        current_cfg = self.project_config.copy() if self.project_config else {}
        current_cfg.update({
            "builtin_remove_state": [bool(v.get()) for v in self.builtin_remove_state],
            "builtin_replace_state": [bool(v.get()) for v in self.builtin_replace_state],
            "custom_remove": [p.to_json() for p in self.custom_remove],
            "custom_replace": [p.to_json() for p in self.custom_replace],
            "subtitle_path": str(self.loaded_path) if self.loaded_path else None,
            "audio_path": str(self.audio_dir.absolute()) if self.audio_dir else None,
            "active_tts_model": self.project_config.get('active_tts_model', 'XTTS' if self.torch_installed else "ElevenLabs"),
            "base_audio_speed": self.project_config.get('base_audio_speed', 1.1)
        })
        return current_cfg

    def _load_app_config(self):
        """Loads the global app config."""
        if APP_CONFIG.exists():
            try:
                with open(APP_CONFIG, "r", encoding="utf-8") as f: self.global_config = json.load(f)
                last_proj = self.global_config.get('last_project')
                if last_proj and Path(last_proj).exists(): # Sprawdź czy plik projektu nadal istnieje
                     self.open_project(last_proj)
                else:
                    # Jeśli nie istnieje, usuń wpis
                    if last_proj: self.save_app_setting('last_project', None)
                    self._reset_app_state() # Zacznij od czystego stanu

            except Exception as e:
                print(f"Błąd wczytywania konfiguracji globalnej: {e}")
                self.global_config = {}

    def filter_preview(self, lines: List[str]) -> List[str]:
        """Filters preview lines based on search."""
        search_term = self.search_entry.get()
        if not search_term:
            return lines
        try:
            # Użyj re.escape, aby traktować wyszukiwany tekst dosłownie, chyba że to regex
            # Prostsze: po prostu szukaj podciągu, ignorując wielkość liter
            pattern = search_term.lower()
            return [line for line in lines if pattern in line.lower()]
        except re.error:
            # Jeśli wprowadzono nieprawidłowy regex, po prostu nie filtruj
            return lines

    def _refresh_custom_lists(self):
        """Recreates the custom pattern UI lists."""
        for frame_attr in ['custom_remove_frame', 'custom_replace_frame']:
            if hasattr(self, frame_attr):
                widget = getattr(self, frame_attr)
                if widget:
                    # Usuń dzieci przed zniszczeniem ramki
                    for child in widget.winfo_children():
                        child.destroy()
                    widget.destroy()
        self.custom_remove_frame = self.build_scroll_list_frame(self.center_frame, 1)
        for p in self.custom_remove:
            self.add_row(self.custom_remove_frame, p, self.custom_remove)

        self.custom_replace_frame = self.build_scroll_list_frame(self.center_frame, 4)  # Poprawiony row
        for p in self.custom_replace:
            self.add_row(self.custom_replace_frame, p, self.custom_replace)

    def _gather_active_patterns(self) -> tuple[List[PatternItem], List[PatternItem]]:
        """Collects all active built-in and custom patterns."""
        remove_patterns = list(self.custom_remove)  # Kopiuj listę
        remove_patterns.extend(p for i, p in enumerate(self.builtin_remove) if self.builtin_remove_state[i].get())

        replace_patterns = list(self.custom_replace)  # Kopiuj listę
        replace_patterns.extend(p for i, p in enumerate(self.builtin_replace) if self.builtin_replace_state[i].get())

        return remove_patterns, replace_patterns

    def apply_processing(self):
        """Applies all active patterns to the loaded subtitles."""
        if not self.original_lines:
            messagebox.showwarning('Brak pliku', 'Najpierw wczytaj plik z napisami.')
            return

        self.apply_patterns()  # To zaktualizuje processed_clean i processed_replace

        # Pokazanie przycisków pobierania
        if not self.btn_download_clean.winfo_ismapped():  # Sprawdź czy już są widoczne
            self.btn_download_clean.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        if not self.btn_download_replace.winfo_ismapped():
            self.btn_download_replace.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.set_status('Przetworzono napisy — gotowe do pobrania')
        self.mark_as_unsaved()

    def download_clean(self):
        """Saves the 'clean' (for Game Reader) subtitles to a file."""
        if not self.processed_clean:
            messagebox.showwarning('Brak danych', 'Brak oczyszczonych linii. Najpierw przetwórz plik.')
            return
        path = filedialog.asksaveasfilename(title='Zapisz oczyszczone napisy', defaultextension='.txt',
                                            filetypes=[('Text files', '*.txt')],
                                            initialdir=self._get_save_dir())
        if not path: return
        self._save_lines_to_file(path, self.processed_clean, "oczyszczone")

    def download_replace(self):
        """Saves the 'replaced' (for TTS) subtitles to a file."""
        if not self.processed_replace:
            messagebox.showwarning('Brak danych', 'Brak zamienionych linii. Najpierw przetwórz plik.')
            return
        path = filedialog.asksaveasfilename(title='Zapisz napisy z podmianami', defaultextension='.txt',
                                            filetypes=[('Text files', '*.txt')],
                                            initialdir=self._get_save_dir())
        if not path: return
        self._save_lines_to_file(path, self.processed_replace, "z podmianami")

    def _get_save_dir(self) -> str | None:
        """Determines the initial directory for save dialogs."""
        if self.loaded_path:
            return str(self.loaded_path.parent)
        return self.global_config.get('start_directory')

    def _save_lines_to_file(self, path: str, lines: List[str], description: str):
        """Helper function to write lines to a text file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo('Gotowe', f'Zapisano napisy {description}:\n{path}')
            self.set_status(f'Zapisano napisy {description}: {Path(path).name}')
        except Exception as e:
            messagebox.showerror('Błąd zapisu', str(e))

    def apply_patterns(self):
        """Recalculates processed lines and updates preview."""
        self.lbl_count_orig.configure(text=f'Linie org.: {len(self.original_lines)}')
        rem_patterns, rep_patterns = self._gather_active_patterns()

        try:
            self.processed_clean = apply_remove_patterns(self.original_lines, rem_patterns)
            self.processed_replace = apply_replace_patterns(self.processed_clean, rep_patterns)
        except re.error as e:
            messagebox.showerror('Błąd regex', f'Błąd w wyrażeniu regularnym:\n{e}')
            return
        except Exception as e:
            messagebox.showerror('Błąd przetwarzania', f'Wystąpił nieoczekiwany błąd podczas stosowania wzorców:\n{e}')
            return

        self.lbl_count_after.configure(text=f'Linie po: {len(self.processed_clean)}')
        self.set_preview(self.processed_replace)
        self.update_audio_buttons_state()

    def set_preview(self, lines_to_show: list[str]):
        """Updates the read-only preview text box with numbered lines."""
        # Zresetuj zaznaczenie
        self.selected_line_index = None
        self.txt_preview.tag_remove("selected_line", "1.0", tk.END)

        total_lines = len(lines_to_show)
        num_digits = len(str(total_lines)) if total_lines > 0 else 1
        numbered_lines = [
            f"{str(i + 1).zfill(num_digits)} | {line}"
            for i, line in enumerate(lines_to_show)
        ]

        filtered = self.filter_preview(numbered_lines)

        self.txt_preview.configure(state='normal')
        self.txt_preview.delete('1.0', tk.END)  # Zaczynaj od 1.0
        if filtered:
            self.txt_preview.insert('1.0', '\n'.join(filtered))
        self.txt_preview.configure(state='disabled')

    def set_status(self, txt: str):
        """Updates status bar."""
        self.status.configure(text=txt)

    def open_audio_deleter(self):
        """Opens Batch Audio Deleter window."""
        if not self.processed_replace: return messagebox.showwarning("Brak danych", "Najpierw przetwórz.", parent=self)
        if not self.audio_dir: return messagebox.showwarning("Brak katalogu", "Ustaw katalog audio.", parent=self)
        win = AudioDeleterWindow(self, self.processed_replace, str(self.audio_dir))
        win.grab_set()

    # === ZMIANA: Rozdzielone funkcje ===
    def open_global_settings(self):
        """Opens the Global Settings window."""
        win = SettingsWindow(self, self.torch_installed, mode='global')
        win.grab_set()

    def open_project_settings(self):
        """Opens the Project Settings window."""
        if not self.current_project_path:
             return messagebox.showwarning("Brak projektu", "Otwórz lub zapisz projekt.", parent=self)
        win = SettingsWindow(self, self.torch_installed, mode='project')
        win.grab_set()
    # ==================================

    def import_patterns_from_csv(self):
        """Imports 'replace' patterns from CSV."""
        initial_dir = self.global_config.get('start_directory') or self._get_save_dir()
        file_path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=initial_dir
        )
        if not file_path: return

        imported_count = 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if not row or len(row) < 2:
                        print(f"Pominięto wiersz {i + 1}: za mało kolumn ({len(row)})")
                        continue
                    pattern = row[0].strip()
                    if not pattern:
                        print(f"Pominięto wiersz {i + 1}: pusty wzorzec")
                        continue

                    replace = row[1].strip() if len(row) > 1 else ""
                    # Domyślnie ignoruj wielkość liter (True), Aa=False => case_sensitive=True
                    ignore_case = True  # Domyślnie
                    if len(row) > 2 and row[2].strip().isdigit():
                        # Jeśli jest 3 kolumna i jest cyfrą, traktuj jako flagę case sensitive
                        # 0 -> ignore case (True), 1 -> case sensitive (False)
                        ignore_case = not bool(int(row[2].strip()))

                    new_pattern = PatternItem(pattern, replace, ignore_case)
                    self.custom_replace.append(new_pattern)
                    self.add_row(self.custom_replace_frame, new_pattern, self.custom_replace)
                    imported_count += 1

            if imported_count > 0:
                self.mark_as_unsaved()
                messagebox.showinfo("Import zakończony", f"Zaimportowano {imported_count} wzorców.")
            else:
                messagebox.showwarning("Import zakończony", "Nie zaimportowano żadnych poprawnych wzorców.")
        except Exception as e:
            messagebox.showerror("Błąd importu", f"Nie udało się zaimportować pliku:\n{e}")

    def save_global_config(self, new_config_data: dict):
        """Saves data to the global .subtitle_studio_config.json file."""
        self.global_config.update(new_config_data)
        try:
            with open(APP_CONFIG.absolute(), "w", encoding="utf-8") as f: json.dump(self.global_config, f, indent=2)
        except Exception as e: messagebox.showerror("Błąd zapisu config", f"Błąd: {e}")

    def save_app_setting(self, param, value):
        """Saves a single key-value to global config."""
        self.save_global_config({param: value})

    def _check_unsaved_changes(self) -> bool:
        """
        Checks for unsaved changes and prompts the user to save if necessary.

        Returns:
            bool: False if the action was cancelled, True otherwise.
        """
        if self.has_unsaved_changes and self.current_project_path:
            msg = "Masz niezapisane zmiany w projekcie. Czy chcesz je zapisać?"
            result = messagebox.askyesnocancel("Niezapisane zmiany", msg, parent=self)

            if result is True:
                self.save_project()
            elif result is None:
                return False
        return True

    def on_close(self):
        """Handles window close event."""
        if self._check_unsaved_changes():
            self.stop_audio()
            self.quit()

    # ===============================
    # === AUDIO UI METHODS        ===
    # ===============================
    def on_preview_click(self, event):
        """Handles clicks inside the preview textbox to select a line."""
        try:
            # Pobierz indeks kliknięcia (np. "5.10")
            click_index = self.txt_preview.index(f"@{event.x},{event.y}")
            # Pobierz numer linii (np. "5")
            line_number_str = click_index.split('.')[0]
            # Przekonwertuj na indeks listy (0-based)
            # Uwaga: To jest indeks linii W WIDOCZNYM, filtrowanym tekście!
            visible_line_index = int(line_number_str) - 1

            # Musimy zmapować ten widoczny indeks na oryginalny indeks z `processed_replace`
            # Najpierw pobierz WSZYSTKIE linie z textboxa
            all_visible_lines = self.txt_preview.get("1.0", tk.END).splitlines()
            if visible_line_index >= len(all_visible_lines): return  # Kliknięcie poza tekstem

            # Pobierz treść klikniętej linii (np. "005 | Jakiś tekst")
            clicked_line_content = all_visible_lines[visible_line_index]

            # Wyciągnij numer oryginalnej linii z początku
            match = re.match(r"^\s*(\d+)\s*\|", clicked_line_content)
            if match:
                original_line_number = int(match.group(1))
                self.selected_line_index = original_line_number - 1  # 0-based index

                # Podświetl linię
                self.txt_preview.tag_remove("selected_line", "1.0", tk.END)
                line_start = f"{line_number_str}.0"
                line_end = f"{line_number_str}.end"
                self.txt_preview.tag_add("selected_line", line_start, line_end)

            else:
                # Nie udało się sparsować numeru linii (np. pusta linia, błąd formatowania)
                self.selected_line_index = None
                self.txt_preview.tag_remove("selected_line", "1.0", tk.END)

        except (ValueError, tk.TclError):
            # Błąd konwersji lub indeksu - kliknięcie w złym miejscu
            self.selected_line_index = None
            self.txt_preview.tag_remove("selected_line", "1.0", tk.END)

        # Zaktualizuj stan przycisków
        self.update_audio_buttons_state()

    def update_audio_buttons_state(self):
        """Enables/disables audio action buttons based on selection and audio dir."""
        line_selected = self.selected_line_index is not None
        audio_dir_set = self.audio_dir is not None and self.audio_dir.is_dir()

        # Znajdź pliki dla zaznaczonej linii (jeśli jest)
        files_exist = False
        if line_selected and audio_dir_set:
            identifier = str(self.selected_line_index + 1)
            found_files = self._find_audio_files(identifier)
            files_exist = bool(found_files)

        # Ustaw stany przycisków
        play_state = "normal" if PYGAME_AVAILABLE and line_selected and audio_dir_set and files_exist else "disabled"
        gen_state = "normal" if line_selected and audio_dir_set else "disabled"
        del_state = "normal" if line_selected and audio_dir_set and files_exist else "disabled"
        del_all_state = del_state  # Taki sam warunek jak dla pojedynczego usunięcia

        self.play_button.configure(state=play_state)
        self.generate_button.configure(state=gen_state)
        self.delete_button.configure(state=del_state)
        self.delete_all_button.configure(state=del_all_state)

    def _get_selected_identifier(self) -> str | None:
        """Returns the identifier (line number as string) of the selected line, or None."""
        if self.selected_line_index is not None:
            return str(self.selected_line_index + 1)
        return None

    def _find_audio_files(self, identifier: str) -> List[Tuple[Path, bool]]:
        """Finds audio files for a given identifier."""
        if not self.audio_dir: return []
        # Uwzględniamy mp3 z elevenlabs
        candidates = [
            (self.audio_dir / f"output1 ({identifier}).wav", False),
            (self.audio_dir / f"output1 ({identifier}).mp3", False),  # Dodano mp3
            (self.audio_dir / f"output1 ({identifier}).ogg", False),
            (self.audio_dir / "ready" / f"output1 ({identifier}).ogg", True),
            (self.audio_dir / "ready" / f"output2 ({identifier}).ogg", True)
        ]
        return [(f, ready) for f, ready in candidates if f.exists()]

    def stop_audio(self):
        """Stops and unloads any currently playing audio file."""
        if not PYGAME_AVAILABLE: return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass

    def play_selected_audio(self, event):
        """Plays the first available audio file for the selected line."""
        if not PYGAME_AVAILABLE: return
        identifier = self._get_selected_identifier()
        if not identifier or not self.audio_dir: return

        files = self._find_audio_files(identifier)
        if files:
            file_to_play = files[0][0]  # Odtwórz pierwszy znaleziony
            self.stop_audio()  # Zatrzymaj poprzedni
            try:
                print(f"Odtwarzam: {file_to_play}")
                pygame.mixer.music.load(str(file_to_play))
                pygame.mixer.music.play()
            except Exception as e:
                messagebox.showerror("Błąd odtwarzania", f"Nie udało się odtworzyć pliku:\n{e}", parent=self)
        else:
            messagebox.showinfo("Brak pliku", "Brak plików audio dla tej linii.", parent=self)

    def delete_selected_audio(self):
        """Deletes the *first found* audio file for the selected line."""
        identifier = self._get_selected_identifier()
        if not identifier or not self.audio_dir: return

        files = self._find_audio_files(identifier)
        if not files:
            messagebox.showinfo("Brak plików", "Brak plików audio do usunięcia dla tej linii.", parent=self)
            return

        file_to_delete = files[0][0]  # Usuń pierwszy znaleziony
        self._delete_single_file_with_check(file_to_delete)

    def delete_all_selected_audio(self):
        """Deletes *all* found audio files for the selected line."""
        identifier = self._get_selected_identifier()
        if not identifier or not self.audio_dir: return

        files = self._find_audio_files(identifier)
        if not files:
            messagebox.showinfo("Brak plików", "Brak plików audio do usunięcia dla tej linii.", parent=self)
            return

        # Sprawdź, czy którykolwiek plik jest odtwarzany
        if PYGAME_AVAILABLE:
            try:
                if pygame.mixer.music.get_busy():
                    # Sprawdź, czy odtwarzany plik jest jednym z tych do usunięcia
                    # (Pygame nie udostępnia ścieżki, więc musimy to pominąć - użytkownik musi zatrzymać)
                    messagebox.showwarning("Plik w użyciu",
                                           "Audio jest odtwarzane. Zatrzymaj je (np. klikając Play dla innej linii) przed usunięciem.",
                                           parent=self)
                    return
            except Exception:
                pass

        # Potwierdzenie
        file_list_str = "\n".join([f.name for f, rdy in files])
        if not messagebox.askyesno("Potwierdź usunięcie",
                                   f"Czy na pewno usunąć WSZYSTKIE ({len(files)}) pliki dla linii {identifier}?\n{file_list_str}",
                                   parent=self):
            return

        self.stop_audio()  # Zatrzymaj na wszelki wypadek

        deleted_count = 0
        errors = []
        for file_path, _ in files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                errors.append(f"{file_path.name}: {e}")

        if errors:
            messagebox.showerror("Błąd usuwania",
                                 f"Usunięto {deleted_count} z {len(files)} plików.\nBłędy:\n" + "\n".join(errors),
                                 parent=self)
        else:
            messagebox.showinfo("Usunięto", f"Pomyślnie usunięto {deleted_count} plików dla linii {identifier}.",
                                parent=self)

        self.update_audio_buttons_state()  # Odśwież stan przycisków

    def _delete_single_file_with_check(self, file_path: Path):
        """Internal helper to delete a single file with safety checks."""
        if PYGAME_AVAILABLE:
            try:
                if pygame.mixer.music.get_busy():
                    messagebox.showwarning("Plik w użyciu",
                                           "Nie można usunąć pliku podczas odtwarzania. Zatrzymaj je i spróbuj ponownie.",
                                           parent=self)
                    return
            except Exception:
                pass

        self.stop_audio()  # Zatrzymaj i zwolnij

        self.lift()
        self.focus_force()
        if os.path.exists(file_path) and messagebox.askyesno("Potwierdź", f"Usunąć plik?\n{file_path.name}",
                                                             parent=self):
            try:
                os.remove(file_path)
                self.update_audio_buttons_state()  # Odśwież stan przycisków
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się usunąć pliku:\n{e}", parent=self)

    def choose_audio_dir(self):
        """Opens dialog to choose audio directory."""
        init_dir = self.global_config.get('start_directory') or (str(self.audio_dir) if self.audio_dir else None)
        path = filedialog.askdirectory(title="Wybierz katalog audio", initialdir=init_dir, parent=self)
        if path:
            new_dir = Path(path)
            if self.audio_dir != new_dir:
                self.audio_dir = new_dir
                if self.current_project_path: self.set_project_config('audio_path', str(new_dir.absolute()))
                self.update_audio_buttons_state()

    # ===============================
    # === GENERATION LOGIC        ===
    # ===============================
    def check_queue(self):
        """Periodically checks queue for GUI updates."""
        try: task = self.queue.get_nowait()
        except queue.Empty: pass
        else: task()
        self.after(100, self.check_queue)

    def _get_active_tts_model_name(self) -> str | None:
        """Gets the active TTS model name from project config."""
        proj_cfg = self._gather_project_config()
        return proj_cfg.get('active_tts_model')

    def _load_tts_model(self):
        """
        Loads the active TTS model instance based on project settings.
        Sets self.tts_model to the loaded instance or None on failure.
        """
        self.active_model_name = self._get_active_tts_model_name()
        if not self.active_model_name:
            raise ValueError("Nie wybrano aktywnego modelu TTS w ustawieniach projektu.")

        try:
            # Wyczyść stary model/sesję
            self.tts_model = None

            if self.active_model_name == 'XTTS':
                # --- Logika XTTS API ---
                api_url = self.global_config.get('xtts_api_url', 'http://127.0.0.1:8001')
                if not api_url:
                    raise ValueError("URL dla XTTS API nie jest ustawione w Ustawieniach Globalnych.")
                # Tworzymy sesję requests dla potencjalnych optymalizacji połączenia
                session = requests.Session()
                session.headers.update({'Content-Type': 'application/json'})
                # Zapisujemy URL i sesję do użycia później
                self.tts_model = {'url': api_url.rstrip('/') + '/xtts/tts', 'session': session}
                print(f"Przygotowano klienta dla XTTS API: {self.tts_model['url']}")

            elif self.active_model_name == 'ElevenLabs':
                api_key = self.global_config.get('elevenlabs_api_key')
                voice_id = self.global_config.get('elevenlabs_voice_id')
                if not api_key or not voice_id:
                    raise ValueError("Klucz API lub Voice ID dla ElevenLabs nie są ustawione w Ustawieniach.")
                self.tts_model = ElevenLabsTTS(api_key=api_key, voice_id=voice_id)

            elif self.active_model_name == 'Google Cloud TTS':
                creds_path = self.global_config.get('google_credentials_path')
                voice_name = self.global_config.get('google_voice_name')
                if not creds_path or not Path(creds_path).exists():
                    raise ValueError("Ścieżka do credentials .json dla Google TTS jest nieprawidłowa lub nie istnieje.")
                self.tts_model = GoogleCloudTTS(credentials_path=creds_path, voice_name=voice_name)

            else:
                raise ValueError(f"Nieznany model TTS: {self.active_model_name}")

        except Exception as e:
            self.tts_model = None  # Resetuj w razie błędu
            # === POPRAWKA: Przekazanie 'e' do lambdy ===
            self.queue.put(lambda e=e: messagebox.showerror(
                f"Błąd modelu {self.active_model_name}",
                f"Nie udało się załadować/przygotować modelu:\n{e}",
                parent=self
            ))
            # ==========================================
            # Zniszcz okno postępu, jeśli było otwarte (np. w generate_all)
            if hasattr(self, 'progress_window') and self.progress_window:
                self.queue.put(lambda: self.progress_window.destroy())

    def _run_converter(self, is_single_file=False, single_file_path: Optional[Path] = None):
        """Initializes and runs the AudioConverter."""
        from audio.audio_converter import AudioConverter  # Import wewnątrz, aby uniknąć problemów z circular import

        if not self.audio_dir:
            print("Błąd: Katalog audio nie jest ustawiony do konwersji.")
            return

        try:
            base_speed = float(self.project_config.get('base_audio_speed', 1.1))
        except ValueError:
            base_speed = 1.1

        filter_settings = self.global_config.get('ffmpeg_filters', {})
        converter = AudioConverter(base_speed=base_speed, filter_settings=filter_settings)
        output_dir = self.audio_dir / "ready"
        os.makedirs(output_dir, exist_ok=True)

        try:
            if is_single_file and single_file_path and single_file_path.exists():
                output_file = converter.build_output_file_path(single_file_path.name, str(output_dir))
                converter.parse_ogg(str(single_file_path), output_file)
            elif not is_single_file:
                converter.convert_dir(str(self.audio_dir), str(output_dir))
        except Exception as conv_e:
            print(f"Błąd podczas konwersji audio: {conv_e}")
            self.queue.put(
                lambda e=conv_e: messagebox.showerror("Błąd konwersji", f"Wystąpił błąd podczas konwersji audio:\n{e}",
                                                      parent=self))

    def generate_selected_audio(self):
        """Starts generation for the currently selected line."""
        identifier = self._get_selected_identifier()
        if identifier is None:
            messagebox.showwarning("Brak zaznaczenia", "Najpierw wybierz linię z podglądu.", parent=self)
            return
        if not self.audio_dir:
            messagebox.showwarning("Brak katalogu", "Najpierw wybierz katalog audio w menu 'Dialogi'.", parent=self)
            return

        self.start_generate_single(identifier)

    def start_generate_single(self, identifier: str):
        """Starts the generation of a single audio file in a new thread."""
        if not self.generation_lock.acquire(blocking=False):
            self.set_status("Generowanie już w toku...")
            return

        self.cancel_event.clear()
        self.set_status(f"Rozpoczynanie generowania dla linii {identifier}...")
        threading.Thread(target=self._task_generate_single, args=(identifier,), daemon=True).start()

    def _task_generate_single(self, identifier: str):
        """Worker thread task for generating a single file."""
        output_path = None  # Zdefiniuj przed try
        try:
            # 1. Załaduj model (lub przygotuj klienta API)
            self.queue.put(lambda: self.set_status(f"Ładowanie modelu {self._get_active_tts_model_name()}..."))
            self._load_tts_model()
            if self.tts_model is None: return  # Błąd zgłoszony w _load_tts_model
            if self.cancel_event.is_set(): raise InterruptedError("Anulowano")

            # 2. Generuj TTS
            self.queue.put(lambda: self.set_status(f"Generowanie głosu dla linii {identifier}..."))
            line_index = int(identifier) - 1
            text = self.dialogs[line_index]
            output_path = self.audio_dir / f"output1 ({identifier}).wav"  # Zawsze .wav jako cel pośredni

            # --- Wywołanie TTS (API lub lokalnie) ---
            if self.active_model_name == 'XTTS':
                self._call_xtts_api(text, str(output_path))
            elif isinstance(self.tts_model, TTSBase):  # Dla modeli online
                self.tts_model.tts(text, str(output_path))
            else:
                raise TypeError("Niespodziewany typ modelu TTS.")

            if self.cancel_event.is_set(): raise InterruptedError("Anulowano")

            # 3. Konwertuj audio
            self.queue.put(lambda: self.set_status(f"Konwertowanie audio dla linii {identifier}..."))
            self._run_converter(is_single_file=True, single_file_path=output_path)

            # 4. Odśwież GUI (status)
            self.queue.put(lambda: self.set_status(f"Zakończono generowanie dla linii {identifier}."))
            # Odświeżenie przycisków nastąpi, jeśli użytkownik ponownie kliknie linię

        except InterruptedError:
            self.queue.put(lambda: self.set_status(f"Anulowano generowanie dla linii {identifier}."))
        except Exception as e:
            print(f"Błąd generowania dla linii {identifier}: {e}")
            self.queue.put(lambda e=e: messagebox.showerror("Błąd generowania", f"Wystąpił błąd: {e}", parent=self))
            self.queue.put(lambda: self.set_status(f"Błąd generowania dla linii {identifier}."))
            # Próba usunięcia nieudanego pliku .wav
            if output_path and output_path.exists():
                try:
                    os.remove(output_path)
                except OSError:
                    pass
        finally: self.generation_lock.release(); self.queue.put(self.update_audio_buttons_state)

    def start_generate_all(self):
        """Starts the generation of all missing audio files in a new thread."""
        if not self.audio_dir:
            messagebox.showwarning("Brak katalogu", "Najpierw wybierz katalog audio w menu 'Dialogi'.", parent=self)
            return
        if not self.processed_replace:
            messagebox.showwarning("Brak danych", "Najpierw przetwórz napisy przyciskiem 'Zastosuj'.", parent=self)
            return

        if not self.generation_lock.acquire(blocking=False):
            self.set_status("Generowanie już w toku...")
            return

        self.cancel_event.clear()
        self.progress_window = GenerationProgressWindow(self, self.cancel_event)
        self.set_status("Start generowania wszystkich...")
        threading.Thread(target=self._task_generate_all, daemon=True).start()

    def _task_generate_all(self):
        """Worker thread task for generating all missing files."""
        generated_count = 0
        skipped_count = 0
        total_lines = len(self.dialogs)
        dialogs_to_generate = []

        try:
            # 1. Załaduj model / Przygotuj klienta
            self.queue.put(lambda: self.progress_window.update_progress(0, total_lines,
                                                                        f"Ładowanie modelu {self._get_active_tts_model_name()}..."))
            self._load_tts_model()
            if self.tts_model is None: return  # Błąd już zgłoszony
            if self.cancel_event.is_set(): raise InterruptedError("Anulowano")

            # 2. Znajdź brakujące pliki
            for i, text in enumerate(self.dialogs):
                identifier = str(i + 1)
                # Sprawdź WAV i MP3 w katalogu głównym
                raw_wav = self.audio_dir / f"output1 ({identifier}).wav"
                raw_mp3 = self.audio_dir / f"output1 ({identifier}).mp3"
                # Sprawdź OGG w katalogu ready
                ready_ogg1 = self.audio_dir / "ready" / f"output1 ({identifier}).ogg"
                ready_ogg2 = self.audio_dir / "ready" / f"output2 ({identifier}).ogg"

                # Jeśli *żaden* z potencjalnych plików nie istnieje, dodaj do kolejki
                if not (raw_wav.exists() or raw_mp3.exists() or ready_ogg1.exists() or ready_ogg2.exists()):
                    dialogs_to_generate.append((identifier, text))
                else:
                    skipped_count += 1
                    # Aktualizuj postęp dla pominiętych
                    current_processed = skipped_count + generated_count
                    self.queue.put(
                        lambda cp=current_processed, tl=total_lines: self.progress_window.update_progress(cp, tl,
                                                                                                          f"Sprawdzanie plików... ({skipped_count} pominięto)"))

            total_to_gen = len(dialogs_to_generate)
            if not dialogs_to_generate:
                self.queue.put(lambda: self.progress_window.destroy())
                self.queue.put(
                    lambda: messagebox.showinfo("Gotowe", "Wszystkie dialogi już istnieją lub zostały przetworzone.",
                                                parent=self))
                self.queue.put(lambda: self.set_status("Generowanie: Wszystkie pliki istnieją."))
                return

            # 3. Generuj TTS (pętla)
            for i, (identifier, text) in enumerate(dialogs_to_generate):
                if self.cancel_event.is_set(): raise InterruptedError("Anulowano")

                current_processed = skipped_count + i + 1
                self.queue.put(lambda cp=current_processed, tt=total_lines, i=i + 1, tg=total_to_gen:
                               self.progress_window.update_progress(cp, tt, f"Generowanie TTS... ({i}/{tg})"))

                output_path = self.audio_dir / f"output1 ({identifier}).wav"

                # --- Wywołanie TTS (API lub lokalnie) ---
                if self.active_model_name == 'XTTS':
                    self._call_xtts_api(text, str(output_path))
                elif isinstance(self.tts_model, TTSBase):  # Modele online
                    self.tts_model.tts(text, str(output_path))
                else:
                    raise TypeError("Niespodziewany typ modelu TTS.")

                generated_count += 1  # Zliczaj tylko faktycznie wygenerowane

            # 4. Konwertuj audio (wszystkie na raz, które istnieją jako wav/mp3 w głównym katalogu)
            if self.cancel_event.is_set():
                self.queue.put(lambda: self.progress_window.set_indeterminate("Anulowano. Kończenie konwersji..."))
            else:
                self.queue.put(lambda: self.progress_window.set_indeterminate("Konwertowanie audio..."))

            self._run_converter(is_single_file=False)

            # 5. Zakończ
            self.queue.put(lambda: self.progress_window.destroy())
            final_message = f"Pomyślnie wygenerowano {generated_count} i pominięto {skipped_count} plików."
            self.queue.put(lambda msg=final_message: messagebox.showinfo("Zakończono", msg, parent=self))
            self.queue.put(lambda: self.set_status(f"Zakończono generowanie ({generated_count} nowych)."))

        except InterruptedError:
            self.queue.put(lambda: self.progress_window.destroy() if self.progress_window else None)
            self.queue.put(lambda gc=generated_count, tg=total_to_gen: messagebox.showinfo("Anulowano",
                                                                                           f"Proces generowania przerwany.\nWygenerowano {gc} z {tg} potrzebnych plików.",
                                                                                           parent=self))
            self.queue.put(lambda: self.set_status("Generowanie anulowane."))
        except Exception as e:
            print(f"Błąd podczas generowania wszystkich: {e}")
            if self.progress_window: self.queue.put(lambda: self.progress_window.destroy())
            self.queue.put(lambda e=e: messagebox.showerror("Błąd generowania", f"Wystąpił błąd: {e}", parent=self))
            self.queue.put(lambda: self.set_status("Błąd podczas generowania."))
        finally:
            self.generation_lock.release()
            # Odśwież stan przycisków po zakończeniu
            self.queue.put(self.update_audio_buttons_state)

    def _call_xtts_api(self, text: str, output_file: str):
        """Helper method to call the XTTS API server."""
        if not isinstance(self.tts_model, dict) or 'url' not in self.tts_model or 'session' not in self.tts_model:
            raise ConnectionError("Klient XTTS API nie jest poprawnie skonfigurowany.")

        api_url = self.tts_model['url']
        session = self.tts_model['session']
        voice_path = self.global_config.get('xtts_voice_path', '')  # Pobierz ścieżkę głosu

        payload = {
            "text": text,
            "output_file": output_file,
            "voice_file": voice_path  # Wyślij ścieżkę do API
        }

        try:
            response = session.post(api_url, json=payload, timeout=300)  # Timeout 5 minut
            response.raise_for_status()  # Rzuci błąd dla 4xx/5xx

            response_data = response.json()
            if not response_data.get("message", "").startswith("TTS generated successfully"):
                raise ConnectionError(
                    f"API zwróciło nieoczekiwaną odpowiedź: {response_data.get('error', response.text)}")

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Błąd połączenia z XTTS API ({api_url}): {e}")
        except json.JSONDecodeError:
            raise ConnectionError(f"Nieprawidłowa odpowiedź JSON z XTTS API: {response.text}")

if __name__ == '__main__':
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')
    app = SubtitleStudioApp()
    app.mainloop()