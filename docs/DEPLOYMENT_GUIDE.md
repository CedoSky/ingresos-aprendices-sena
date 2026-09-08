# 🚀 GUÍA DE DEPLOYMENT EN RENDER.COM

## 📋 Requisitos previos

- Cuenta en GitHub (para conectar este repositorio)
- Cuenta en Render.com (gratis: https://render.com)
- Git instalado en tu máquina

---

## 🔧 PASO 1: Preparar el repositorio

### 1.1 Inicializar Git (si no está hecho)
```bash
cd "C:\Users\AMAT\Desktop\ingreso de aprendices\prubas\ingresos aprendices\backup version vs code\ingresos aprendices 6 backup final\ingresos aprendices 6 backup final"
git init
git add .
git commit -m "Inicial: Sistema SENA de ingresos y salidas"
```

### 1.2 Crear repositorio en GitHub
- Ve a https://github.com/new
- Nombre: `sena-ingresos-nube`
- Descripción: "Sistema de gestión de ingresos y salidas - SENA"
- **NO inicialices con README** (ya existe)

### 1.3 Enlazar con GitHub
```bash
git remote add origin https://github.com/TU_USUARIO/sena-ingresos-nube.git
git branch -M main
git push -u origin main
```

---

## 🌐 PASO 2: Crear cuenta en Render

1. Ve a https://render.com y regístrate
2. Confirma tu email
3. Conecta tu cuenta de GitHub:
   - Dashboard → Account Settings
   - GitHub → Connect

---

## 📱 PASO 3: Crear el servicio en Render

### 3.1 Crear web service
1. Click en **"+ New"** → **"Web Service"**
2. Selecciona tu repositorio `sena-ingresos-nube`
3. Configura:
   - **Name**: `sena-ingresos-api`
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
   - **Plan**: Free (gratis con limitaciones)

### 3.2 Configurar variables de entorno
En el apartado **Environment**:
```
FLASK_ENV = production
SECRET_KEY = (generado automáticamente por Render)
JWT_SECRET_KEY = (generado automáticamente por Render)
```

### 3.3 Crear PostgreSQL
1. Click en **"+ New"** → **"PostgreSQL"**
2. Configura:
   - **Name**: `sena-db`
   - **PostgreSQL Version**: 15
   - **Plan**: Free

3. Espera a que se cree (2-5 minutos)
4. Copia la **Internal Database URL** del PostgreSQL

### 3.4 Conectar la BD al API
Vuelve al Web Service y agrega:
```
DATABASE_URL = postgresql://...  (la que copiaste)
```

---

## ⚙️ PASO 4: Configuraciones adicionales

### Variables recomendadas para pruebas:
```
CORS_ORIGINS = https://sena-ingresos-api.onrender.com,http://localhost:3000
STORAGE_BACKEND = s3
USE_USB = false
```

### Habilitar HTTPS (automático en Render)
- Render genera automáticamente certificados SSL
- Tu URL será: `https://sena-ingresos-api.onrender.com`

---

## 🧪 PASO 5: Probar en Render

### 5.1 Ver logs
En el dashboard de Render:
- Click en tu servicio
- Tab **"Logs"** para ver errores en tiempo real

### 5.2 Verificar salud
```bash
curl https://sena-ingresos-api.onrender.com/api/health
```

**Respuesta esperada:**
```json
{
  "status": "OK",
  "version": "1.0",
  "database": "postgresql",
  "timestamp": "2026-03-15T12:34:56Z"
}
```

### 5.3 Probar login
```bash
curl -X POST https://sena-ingresos-api.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sena.edu.co","password":"tu_contraseña"}'
```

---

## 🔗 PASO 6: Actualizar frontend para producción

### En las páginas HTML (frontend/):
Cambiar URLs de localhost a Render:

**Antes:**
```javascript
const API_URL = "http://localhost:8000";
```

**Después:**
```javascript
const API_URL = "https://sena-ingresos-api.onrender.com";
```

### Actualizar en archivos:
- `frontend/ingreso.html`
- `frontend/vigilancia.html`
- `frontend/login.html`
- `js/APIClientBackend.js` (si existe)

---

## 📊 PASO 7: Monitoreo en producción

### Render Dashboard
- **Metrics**: CPU, RAM, conexiones
- **Web Services**: Estado (deployed/failed)
- **Logs**: Errores en tiempo real

### Configurar alertas
En Render Settings:
- Email para notificaciones de deployment
- Alertas de errores

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Error: "Build failed"
→ Ver en **Logs** qué falta
→ Usualmente `psycopg2` no instalado

### Error: "Failed to connect to database"
→ Verificar que `DATABASE_URL` esté configurado
→ Esperar 5 minutos (la BD tarda en inicializar)

### Error 500 al hacer login
→ Las tablas no se crearon
→ Solución: Ejecutar en la consola de Render:
```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Error CORS
→ Agregar tu dominio a `CORS_ORIGINS`
→ Reiniciar el servicio

---

## 📈 PASO 8: Escalar (cuando funcione)

### Upgrades sugeridos:
1. **Plan de pago** (Render): $7-12/mes
   - Más CPU/RAM
   - Mejor performance

2. **Certificado SSL Premium** (opcional $10/mes)

3. **Backup automático de BD**:
   - Render PostgreSQL mantiene respaldos automáticos

4. **CDN + Static files**:
   - Servir frontend desde CDN (CloudFlare gratis)

---

## 🎯 CHECKLIST ANTES DE IR A PRODUCCIÓN

- [ ] Base de datos PostgreSQL creada
- [ ] Variables de entorno configuradas
- [ ] `/api/health` responde OK
- [ ] Login funciona
- [ ] Registros se guardan en BD
- [ ] Exportación a Excel funciona
- [ ] WebSockets funcionan (monitor en tiempo real)
- [ ] HTTPS activo (certificado gen)
- [ ] Emails de notificación funcionan (opcional)
- [ ] Respaldos a S3 configurados (opcional)

---

## 📞 Soporte Render

- Documentación: https://render.com/docs
- Discord: https://discord.gg/render
- Email: support@render.com

---

## 🎉 ¡LISTO!

Tu aplicación está en la nube y accesible desde cualquier lugar:
**https://sena-ingresos-api.onrender.com**

Ahora puedes:
✅ Probar desde cualquier dispositivo
✅ Integrar sistemas externos
✅ Escalar cuando necesites
✅ Hacer respaldos automáticos en la nube
