import re

def to_wsl_path(windows_path: str) -> str:
    """
    Konwertuje ścieżkę Windows (np. D:\\folder\\plik.wav) na ścieżkę WSL (np. /mnt/d/folder/plik.wav).
    Jeśli ścieżka nie pasuje do wzorca dysku, zamienia tylko backslashe.
    """
    if not windows_path:
        return windows_path
        
    # Sprawdź, czy ścieżka zaczyna się od litery dysku (np. C:, D:)
    match = re.match(r'^([a-zA-Z]):', windows_path)
    if match:
        drive = match.group(1).lower()
        # Usuń literę dysku i dwukropek, zamień backslashe na slashe
        rest_of_path = windows_path[2:].replace('\\', '/')
        return f"/mnt/{drive}{rest_of_path}"
    
    # Jeśli to nie jest pełna ścieżka z dyskiem, zwróć tylko z poprawionymi slashami
    return windows_path.replace('\\', '/')

def identity_path(path: str) -> str:
    """
    Zwraca ścieżkę bez zmian (dla natywnego Windowsa).
    """
    return path