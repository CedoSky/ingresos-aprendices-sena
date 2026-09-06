# 🚀 DEPLOYMENT RÁPIDO - SENA INGRESOS A LA NUBE

## 📌 Resumen rápido

Tu aplicación está lista para deployarse en **Render.com** (gratis). Sigue estos pasos:

---

## 1️⃣ PRE-DEPLOY (LOCAL)

### Instalar TODO lo necesario:
```bash
# En PowerShell (desde la carpeta raíz del proyecto)
python.exe setup_deployment.py
```

Esto hará automaticamente:
- ✅ Crear `.env`
- ✅ Inicializar Git
- ✅ Instalar dependencias
- ✅ Verificar que todo funcione

---

## 2️⃣ PUSH A GITHUB

```bash
# Crear repositorio en GitHub
git remote add origin https://github.com/TU_USUARIO/sena-ingresos-nube.git
git branch -M main
git push -u origin main
```

---

## 3️⃣ DEPLOY EN RENDER (5 MINUTOS)

### 3.1 Crear Web Service
1. Ve a https://render.com/dashboard
2. **"+ New"** → **"Web Service"**
3. Conecta tu repo `sena-ingresos-nube`
4. Configura:
   - **Name**: `sena-ingresos-api`
   - **Build Command**: `./build.sh`
   - **Start Command**: `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
   - **Plan**: Free

### 3.2 Crear Base de Datos
1. **"+ New"** → **"PostgreSQL"**
2. Configura:
   - **Name**: `sena-db`
   - **Plan**: Free

### 3.3 Conectar BD al API
1. Copia `Internal Database URL` del PostgreSQL
2. Ve al Web Service → Environment
3. Agrega:
   ```
   DATABASE_URL = postgresql://...
   ```
4. Haz deploy

---

## ✅ VERIFICAR QUE FUNCIONA

### Probar salud del API:
```bash
curl https://TU_SERVICIO.onrender.com/api/health
```

### Probar login:
```bash
curl -X POST https://TU_SERVICIO.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sena.edu.co","password":"contraseña"}'
```

---

## 🔧 CONFIGURAR FRONTEND

Cambiar en `frontend/ingreso.html`, `vigilancia.html`, etc:

**Antes:**
```javascript
const API_URL = "http://localhost:8000/api";
```

**Después:**
```javascript
const API_URL = "https://tu-servicio.onrender.com/api";
```

---

## 📊 MONITOREO

- **Logs en tiempo real**: Render Dashboard → Logs
- **Salud**: Ver CPU, RAM, requests
- **Errores**: Se muestran inmediatamente

---

## 🆘 PROBLEMAS COMUNES

| Problema | Solución |
|----------|----------|
| **Build failed** | Ver logs → buscar "psycopg2" |
| **Error 500 al login** | Las tablas no se crearon. Ver sección CREAR TABLAS |
| **CORS error** | Agregar dominio a `CORS_ORIGINS` |
| **BD no conecta** | Esperar 5 min, verificar `DATABASE_URL` |

### Crear tablas manualmente:
En **Render Dashboard** → Tu Web Service → **"Shell"**:
```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Tablas creadas')"
```

---

## 📚 DOCUMENTACIÓN COMPLETA

Para más detalles, ver: **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

---

## 🎉 ¡LISTO!

Tu app está en: **https://tu-servicio.onrender.com**

**Próximo paso**: Prueba desde otro dispositivo, laptop o móvil en la misma red

---

## 💡 TIPS

✅ Haz push de cambios regularmente: `git push`
✅ Render redeploya automáticamente cuando hacesalias push
✅ Verifica logs durante el deploy
✅ Mantén `.env` fuera de Git (está en `.gitignore`)
✅ Las variables sensibles van en Render Settings, no en código
