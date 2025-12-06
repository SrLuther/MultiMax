@echo off
setlocal
set "REPO=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO%scripts\install_and_create_shortcuts.ps1"
echo.
echo Instalacao e geracao de atalhos concluida.
echo Pressione qualquer tecla para fechar...
pause >nul
