import os
from app.path_utils import to_wsl_path
from app.tts_server import run_server

if __name__ == "__main__":
    # Definiujemy katalog wewnątrz WSL (szybki system plików)
    # expanduser zamienia ~ na /home/użytkownik
    staging_path = os.path.expanduser("~/tts_output")
    
    # Uruchamiamy serwer z konwerterem ścieżek I katalogiem staging
    run_server(to_wsl_path, staging_path=staging_path)