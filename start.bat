@echo off
echo =========================================
echo   Iniciando PDF Extractext
echo =========================================

IF NOT EXIST ".venv\" (
    echo [INFO] No se encontro el entorno virtual '.venv'.
    echo [INFO] Creando entorno e instalando dependencias con uv...
    uv venv
    uv sync --frozen --no-dev
    echo [INFO] Instalacion completada.
)

echo [INFO] Asegurate de que MongoDB este corriendo en el puerto 27017...

uv sync --frozen --no-dev

echo [INFO] Iniciando el backend..
start "PDF Backend Server" cmd /c "uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [INFO] Esperando 2 segundos para que el servidor inicie...
timeout /t 2 /nobreak > NUL

echo [INFO] Iniciando el frontend...
uv run python app\interface.py

echo [INFO] Interfaz cerrada. (El backend seguira corriendo en la otra ventana).
pause
