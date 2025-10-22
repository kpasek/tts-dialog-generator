from tkinter import messagebox
from typing import List
import re, sys, os
import importlib.util

from app.entity import PatternItem


def compile_pattern(pat: PatternItem):
    flags = re.IGNORECASE if pat.ignore_case else 0
    return re.compile(pat.pattern, flags)


def apply_remove_patterns(lines: List[str], patterns: List[PatternItem]) -> List[str]:
    try:
        compiled = [compile_pattern(p) for p in patterns]
    except Exception as e:
        messagebox.showerror("Błąd", f"Nieprawidłowy pattern:\n{e}")

        return []

    out = []
    for line in lines:
        s = line
        for i, pat in enumerate(patterns):
            s = compiled[i].sub(pat.replace, s)
        if s.strip():
            out.append(s)
    seen = set()
    uniq = []
    for l in out:
        if l not in seen:
            uniq.append(l)
            seen.add(l)
    return uniq


def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def apply_replace_patterns(lines: List[str], patterns: List[PatternItem]) -> List[str]:
    compiled = [compile_pattern(p) for p in patterns]
    out = []
    for line in lines:
        s = line
        for i, pat in enumerate(patterns):
            s = compiled[i].sub(pat.replace, s)
        out.append(s)
    return out


def is_installed(package_name: str) -> bool:
    return importlib.util.find_spec(package_name) is not None