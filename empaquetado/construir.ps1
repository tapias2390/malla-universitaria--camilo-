# Construye el ejecutable y el instalador .msi de "Transición de Mallas".
#
# Requisitos (una sola vez):
#   .venv\Scripts\python -m pip install pyinstaller==6.11.1 pillow==11.0.0
#   dotnet tool install --global wix --version 5.0.2
#
# Uso (desde la raíz del proyecto, en PowerShell):
#   powershell -ExecutionPolicy Bypass -File empaquetado\construir.ps1 [-Version 2.0.2]
#   (cada instalador nuevo debe tener una versión MAYOR para reemplazar al anterior)
#
# Resultado:
#   dist\TransicionMallas\TransicionMallas.exe   (versión portable: se puede copiar la carpeta)
#   dist\TransicionMallas-<versión>.msi           (instalador)
param([string]$Version = "2.0.2")
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host "1/3 Ícono..." -ForegroundColor Cyan
if (Test-Path empaquetado\escudo_unal.png) {
    # Escudo coloreado (también se copia como ícono de la página web)
    & .venv\Scripts\python.exe empaquetado\icono_escudo.py empaquetado\escudo_unal.png
    Copy-Item empaquetado\icono_vista_previa.png app\presentation\web\icono.png -Force
} else {
    & .venv\Scripts\python.exe empaquetado\generar_icono.py
}

Write-Host "2/3 Ejecutable (PyInstaller)..." -ForegroundColor Cyan
& .venv\Scripts\pyinstaller.exe empaquetado\transicion_mallas.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "Falló PyInstaller" }

Write-Host "3/3 Instalador (WiX)..." -ForegroundColor Cyan
$wix = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"
if (-not (Test-Path $wix)) { $wix = "wix" }
$msi = "dist\TransicionMallas-$Version.msi"
& $wix build empaquetado\instalador.wxs -arch x64 -d "Version=$Version" -d "Origen=$raiz\dist\TransicionMallas" -b empaquetado -o $msi
if ($LASTEXITCODE -ne 0) { throw "Falló WiX" }

Write-Host "`nListo:" -ForegroundColor Green
Write-Host "  Portable:    dist\TransicionMallas\TransicionMallas.exe"
Write-Host "  Instalador:  $msi"
