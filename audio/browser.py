import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os, re
from pathlib import Path
import pygame


class AudioBrowserWindow(ctk.CTkToplevel):
    def __init__(self, master, project_config: dict, save_project_config):
        super().__init__(master)
        self.save_project_config = save_project_config
        self.title("Przeglądaj dialogi")
        self.geometry(master.geometry())  # dziedziczy rozmiar
        self.project_config = project_config

        if project_config.get('audio_path'):
            self.audio_dir = Path(project_config.get("audio_path"))
        else:
            self.choose_audio_dir()
            self.save_project()

        self.dialogs = master.processed_replace
        self.filtered_indices = []  # mapowanie widocznych pozycji na indeksy oryginalne
        self.current_identifier = None
        pygame.mixer.init()

        self._create_widgets()

    # =====================
    # UI
    # =====================
    def _create_widgets(self):
        root = ctk.CTkFrame(self)
        root.pack(fill="both", expand=True, padx=10, pady=10)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # === LEWY PANEL ===
        left = ctk.CTkFrame(root)
        left.grid(row=0, column=0, sticky="nswe", padx=(0, 10))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Dialogi").grid(row=0, column=0, sticky="we", pady=4)
        self.search_entry = ctk.CTkEntry(left, placeholder_text="Szukaj...")
        self.search_entry.grid(row=1, column=0, sticky="we", padx=4, pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_dialog_list())

        self.dialog_list = tk.Listbox(left)
        self.dialog_list.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        self.dialog_list.bind("<<ListboxSelect>>", self.on_select_dialog)
        self.dialog_list.bind("<Double-Button-1>", self.on_double_click_dialog)

        self.refresh_dialog_list()

        # === PRAWY PANEL ===
        right = ctk.CTkFrame(root, width=500)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        top_frame = ctk.CTkFrame(right)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(top_frame, text="Wybierz katalog audio", command=self.choose_audio_dir).pack(side="left", padx=4)

        # przewijalna lista bloków audio
        self.audio_scroll = ctk.CTkScrollableFrame(right)
        self.audio_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

    # =====================
    # DIALOGS
    # =====================
    def refresh_dialog_list(self):
        """Aktualizuje listę widocznych dialogów i zapisuje mapowanie indeksów."""
        pattern = self.search_entry.get().lower()
        self.dialog_list.delete(0, tk.END)
        self.filtered_indices = []

        self.filtered_indices = []
        self.dialog_list.delete(0, tk.END)

        for i, line in enumerate(self.dialogs):
            if not pattern:
                match = True
            else:
                try:
                    match = re.search(pattern, line, re.IGNORECASE)
                except re.error:
                    match = False
            if match:
                self.dialog_list.insert(tk.END, f"{i + 1}: {line}")
                self.filtered_indices.append(i)

    def on_select_dialog(self, event):
        if not self.dialog_list.curselection():
            return
        list_index = self.dialog_list.curselection()[0]
        original_index = self.filtered_indices[list_index]
        self.current_identifier = str(original_index + 1)
        self.load_audio_files(self.current_identifier)

    def on_double_click_dialog(self, event):
        """Dwuklik na dialog odtwarza pierwszy plik audio (z pełnej listy, nie filtrowanej)."""
        if not self.dialog_list.curselection():
            return
        list_index = self.dialog_list.curselection()[0]
        original_index = self.filtered_indices[list_index]
        identifier = str(original_index + 1)
        files = self._find_audio_files(identifier)
        if files:
            self.play_audio(files[0][0])

    # =====================
    # AUDIO
    # =====================
    def _find_audio_files(self, identifier: str):
        candidates = [
            (self.audio_dir / f"output1 ({identifier}).wav", False),
            (self.audio_dir / f"output1 ({identifier}).ogg" , False),
            (self.audio_dir / "ready" / f"output1 ({identifier}).ogg", True),
            (self.audio_dir / "ready" / f"output2 ({identifier}).ogg", True)
        ]
        return [(f,ready) for f, ready in candidates if f.exists()]

    def load_audio_files(self, identifier: str):
        """Tworzy listę plików audio jako bloki z labelami i przyciskami."""
        for widget in self.audio_scroll.winfo_children():
            widget.destroy()

        found = self._find_audio_files(identifier)

        if not found:
            block = ctk.CTkFrame(self.audio_scroll)
            block.pack(fill="x", pady=4, padx=6)
            ctk.CTkLabel(block, text="(Brak plików — można wygenerować)").pack(side="left", padx=6)
            ctk.CTkButton(block, text="Generuj", width=100, command=lambda: self.generate_audio(identifier)).pack(side="right", padx=6)
        else:
            for file, ready in found:
                self._create_audio_block(file,ready)

    def _create_audio_block(self, file: Path, ready =False):
        block = ctk.CTkFrame(self.audio_scroll)
        block.pack(fill="x", pady=4, padx=6)
        file_name = ("ready/" if ready else "") + str(file.name)
        lbl = ctk.CTkLabel(block, text=file_name, anchor="w")
        lbl.pack(fill="x", padx=6, pady=(4, 2))

        btn_frame = ctk.CTkFrame(block)
        btn_frame.pack(fill="x", padx=6, pady=(0, 4))

        ctk.CTkButton(btn_frame, text="▶️ Odtwórz", width=80, command=lambda f=file: self.play_audio(f)).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="❌ Usuń", width=80, command=lambda f=file: self.delete_audio(f)).pack(side="left", padx=4)

    def play_audio(self, file: Path, speed: float = 1.0):
        if not file.exists():
            return
        try:
            pygame.mixer.music.load(str(file))
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Błąd odtwarzania", str(e))

    def generate_audio(self, identifier: str):
        messagebox.showinfo("Generuj", f"Tu można dodać generowanie audio dla {identifier}")

    def delete_audio(self, file: Path):
        self.lift()
        self.focus_force()
        if os.path.exists(file) and messagebox.askyesno("Potwierdź", f"Usunąć plik?\n{file}", parent=self):
            os.remove(file)
            self.load_audio_files(self.current_identifier)

    # =====================
    # KONFIGURACJA
    # =====================
    def choose_audio_dir(self):
        """Zawsze pokazuje dialog nad głównym oknem."""
        self.lift()
        self.focus_force()
        path = filedialog.askdirectory(title="Wybierz katalog audio", parent=self)
        if path:
            self.audio_dir = Path(path)
            self.save_project()

    def save_project(self):
        abs_dir = str(self.audio_dir.absolute())
        self.project_config["audio_path"] = abs_dir
        self.save_project_config('audio_path', abs_dir)
