# ============================================
# Skrypt uruchamiający TTS Dialog Generator
# ============================================

# Konfiguracja
$repoUrl = "https://github.com/kpasek/tts-dialog-generator.git"
$repoName = "tts-dialog-generator"
$pythonVersion = "python3.11"  # lub "python" jeśli masz ustawione globalnie
$venvPath = ".venv"

# Jeśli katalog repo nie istnieje – klonuj
if (-Not (Test-Path $repoName)) {
    Write-Host "📥 Klonowanie repozytorium..."
    git clone $repoUrl
} else {
    Write-Host "🔄 Repozytorium istnieje — aktualizuję..."
    Set-Location $repoName
    git pull
    Set-Location ..
}

# Wejście do repo
Set-Location $repoName

# Sprawdzenie/utworzenie wirtualnego środowiska
if (-Not (Test-Path $venvPath)) {
    Write-Host "🐍 Tworzenie wirtualnego środowiska..."
    & $pythonVersion -m venv $venvPath
}

# Aktywacja środowiska
Write-Host "✅ Aktywacja wirtualnego środowiska..."
& "$venvPath\Scripts\Activate.ps1"

# Instalacja zależności
Write-Host "📦 Instalacja zależności..."
pip install --upgrade pip
pip install -r requirements.txt

# Uruchomienie aplikacji
Write-Host "🚀 Uruchamianie aplikacji..."
python gui.py
