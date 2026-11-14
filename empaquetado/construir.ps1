# Construye el ejecutable y el instalador .msi de "Transición de Mallas".
#
# Requisitos (una sola vez):
#   .venv\Scripts\python -m pip install pyinstaller==6.11.1
#   dotnet tool install --global wix --version 5.0.2
#
# Uso (desde la raíz del proyecto, en PowerShell):
#   powershell -ExecutionPolicy Bypass -File empaquetado\construir.ps1 [-Version 2.0.0]
#
# Resultado:
#   dist\TransicionMallas\TransicionMallas.exe   (versión portable: se puede copiar la carpeta)
#   dist\TransicionMallas-<versión>.msi           (instalador)
param([string]$Version = "2.0.1")
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

Write-Host "1/3 Ícono..." -ForegroundColor Cyan
& .venv\Scripts\python.exe empaquetado\generar_icono.py

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
