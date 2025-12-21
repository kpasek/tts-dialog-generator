from app.path_utils import to_wsl_path
from app.tts_server import run_server

if __name__ == "__main__":
    run_server(to_wsl_path)