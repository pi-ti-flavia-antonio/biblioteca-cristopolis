
@echo off
cd /d "%~dp0"

if not exist "data\logs" mkdir "data\logs"

echo ======================================== >> "data\logs\backup.log"
echo Inicio: %date% %time% >> "data\logs\backup.log"

"venv\Scripts\python.exe" "drive_backup.py" >> "data\logs\backup.log" 2>&1

if errorlevel 1 (
    echo Resultado: FALHA >> "data\logs\backup.log"
) else (
    echo Resultado: CONCLUIDO >> "data\logs\backup.log"
)

echo Fim: %date% %time% >> "data\logs\backup.log"
