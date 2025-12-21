@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "_envfile=.env.txt"
if exist "%_envfile%" (
  for /f "usebackq eol=# tokens=1* delims==" %%A in ("%_envfile%") do (
    if not "%%~A"=="" if not "%%~B"=="" set "%%~A=%%~B"
  )
)

set "_activate=.venv\Scripts\activate.bat"
if exist "%_activate%" call "%_activate%"

set "_pyvenv=.venv\Scripts\python.exe"
set "PYTHON=%_pyvenv%"
if not exist "%_pyvenv%" set "PYTHON=python"

echo Usando Python: %PYTHON%
if not defined PORT set "PORT=5000"
echo Servidor iniciando em http://localhost:%PORT%

"%PYTHON%" "app.py"
