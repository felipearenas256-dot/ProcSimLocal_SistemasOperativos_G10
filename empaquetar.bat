@echo off
REM Genera el ejecutable de Windows dist\ProcSimLocal.exe con PyInstaller.
REM Uso: doble clic o "empaquetar.bat" desde la raiz del repositorio.
cd /d "%~dp0"
python -m pip install --user pyinstaller || goto :error
python -m PyInstaller --noconfirm --onefile --windowed --name ProcSimLocal ^
  --paths src --add-data "src\bd\esquema.sql;bd" src\main.py || goto :error
echo.
echo Listo: dist\ProcSimLocal.exe
goto :eof
:error
echo Error al generar el ejecutable.
exit /b 1
