@echo off
echo.
echo =================================================
echo        MULTIMAX - SERVIDOR DE ESTOQUE
echo =================================================
echo.
echo Aguarde... encontrando seu IP na rede...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /C:"IPv4"') do set IP=%%i
set IP=%IP: =%
echo.
echo SUCESSO! SERVIDOR INICIADO
echo.
echo OUTRAS MAQUINAS DEVEM ACESSAR:
echo       http://%IP%:5000
echo.
echo (Ctrl + C para parar)
echo.
python app.py
pause