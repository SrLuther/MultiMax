@echo off
setlocal
echo.
echo =================================================
echo        MULTIMAX - SERVIDOR DE ESTOQUE
echo =================================================
echo.
where py >nul 2>&1 && set "PYLAUNCHER=py"
if defined PYLAUNCHER (
  %PYLAUNCHER% -3 -V >nul 2>&1 && set "PYCMD=%PYLAUNCHER% -3"
) else (
  where python >nul 2>&1 && set "PYCMD=python"
)
if not defined PYCMD (
  echo Python nao encontrado. Instale Python 3 e execute novamente.
  pause
  exit /b 1
)
if not exist venv (
  echo Preparando ambiente...
  %PYCMD% -m venv venv
)
call venv\Scripts\python -m pip install --upgrade pip
if exist requirements.txt (
  call venv\Scripts\python -m pip install -r requirements.txt
)
echo.
echo Aguarde... encontrando seu IP na rede...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /C:"IPv4"') do set IP=%%i
set IP=%IP: =%
set HOST=0.0.0.0
set PORT=5000
set DEBUG=false
echo.
echo SUCESSO! SERVIDOR INICIADO
echo.
echo OUTRAS MAQUINAS DEVEM ACESSAR:
echo       http://%IP%:%PORT%
echo.
echo (Ctrl + C para parar)
echo.
call venv\Scripts\python app.py
pause
