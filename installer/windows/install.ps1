# Installer PowerShell per WhisperGUI (Windows)
# Uso: .\install.ps1 [-InstallDir <path>]

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\WhisperGUI"
)

$ExeName = "WhisperGUI-x86_64.exe"
$DestPath = "$InstallDir\WhisperGUI.exe"

if (-not (Test-Path $ExeName)) {
    Write-Error "$ExeName non trovato. Scaricalo da: https://github.com/lorenzo0932/whisper_project/releases"
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $ExeName $DestPath -Force

# Aggiungi al PATH utente
$paths = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($paths -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$paths;$InstallDir", "User")
}

Write-Host "✅ WhisperGUI installato in $DestPath"
Write-Host "Puoi avviarlo con: WhisperGUI.exe"
Write-Host "Oppure cerca 'WhisperGUI' nel menu Start (dopo aver riaperto la sessione)."
