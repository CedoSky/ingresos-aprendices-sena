# 🐳 INSTALAR DOCKER — Guía Paso a Paso

Docker NO está instalado. Aquí cómo instalarlo:

---

## 📥 Paso 1: Descargar Docker Desktop

### Windows (Lo más común)

1. **Abre este enlace:**
   ```
   https://www.docker.com/products/docker-desktop
   ```

2. **Haz click en "Download for Windows"**
   - Se descargará `Docker Desktop Installer.exe`

3. **Ejecuta el instalador**
   - Doble click en el archivo descargado
   - Espera a que instale (5-10 minutos)

4. **Reinicia Windows cuando te lo pida**

---

## ✅ Paso 2: Verificar Instalación

Después de reiniciar, abre **PowerShell** y ejecuta:

```powershell
docker --version
docker-compose --version
```

Deberías ver:
```
Docker version 26.1.0, build abc123...
Docker Compose version 2.25.0
```

Si ves esto ✅ **¡Docker está listo!**

---

## 🎯 Paso 3: Usa mi Script de Verificación

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
.\verify-docker-installation.bat
```

Este script verifica automáticamente si Docker está instalado correctamente.

---

## 🚀 Paso 4: Inicia tu Sistema

Una vez Docker esté verificado:

```powershell
docker-compose up -d
```

Listo. El sistema estará corriendo en:
- **Frontend:** http://localhost
- **Backend:** http://localhost:8000

---

## ⏱️ Tiempo Total

| Tarea | Tiempo |
|-------|--------|
| Descargar Docker | 5-10 min |
| Instalar | 2-5 min |
| Reiniciar Windows | 1-2 min |
| Setup del proyecto | 10-15 min |
| **TOTAL** | **20-30 min** |

---

## 🆘 Problemas Comunes

### "Docker Desktop no inicia"
- Verifica que Windows esté actualizado
- Reinicia la máquina
- Abre Docker Desktop desde Inicio

### "Port 80 already in use"
En `.env`, cambia:
```
NGINX_PORT=80
# A:
NGINX_PORT=8080
```

### "Disco lleno"
```powershell
docker system prune -a
```

---

## 📞 Cuando Docker esté Instalado

Avísame y ejecuta:
```powershell
docker-compose up -d
```

Si hay error, dime qué dice exactamente.
