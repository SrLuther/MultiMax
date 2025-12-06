@echo off
setlocal
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
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install pyinstaller
pyinstaller --name MultiMax --onefile --add-data "templates;templates" app.py
echo.
echo Binario criado em dist\MultiMax.exe
pause
