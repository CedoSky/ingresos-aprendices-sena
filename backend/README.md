# Backend API - SENA Ingresos Aprendices

## Inicio Rápido

### Requisitos
- Python 3.9+
- PostgreSQL 12+

### 1. Instalar y ejecutar

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### 2. Configurar PostgreSQL

```bash
psql -U postgres
CREATE DATABASE sena_aprendices_dev;
\q
```

Actualizar `.env` con tu configuración de BD:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/sena_aprendices_dev
```

### 3. Usar API

- **Login:** `POST /api/auth/login`
  - Email: `admin@sena.edu.co`
  - Password: `admin123`

- **Crear persona:** `POST /api/personas`
- **Listar personas:** `GET /api/personas`
- **Registrar acceso:** `POST /api/registros-acceso`
- **Ver estadísticas:** `GET /api/estadisticas`

### 4. Con Docker

```bash
docker-compose up -d
```

La API estará en `http://localhost:5000`

## Archivos principales

- `app.py` - Aplicación Flask
- `models.py` - Modelos de base de datos
- `routes.py` - Endpoints API
- `cloud_storage.py` - Integración AWS S3
- `config.py` - Configuración
- `requirements.txt` - Dependencias
- `docker-compose.yml` - Orquestación de contenedores

## Testing

Abre la consola con:
```bash
curl http://localhost:5000/health
```

## Endpoints principales

Ver `routes.py` para detalles completos de cada endpoint.
