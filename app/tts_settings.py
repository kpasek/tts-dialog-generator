TTS_PROVIDERS = {
    "xtts": {
        "name": "XTTS (offline)",
        "settings": ["voice_path"],
        "description": "Model XTTS do generowania mowy (offline)"
    },
    "stylish": {
        "name": "Stylish (offline)",
        "settings": [],
        "description": "Model Stylish do generowania mowy (offline)"
    },
    "elevenlabs": {
        "name": "ElevenLabs (online)",
        "settings": ["api_key", "voice_id"],
        "description": "ElevenLabs - wysokiej jakości synteza mowy"
    },
    "gemini": {
        "name": "Google Cloud TTS (online)",
        "settings": ["credentials_path", "voice_name", "language_code"],
        "description": "Google Cloud Text-to-Speech"
    }
}

SETTINGS_DESCRIPTIONS = {
    "voice_path": "Ścieżka do pliku głosu wzorcowego (.wav)",
    "api_key": "Klucz API dla usługi",
    "voice_id": "ID głosu do użycia",
    "credentials_path": "Ścieżka do pliku credentials.json",
    "voice_name": "Nazwa głosu do użycia",
    "language_code": "Kod języka (np. pl-PL)"
}
