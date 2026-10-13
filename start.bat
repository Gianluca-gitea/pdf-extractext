@echo off
echo =========================================
echo   Iniciando PDF Extractext
echo =========================================

if "%EXTRACT_PORT%"=="" set EXTRACT_PORT=8001
if "%DOCUMENTS_PORT%"=="" set DOCUMENTS_PORT=8002

for %%D in (services\extract services\documents gui) do (
    echo [INFO] Sincronizando dependencias de %%D...
    uv --directory %%D sync --frozen --no-dev
)

echo [INFO] Asegurate de que MongoDB este corriendo en el puerto 27017...

echo [INFO] Iniciando el servicio extract en el puerto %EXTRACT_PORT%...
start "PDF Extract Service" cmd /c "uv --directory services\extract run uvicorn app.main:app --host 127.0.0.1 --port %EXTRACT_PORT%"

echo [INFO] Iniciando el servicio documents en el puerto %DOCUMENTS_PORT%...
start "PDF Documents Service" cmd /c "set EXTRACT_SERVICE_URL=http://127.0.0.1:%EXTRACT_PORT%&& uv --directory services\documents run uvicorn app.main:app --host 127.0.0.1 --port %DOCUMENTS_PORT%"

echo [INFO] Esperando 2 segundos para que los servicios inicien...
timeout /t 2 /nobreak > NUL

echo [INFO] Iniciando el frontend...
set EXTRACT_API_URL=http://127.0.0.1:%EXTRACT_PORT%
set DOCUMENTS_API_URL=http://127.0.0.1:%DOCUMENTS_PORT%
uv --directory gui run python interface.py

echo [INFO] Interfaz cerrada. (Los servicios seguiran corriendo en las otras ventanas).
pause
