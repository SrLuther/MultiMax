@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo   MultiMax - Iniciando Release e Push Automatico
echo ====================================================
echo.

powershell -ExecutionPolicy Bypass -File ".\git-push-with-version.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu uma falha durante o processo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUCESSO] Procedimento concluido!
timeout /t 5
