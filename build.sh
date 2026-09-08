#!/bin/bash
# Script de construcción para Render.com
# Prepara la aplicación para producción en la nube

set -o errexit

echo "=== INICIANDO BUILD PARA RENDER ==="
echo "[1] Instalando dependencias..."
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "[2] Preparando base de datos..."
cd backend
# Crear tablas si no existen
python -c "
from app import create_app
from models import db
import os

# Usar configuración de producción
os.environ['FLASK_ENV'] = 'production'
app, _ = create_app('production')
with app.app_context():
    print('▸ Inicializando base de datos...')
    db.create_all()
    print('✓ Tablas creadas/verificadas')
" 2>&1 || echo "⚠ Advertencia: No se pudo verificar BD, se creará en runtime"

echo "[3] Limpiando caché..."
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true

echo "=== BUILD COMPLETADO ==="
echo "Listo para deployarse en Render.com"
