# 🎓 Sistema Control de Ingresos SENA

**Versión:** 6-WithSecurity  
**Estado:** ✅ Operacional y Endurecido  
**Última actualización:** 30/03/2026

---

## 📁 Estructura del Proyecto

```
.
├── 📂 backend/              # API Flask (puerto 8000)
├── 📂 frontend/             # Interfaces HTML/JS
├── 📂 Arduino/              # Código ESP32 TRIAC
├── 📂 docs/                 # 📚 Documentación (19 archivos)
├── 📂 scripts/              # 🔧 Scripts Python y Batch
├── 📂 tests/                # 🧪 Casos de prueba
├── 📂 instance/             # Base de datos SQLite
├── 📂 logs/                 # Registros de aplicación
├── 📂 RESPALDOS_USB/        # Respaldos locales
│
├── requirements.txt         # Dependencias Python
├── pyrightconfig.json       # Configuración Pyright
├── .env.example             # Template de variables
├── .env.esp32               # Config ESP32
├── render.yaml              # Deploy (Render)
├── Procfile                 # Procfile (Heroku/Render)
├── runtime.txt              # Versión Python
└── build.sh                 # Build script Linux
```

---

## 🚀 Inicio Rápido

### 1. Instalar Docker Desktop
- Descarga: https://www.docker.com/products/docker-desktop
- Instala y reinicia

### 2. Ejecutar sistema
En PowerShell (como administrador):
```bash
DOCKER_SETUP.bat
```

**Listo.** Tu sistema está en:
- Frontend: http://localhost
- Backend: http://localhost:8000

### Credenciales de prueba
- Email: admin@sena.edu.co
- Contraseña: admin123
```bash
python backend/app.py
# O usar: python scripts/restart_flask.py
```

Servidor disponible en: **http://localhost:8000**

---

## 📚 Documentación
Ver carpeta `docs/` para:
- **SEGURIDAD.md** — Guía de seguridad completa
- **DEPLOYMENT_GUIDE.md** — Despliegue a producción
- **REPORTE_FINAL_SEGURIDAD.md** — Reporte de implementación
- **GUIA_INTEGRACION_TRIAC.md** — Integración ESP32

---

## 🔧 Scripts Disponibles

Ubicados en `scripts/`:
- `INICIAR.bat` — Start rápido (Windows)
- `MANTENIMIENTO.bat` — Panel mantenimiento con PIN
- `VERIFICAR_INSTALACION.bat` — Validar setup
- `restart_flask.py` — Reiniciar servidor Python

---

## 🧪 Testing

Ejecutar pruebas desde `tests/`:
```bash
python tests/test_api_simple.py
python tests/test_sesion.py
```

---

## 🏗️ Tecnologías

| Layer | Tech |
|-------|------|
| Backend | Flask 3.1.3, SQLAlchemy 2.0.48 |
| Frontend | HTML5, JavaScript, Bootstrap |
| Database | SQLite (dev), PostgreSQL (prod) |
| Security | JWT, Fernet Encryption, CSRF |
| IoT | ESP32 TRIAC Control |

---

## ✅ Estado de Seguridad
- ✅ JWT autenticación con expiración
- ✅ Encriptación datos sensibles (Fernet)
- ✅ Protección XSS/SQL Injection
- ✅ Rate limiting por IP
- ✅ Auditoría completa de cambios
- ✅ **11/11 pruebas seguridad pasadas (100%)**

---

## 📞 Soporte
Para issues o cambios, revisar:
- `docs/CAMBIOS_IMPLEMENTADOS.md` — Histórico de cambios
- `docs/STATUS.md` — Estado actual del sistema

---

**Última limpieza:** 30/03/2026 — Se reorganizó la raíz del proyecto moviendo documentación a `docs/`, scripts a `scripts/` y tests a `tests/`.
