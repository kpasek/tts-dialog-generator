from __future__ import annotations

import os.path

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import csv
import json
import sys
import os  # sys i os są potrzebne do close_project
from typing import List, Optional
from pathlib import Path

import threading

from app.settings import SettingsWindow
from app.utils import apply_remove_patterns, apply_replace_patterns, resource_path, is_installed

if is_installed('torch'):
    from generators.xtts import XTTSPolishTTS


from app.entity import PatternItem
from app.tooltip import CreateToolTip

from customtkinter import CTkFrame, CTkScrollableFrame

from audio.browser import AudioBrowserWindow
from audio.deleter import AudioDeleterWindow

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


class SubtitleStudioApp(ctk.CTk):
    """
    Main application class for Subtitle Studio.
    Handles the main window, UI components, file operations, and project management.
    """

    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.has_unsaved_changes = False

        self.title(APP_TITLE)
        self.geometry("1600x1000")
        try:
            self.iconphoto(False, tk.PhotoImage(file=resource_path("assets/icon512.png")))
        except Exception:
            pass

        self.loaded_path: Optional[Path] = None
        self.original_lines: List[str] = []

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

        self.processed_clean: List[str] = []
        self.processed_replace: List[str] = []

        self.project_config = {}
        self.global_config = {}

        # === ZMIANA: Sprawdzenie instalacji Torcha ===
        self.torch_installed = is_installed('torch')
        if not self.torch_installed:
            print("Ostrzeżenie: Pakiet 'torch' nie jest zainstalowany. Model XTTS będzie niedostępny.")
        # ===========================================

        # Model TTS (dla XTTS) jest ładowany tylko raz
        self.tts_model = None
        self.generation_lock = threading.Lock()
        self.cancel_generation_event = threading.Event()

        self._create_menu()
        self._create_widgets()
        self._load_app_config()

    def mark_as_unsaved(self, *args):
        """Flags the current project as having unsaved changes."""
        self.has_unsaved_changes = True
        if "Gotowy" in self.status.cget("text"):
            self.set_status("Gotowy (niezapisane zmiany)")

    def _create_menu(self):
        """Creates the main application menu bar."""
        menubar = tk.Menu(self)
        config_menu = tk.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Otwórz projekt", command=self.open_project)
        config_menu.add_command(label="Zapisz projekt", command=self.save_project)
        config_menu.add_command(label="Zapisz jako...", command=self.save_project_as)
        config_menu.add_separator()
        config_menu.add_command(label="Zamknij projekt", command=self.close_project)
        config_menu.add_separator()
        config_menu.add_command(label="Ustawienia", command=self.open_settings_window)
        config_menu.add_separator()
        config_menu.add_command(label="Zamknij", command=self.on_close)  # Zmienione na on_close
        menubar.add_cascade(label="Projekt", menu=config_menu)

        gen_menu = tk.Menu(menubar, tearoff=0)
        gen_menu.add_command(label="Przeglądaj/Generuj dialogi", command=self.audio_preview)
        gen_menu.add_separator()
        gen_menu.add_command(label="Masowe usuwanie dialogów", command=self.open_audio_deleter)
        menubar.add_cascade(label="Dialogi", menu=gen_menu)

        self.config(menu=menubar)

    def _create_widgets(self):
        """Creates and places all main UI widgets in the window."""
        root_grid = ctk.CTkFrame(self)
        root_grid.pack(fill="both", expand=True, padx=10, pady=10)
        root_grid.grid_rowconfigure(0, weight=1)
        root_grid.grid_columnconfigure(2, weight=1)

        # LEFT: built-in patterns
        left = ctk.CTkFrame(root_grid, width=MAX_COL_WIDTH)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        left.grid_rowconfigure(4, weight=1)

        file_frame = ctk.CTkFrame(left)
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.lbl_filename = ctk.CTkLabel(file_frame, text="Brak wczytanego pliku")
        self.lbl_filename.pack(side="left", padx=(5, 10))
        ctk.CTkButton(file_frame, text="Wczytaj", command=self.load_file).pack(side="right", padx=5)

        ctk.CTkLabel(left, text="Wbudowane wzorce wycinające").grid(row=1, column=0, sticky="we", padx=6)
        self._create_builtin_list(left, self.builtin_remove, self.builtin_remove_state, 2)

        ctk.CTkLabel(left, text="Wbudowane wzorce podmieniające").grid(row=3, column=0, sticky="we", padx=6)
        self._create_builtin_list(left, self.builtin_replace, self.builtin_replace_state, 4)

        # CENTER
        self.center_frame = ctk.CTkFrame(root_grid, width=500)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self.center_frame, text="Własne wzorce wycinające").grid(row=0, column=0, sticky="w", padx=6)
        self.custom_remove_frame = ctk.CTkScrollableFrame(self.center_frame)
        self.custom_remove_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 6))

        clean_inline_frame = self.build_clean_list_frame(2)
        self.ent_remove_pattern = ctk.CTkEntry(clean_inline_frame, placeholder_text="regexp")
        self.ent_remove_pattern.pack(side="left", fill="x", expand=True, padx=(4, 2))
        self.ent_remove_replace = ctk.CTkEntry(clean_inline_frame, placeholder_text="zamień na")
        self.ent_remove_replace.pack(side="left", fill="x", expand=True, padx=(2, 2))
        self.var_remove_ignore = tk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(clean_inline_frame, text="Aa", variable=self.var_remove_ignore)
        checkbox.pack(side="left", padx=(2, 4))
        CreateToolTip(checkbox, 'Uwzględnij wielkość znaków')
        ctk.CTkButton(clean_inline_frame, text="Dodaj", command=self.add_inline_remove).pack(side="left", padx=2)

        replace_top_frame = ctk.CTkFrame(self.center_frame)
        replace_top_frame.grid(row=3, column=0, sticky="ew", pady=(4, 4))
        lab = ctk.CTkLabel(replace_top_frame, text="Własne wzorce podmieniające")
        lab.pack(side="left", anchor="w", fill="x", expand=False, padx=6)
        ctk.CTkButton(replace_top_frame, text="Importuj", command=self.import_patterns_from_csv).pack(side="right")

        self.custom_replace_frame = ctk.CTkScrollableFrame(self.center_frame)
        self.custom_replace_frame.grid(row=4, column=0, sticky="nsew", padx=6, pady=(2, 6))

        replace_inline_frame = self.build_clean_list_frame(5)
        self.ent_replace_pattern = ctk.CTkEntry(replace_inline_frame, placeholder_text="regexp")
        self.ent_replace_pattern.pack(side="left", fill="x", expand=True, padx=(4, 2))
        self.ent_replace_replace = ctk.CTkEntry(replace_inline_frame, placeholder_text="zamień na")
        self.ent_replace_replace.pack(side="left", fill="x", expand=True, padx=(2, 2))
        self.var_replace_ignore = tk.BooleanVar(value=False)
        ignore_checkbox = ctk.CTkCheckBox(replace_inline_frame, text="Aa", variable=self.var_replace_ignore)
        ignore_checkbox.pack(side="left", padx=(2, 4))
        CreateToolTip(ignore_checkbox, 'Uwzględnij wielkość znaków')
        ctk.CTkButton(replace_inline_frame, text="Dodaj", command=self.add_inline_replace).pack(side="left", padx=2)

        # RIGHT: stats + apply + download buttons
        right = ctk.CTkFrame(root_grid)
        right.grid(row=0, column=2, sticky="nsew")

        self.lbl_count_orig = ctk.CTkLabel(right, text="Linie oryginalne: 0")
        self.lbl_count_orig.pack(anchor="w", pady=(6, 2))
        self.lbl_count_after = ctk.CTkLabel(right, text="Linie po zastosowaniu: 0")
        self.lbl_count_after.pack(anchor="w", pady=(0, 8))

        ctk.CTkButton(right, text="Zastosuj", command=self.apply_processing).pack(anchor="w")

        self.btn_download_clean = ctk.CTkButton(right, text="Pobierz - napisy dla Game Reader",
                                                command=self.download_clean)
        self.btn_download_replace = ctk.CTkButton(right, text="Pobierz - napisy dla TTS", command=self.download_replace)
        self.btn_download_clean.pack_forget()
        self.btn_download_replace.pack_forget()

        search_frame = ctk.CTkFrame(right)
        search_frame.pack(anchor="w", pady=(6, 2), padx=6, fill="x")

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Przeszukaj podgląd")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda event: self.apply_patterns())
        self.search_entry.bind("<Control-BackSpace>", lambda event: self.search_entry.delete(0, tk.END))

        self.search_button = ctk.CTkButton(search_frame, text="Szukaj", command=self.apply_patterns)
        self.search_button.pack(side="left", padx=(6, 0))

        ctk.CTkLabel(right, text="Podgląd:").pack(anchor="w", padx=6)
        self.txt_preview = ctk.CTkTextbox(right)
        self.txt_preview.configure(state=tk.DISABLED)
        self.txt_preview.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.status = ctk.CTkLabel(self, text="Gotowy", anchor="w")
        self.status.pack(fill="x", side="bottom")

    def build_clean_list_frame(self, row_nr) -> CTkFrame:
        """Helper to create a standard input frame for patterns."""
        clean_inline_frame = ctk.CTkFrame(self.center_frame)
        clean_inline_frame.grid(row=row_nr, column=0, sticky="ew", pady=(4, 4))
        return clean_inline_frame

    def build_scroll_list_frame(self, row_nr) -> CTkScrollableFrame:
        """Helper to create a standard scrollable frame."""
        scroll_frame = ctk.CTkScrollableFrame(self.center_frame)
        scroll_frame.grid(row=row_nr, column=0, sticky="ew", pady=(4, 4))
        return scroll_frame

    def _create_builtin_list(self, parent, patterns, states, row_nr):
        """Populates a scrollable frame with built-in pattern checkboxes."""
        sc = ctk.CTkScrollableFrame(parent)
        sc.grid(sticky="nsew", padx=6, pady=(0, 6), row=row_nr)
        for i, p in enumerate(patterns):
            text = f"{p.pattern} -> {p.replace}" if p.name is None else p.name
            cb = ctk.CTkCheckBox(sc, text=text, variable=states[i])
            cb.pack(anchor="w", pady=2)

    def add_inline_remove(self):
        """Adds a new custom 'remove' pattern from the input fields."""
        pattern = self.ent_remove_pattern.get()
        replace = self.ent_remove_replace.get()
        case_sensitive = self.var_remove_ignore.get()
        if not pattern:
            return

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
        if not pattern:
            return

        new_pattern = PatternItem(pattern, replace, not case_sensitive)
        self.custom_replace.append(new_pattern)
        self.add_row(self.custom_replace_frame, new_pattern, self.custom_replace)
        self.mark_as_unsaved()

        self.ent_replace_pattern.delete(0, "end")
        self.ent_replace_replace.delete(0, "end")

    def add_row(self, frame, pattern_item: PatternItem, target_list: List[PatternItem]):
        """
        Adds a new row representing a pattern to a given frame.

        Args:
            frame: The parent CTkScrollableFrame.
            pattern_item: The PatternItem data object.
            target_list: The list (self.custom_remove or self.custom_replace) to remove the item from.
        """
        row = ctk.CTkFrame(frame)
        row.pack(fill="x", pady=2, padx=2)

        lbl_text = f"[{pattern_item.pattern}] -> [{pattern_item.replace}] {'' if pattern_item.ignore_case else '(Aa)'}"
        lbl = ctk.CTkLabel(row, text=lbl_text)
        lbl.pack(side="left", fill="x", expand=False, padx=4)

        def on_delete():
            try:
                target_list.remove(pattern_item)
            except ValueError:
                print(f"Ostrzeżenie: Nie znaleziono {pattern_item} na liście {target_list}")
                pass
            row.destroy()
            self.mark_as_unsaved()  # Mark as unsaved on delete

        btnX = ctk.CTkButton(row, text="X", width=60, command=on_delete)
        btnX.pack(side="right", padx=4)

    def load_file(self, path: Optional[str] = None):
        """Loads a subtitle .txt file into the application."""
        if not path:
            initial_dir = self.global_config.get('start_directory')
            if not initial_dir and os.path.exists("subtitles"):
                initial_dir = "subtitles"
            path = filedialog.askopenfilename(title="Wybierz plik napisów",
                                              filetypes=[("Text files", "*.txt"), ("All files", "*")],
                                              initialdir=initial_dir)
        if not path:
            return

        # === ZMIANA: Sprawdź niezapisane zmiany ===
        if not self._check_unsaved_changes():
            return  # Anulowano
        # ========================================

        self.loaded_path = Path(path)
        self.lbl_filename.configure(text=str(self.loaded_path.name))
        try:
            with open(self.loaded_path, "r", encoding="utf-8", errors="replace") as f:
                self.original_lines = f.read().splitlines()
            self.apply_patterns()
            self.set_status(f"Wczytano {len(self.original_lines)} linii")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{e}")

    def open_project(self, path: str | None = None):
        """Opens a .json project file and loads its settings."""
        if path is None:
            # === ZMIANA: Sprawdź niezapisane zmiany ===
            if not self._check_unsaved_changes():
                return  # Anulowano
            # ========================================
            initial_dir = self.global_config.get('start_directory')
            path = filedialog.askopenfilename(title="Otwórz projekt",
                                              filetypes=[("JSON", "*.json"), ("All", "*")],
                                              initialdir=initial_dir)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for i, val in enumerate(cfg.get("builtin_remove_state", [])):
                if i < len(self.builtin_remove_state):
                    self.builtin_remove_state[i].set(bool(val))
            for i, val in enumerate(cfg.get("builtin_replace_state", [])):
                if i < len(self.builtin_replace_state):
                    self.builtin_replace_state[i].set(bool(val))
            self.custom_remove = [PatternItem.from_json(x) for x in cfg.get("custom_remove", [])]
            self.custom_replace = [PatternItem.from_json(x) for x in cfg.get("custom_replace", [])]
            self._refresh_custom_lists()
            self.current_project_path = Path(path)

            subtitle_path = cfg.get("subtitle_path")
            if subtitle_path and Path(subtitle_path).exists():
                self.load_file(subtitle_path)

            self.set_status("Wczytano projekt")
            self.save_app_setting('last_project', path)
            self.project_config = cfg
            self.has_unsaved_changes = False  # Świeżo załadowany projekt jest "zapisany"
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać konfiguracji:\n{e}")

    def close_project(self):
        """Closes the current project and restarts the application to a clean state."""
        # === ZMIANA: Sprawdź niezapisane zmiany ===
        if not self._check_unsaved_changes():
            return  # Anulowano
        # ========================================
        try:
            self.save_app_setting('last_project', None)
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            messagebox.showerror("Błąd restartu",
                                 f"Nie udało się zrestartować aplikacji:\n{e}\n\nProszę zamknąć i otworzyć program ręcznie.")

    def set_project_config(self, param, value):
        """Saves a single key-value pair to the current project configuration."""
        cfg = self._gather_project_config()
        cfg[param] = value
        self.save_project(cfg)  # save_project ustawia has_unsaved_changes na False

    def save_project(self, cfg: dict | None = None):
        """Saves the current configuration to the loaded project file."""
        if not self.current_project_path:
            return self.save_project_as()
        cfg = self._gather_project_config() if cfg is None else cfg
        self.project_config = cfg
        try:
            with open(self.current_project_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            self.set_status(f"Zapisano projekt: {self.current_project_path.name}")
            self.has_unsaved_changes = False
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać konfiguracji:\n{e}")

    def save_project_as(self):
        """Saves the current configuration to a new .json project file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialdir=self.global_config.get('start_directory')
        )
        if not path:
            return
        self.current_project_path = Path(path)
        self.save_project()

    def _gather_project_config(self) -> dict:
        """Collects all current project settings into a dictionary."""
        current_cfg = self.project_config.copy()
        current_cfg.update({
            "builtin_remove_state": [bool(v.get()) for v in self.builtin_remove_state],
            "builtin_replace_state": [bool(v.get()) for v in self.builtin_replace_state],
            "custom_remove": [p.to_json() for p in self.custom_remove],
            "custom_replace": [p.to_json() for p in self.custom_replace],
            "subtitle_path": str(self.loaded_path) if self.loaded_path else None,
            "audio_path": self.project_config.get('audio_path'),
            "active_tts_model": self.project_config.get('active_tts_model', 'XTTS' if self.torch_installed else None),
            "base_audio_speed": self.project_config.get('base_audio_speed', 1.1)
        })
        return current_cfg

    def _load_app_config(self):
        """Loads the global application configuration from .subtitle_studio_config.json."""
        if APP_CONFIG.exists():
            try:
                with open(APP_CONFIG, "r", encoding="utf-8") as f:
                    self.global_config = json.load(f)
                if self.global_config.get('last_project'):
                    self.open_project(self.global_config.get('last_project'))
            except Exception:
                pass  # Ignore errors, load defaults

    def filter_preview(self, lines: List[str]) -> List[str]:
        """Filters the preview text box based on the search entry."""
        if not self.search_entry.get():
            return lines
        filtered = []
        for line in lines:
            if re.compile(f".*{self.search_entry.get()}.*", flags=re.IGNORECASE).match(line):
                filtered.append(line)
        return filtered

    def _refresh_custom_lists(self):
        """Destroys and recreates the custom pattern lists in the UI."""
        if hasattr(self, 'custom_remove_frame'):
            self.custom_remove_frame.destroy()
        if hasattr(self, 'custom_replace_frame'):
            self.custom_replace_frame.destroy()

        self.custom_remove_frame = self.build_scroll_list_frame(1)
        self.custom_remove_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 6))
        for p in self.custom_remove:
            self.add_row(self.custom_remove_frame, p, self.custom_remove)

        self.custom_replace_frame = self.build_scroll_list_frame(4)
        self.custom_replace_frame.grid(row=4, column=0, sticky="nsew", padx=6, pady=(2, 6))
        for p in self.custom_replace:
            self.add_row(self.custom_replace_frame, p, self.custom_replace)

    def _gather_active_patterns(self) -> tuple[List[PatternItem], List[PatternItem]]:
        """Collects all active built-in and custom patterns."""
        remove_patterns = []
        remove_patterns.extend(self.custom_remove)
        for i, p in enumerate(self.builtin_remove):
            if self.builtin_remove_state[i].get():
                remove_patterns.append(p)

        replace_patterns = []
        replace_patterns.extend(self.custom_replace)
        for i, p in enumerate(self.builtin_replace):
            if self.builtin_replace_state[i].get():
                replace_patterns.append(p)

        return remove_patterns, replace_patterns

    def apply_processing(self):
        """Applies all active patterns to the loaded subtitles."""
        if not self.original_lines:
            messagebox.showwarning('Brak pliku', 'Najpierw wczytaj plik z napisami.')
            return

        self.apply_patterns()

        # Pokazanie przycisków pobierania
        self.btn_download_clean.pack(fill='x', padx=6, pady=(6, 3))
        self.btn_download_replace.pack(fill='x', padx=6, pady=(0, 6))

        self.set_status('Przetworzono napisy — gotowe do pobrania')

    def download_clean(self):
        """Saves the 'clean' (for Game Reader) subtitles to a file."""
        if not getattr(self, 'processed_clean', None):
            messagebox.showwarning('Brak danych', 'Brak oczyszczonych linii. Najpierw przetwórz plik.')
            return
        path = filedialog.asksaveasfilename(title='Zapisz oczyszczone napisy', defaultextension='.txt',
                                            filetypes=[('Text files', '*.txt')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.processed_clean))
            messagebox.showinfo('Gotowe', f'Zapisano oczyszczone napisy:\n{path}')
            self.set_status(f'Zapisano oczyszczone napisy: {Path(path).name}')
        except Exception as e:
            messagebox.showerror('Błąd zapisu', str(e))

    def download_replace(self):
        """Saves the 'replaced' (for TTS) subtitles to a file."""
        if not getattr(self, 'processed_replace', None):
            messagebox.showwarning('Brak danych', 'Brak zamienionych linii. Najpierw przetwórz plik.')
            return
        path = filedialog.asksaveasfilename(title='Zapisz napisy z podmianami', defaultextension='.txt',
                                            filetypes=[('Text files', '*.txt')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.processed_replace))
            messagebox.showinfo('Gotowe', f'Zapisano napisy z podmianami:\n{path}')
            self.set_status(f'Zapisano napisy z podmianami: {Path(path).name}')
        except Exception as e:
            messagebox.showerror('Błąd zapisu', str(e))

    def apply_patterns(self):
        """Internal method to re-calculate processed lines and update the preview."""
        self.lbl_count_orig.configure(text=f'Linie oryginalne: {len(self.original_lines)}')
        rem_patterns, rep_patterns = self._gather_active_patterns()

        try:
            self.processed_clean = apply_remove_patterns(self.original_lines, rem_patterns)
            self.processed_replace = apply_replace_patterns(self.processed_clean, rep_patterns)
        except re.error as e:
            messagebox.showerror('Błąd regex', f'Błąd w wyrażeniu regularnym:\n{e}')
            return
        self.lbl_count_after.configure(text=f'Linie po zastosowaniu: {len(self.processed_clean)}')

        self.set_preview(self.processed_replace)

    def set_preview(self, cleaned: list[str]):
        """Updates the read-only preview text box with numbered lines."""
        total_lines = len(cleaned)
        num_digits = len(str(total_lines)) if total_lines > 0 else 1
        numbered_lines = [
            f"{str(i + 1).zfill(num_digits)} | {line}"
            for i, line in enumerate(cleaned)
        ]

        filtered = self.filter_preview(numbered_lines)

        self.txt_preview.configure(state='normal')
        self.txt_preview.delete('0.0', tk.END)
        self.txt_preview.insert('0.0', '\n'.join(filtered))
        self.txt_preview.configure(state='disabled')

    def set_status(self, txt: str):
        """Updates the bottom status bar label."""
        self.status.configure(text=txt)

    def audio_preview(self):
        """Opens the Audio Browser window."""
        if not self.processed_replace:
            messagebox.showwarning("Brak danych", "Najpierw przetwórz dialogi, aby zobaczyć podgląd.")
            return

        project_cfg = self._gather_project_config()

        # === ZMIANA: Walidacja modelu TTS ===
        active_model = project_cfg.get('active_tts_model')
        if not active_model:
            messagebox.showwarning("Brak modelu TTS",
                                   "Nie wybrano aktywnego modelu TTS w Ustawieniach Projektu.",
                                   parent=self)
            return

        if active_model == 'XTTS' and not self.torch_installed:
            messagebox.showerror("Błąd XTTS",
                                 "Model XTTS jest wybrany, ale pakiet 'torch' nie jest zainstalowany.\nZainstaluj 'torch' lub wybierz inny model w Ustawieniach.",
                                 parent=self)
            return
        # ====================================

        win = AudioBrowserWindow(
            self,
            project_cfg,
            self.set_project_config,
            self.cancel_generation_event,
            self.global_config,  # Przekaż globalną konfigurację
            active_model  # Przekaż nazwę aktywnego modelu
        )
        # === ZMIANA: Ustawienie modalności (grab_set) ===
        win.grab_set()
        win.lift()
        win.focus_force()
        # ==============================================

    def open_audio_deleter(self):
        """Opens the Batch Audio Deleter window."""
        if not self.processed_replace:
            messagebox.showwarning("Brak danych", "Najpierw przetwórz dialogi (Zastosuj).", parent=self)
            return
        if not self.project_config.get("audio_path"):
            messagebox.showwarning("Brak katalogu", "Najpierw ustaw katalog audio w przeglądarce dialogów.",
                                   parent=self)
            return

        deleter_win = AudioDeleterWindow(self, self.processed_replace, self.project_config.get("audio_path"))
        deleter_win.grab_set()  # Okno modalne

    def open_settings_window(self):
        """Opens the Settings window."""
        # === ZMIANA: Przekaż flagę instalacji torcha ===
        win = SettingsWindow(self, self.torch_installed)
        # =============================================
        win.grab_set()

    def import_patterns_from_csv(self):
        """Imports 'replace' patterns from a 2-column CSV file."""
        initial_dir = self.global_config.get('start_directory')
        file_path = filedialog.askopenfilename(
            title="Wybierz plik CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=initial_dir
        )
        if not file_path:
            return

        try:
            count = 0
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    pattern = row[0]
                    if not pattern:
                        continue
                    replace = row[1] if len(row) > 1 else ""
                    case_sensitive = bool(int(row[2])) if len(row) > 2 and row[2].isdigit() else False

                    new_pattern = PatternItem(pattern, replace, not case_sensitive)
                    self.custom_replace.append(new_pattern)
                    self.add_row(self.custom_replace_frame, new_pattern, self.custom_replace)
                    count += 1

            self.mark_as_unsaved()
            messagebox.showinfo("Import zakończony", f"Zaimportowano {count} wzorców.")
        except Exception as e:
            messagebox.showerror("Błąd importu", f"Nie udało się zaimportować pliku:\n{e}")

    def save_global_config(self, new_config_data: dict):
        """Saves data to the global .subtitle_studio_config.json file."""
        self.global_config.update(new_config_data)
        try:
            with open(APP_CONFIG.absolute(), "w", encoding="utf-8") as f:
                json.dump(self.global_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać globalnej konfiguracji: {e}")

    def save_app_setting(self, param, value):
        """Saves a single key-value pair to the global config file."""
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

            if result is True:  # Tak
                self.save_project()
            elif result is None:  # Anuluj
                return False
            # Jeśli Nie, kontynuuj bez zapisywania
        return True

    def on_close(self):
        """Handles the application window close event."""
        if self._check_unsaved_changes():
            self.destroy()


if __name__ == '__main__':
    ctk.set_appearance_mode('System')
    ctk.set_default_color_theme('blue')
    app = SubtitleStudioApp()
    app.mainloop()