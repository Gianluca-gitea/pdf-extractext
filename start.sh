#!/bin/bash

echo "========================================="
echo "  Iniciando PDF Extractext"
echo "========================================="

if [ ! -d ".venv" ]; then
    echo "[INFO] No se encontró el entorno virtual '.venv'."
    echo "[INFO] Creando entorno e instalando dependencias con uv (vuela)..."
    uv venv
    uv sync --frozen --no-dev
    echo "[INFO] Instalación completada."
fi

echo "[INFO] Asegurate de que MongoDB esté corriendo en el puerto 27017..."

uv sync --frozen --no-dev

echo "[INFO] Iniciando el backend..."
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "[INFO] Esperando 2 segundos para que el servidor inicie..."
sleep 2

echo "[INFO] Iniciando el frontend..."
python app/interface.py

echo "[INFO] Interfaz cerrada. Deteniendo el backend..."
kill $BACKEND_PID
wait $BACKEND_PID 2>/dev/null
echo "[INFO] Listo."
