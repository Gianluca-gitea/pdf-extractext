#!/bin/bash

echo "========================================="
echo "  Iniciando PDF Extractext"
echo "========================================="

EXTRACT_PORT="${EXTRACT_PORT:-8001}"
DOCUMENTS_PORT="${DOCUMENTS_PORT:-8002}"

for dir in services/extract services/documents gui; do
    echo "[INFO] Sincronizando dependencias de $dir..."
    uv --directory "$dir" sync --frozen --no-dev
done

echo "[INFO] Asegurate de que MongoDB esté corriendo en el puerto 27017..."

echo "[INFO] Iniciando el servicio extract en el puerto $EXTRACT_PORT..."
uv --directory services/extract run uvicorn app.main:app --host 127.0.0.1 --port "$EXTRACT_PORT" &
EXTRACT_PID=$!

echo "[INFO] Iniciando el servicio documents en el puerto $DOCUMENTS_PORT..."
EXTRACT_SERVICE_URL="http://127.0.0.1:$EXTRACT_PORT" \
    uv --directory services/documents run uvicorn app.main:app --host 127.0.0.1 --port "$DOCUMENTS_PORT" &
DOCUMENTS_PID=$!

echo "[INFO] Esperando 2 segundos para que los servicios inicien..."
sleep 2

echo "[INFO] Iniciando el frontend..."
EXTRACT_API_URL="http://127.0.0.1:$EXTRACT_PORT" \
DOCUMENTS_API_URL="http://127.0.0.1:$DOCUMENTS_PORT" \
    uv --directory gui run python interface.py

echo "[INFO] Interfaz cerrada. Deteniendo los servicios..."
kill $EXTRACT_PID $DOCUMENTS_PID
wait $EXTRACT_PID $DOCUMENTS_PID 2>/dev/null
echo "[INFO] Listo."
