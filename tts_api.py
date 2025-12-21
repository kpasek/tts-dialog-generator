from app.path_utils import identity_path
from app.tts_server import run_server

if __name__ == "__main__":
    # Windows native: brak stagingu (None), brak konwersji ścieżek
    run_server(identity_path, staging_path=None)