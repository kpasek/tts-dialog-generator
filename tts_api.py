from app.path_utils import identity_path
from app.tts_server import run_server

if __name__ == "__main__":
    run_server(identity_path)