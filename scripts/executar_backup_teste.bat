
@echo off
setlocal

cd /d "%~dp0.."

if not defined BIBLIOTECA_DRIVE_FOLDER_ID (
    echo ERRO: A variavel BIBLIOTECA_DRIVE_FOLDER_ID nao esta configurada.
    echo Configure a variavel de ambiente no Windows e abra um novo terminal.
    pause
    exit /b 1
)

set "PASTA_LOG=%LOCALAPPDATA%\BibliotecaCristopolis\data\logs"

if not exist "%PASTA_LOG%" mkdir "%PASTA_LOG%"

set "EXECUTAVEL=%CD%\dist\BackupBiblioteca\BackupBiblioteca.exe"

if not exist "%EXECUTAVEL%" (
    echo ERRO: Executavel nao encontrado:
    echo %EXECUTAVEL%
    pause
    exit /b 1
)

echo ======================================== >> "%PASTA_LOG%\backup_teste.log"
echo Inicio: %date% %time% >> "%PASTA_LOG%\backup_teste.log"

"%EXECUTAVEL%" >> "%PASTA_LOG%\backup_teste.log" 2>&1
set "RESULTADO=%ERRORLEVEL%"

if not "%RESULTADO%"=="0" (
    echo Resultado: FALHA - Codigo %RESULTADO% >> "%PASTA_LOG%\backup_teste.log"
) else (
    echo Resultado: CONCLUIDO >> "%PASTA_LOG%\backup_teste.log"
)

echo Fim: %date% %time% >> "%PASTA_LOG%\backup_teste.log"

echo.
echo Execucao finalizada. Consulte o arquivo de log.
pause

exit /b %RESULTADO%
