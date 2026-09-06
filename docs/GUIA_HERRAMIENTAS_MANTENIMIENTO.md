# Sistema de Herramientas Restringidas de Mantenimiento

## 📋 Descripción

El sistema tiene un área protegida de **Herramientas de Mantenimiento** que requiere un PIN dinámico generado desde la terminal. Esta medida de seguridad asegura que solo personal autorizado de sistemas pueda realizar operaciones críticas en la base de datos y configuración del sistema.

---

## 🔐 Cómo Funciona

### 1. **Generar el PIN (Terminal)**

El personal de sistemas debe ejecutar:

```batch
MANTENIMIENTO.bat
```

Luego seleccionar opción **P** para "Ver PIN del panel de sistemas".

El sistema mostrará un PIN dinámico:
```
PIN: 123456
Válido por: 5 minutos
```

**⏰ El PIN cambia automáticamente cada 5 minutos**

### 2. **Ingresar el PIN (Panel Admin)**

1. Abre el **Panel de Administración**
2. Ve a la pestaña **"Herramientas"**
3. Verás un modal de bloqueo con un campo de entrada
4. Ingresa el PIN generado en el paso anterior
5. Haz clic en **"Desbloquear"**
6. ✅ Acceso concedido a herramientas de mantenimiento

---

## 🛠️ Herramientas Disponibles (Solo con PIN)

Una vez desbloqueado, tienes acceso a:

### **Limpieza de Datos**
- **Limpiar Registros de Acceso**: Elimina todos los registros de entrada/salida (mantiene las personas)
- **Restaurar Base de Datos**: ⚠️ CUIDADO - Elimina TODO

### **Sistema**
- **Descargar BD**: Descarga una copia de la base de datos
- **Optimizar**: Desfragmenta y optimiza la base de datos
- **Health Check**: Verifica el estado del sistema
- **Estado**: Muestra información del sistema

---

## ⚠️ Advertencias Críticas

### Restaurar Base de Datos
- ❌ NO se puede deshacer
- ❌ Elimina TODAS las personas
- ❌ Elimina TODOS los registros
- ✅ Solo úsalo si sabes exactamente lo que haces

---

## 🔄 Ciclo de Vida del PIN

| Acción | Duración |
|--------|----------|
| PIN generado | - |
| PIN válido | 5 minutos |
| PIN ingresado | Sesión actual |
| Acceso desbloqueado | Sesión actual |

---

## 💡 Recomendaciones

1. Genera PINs justo cuando los necesites
2. Nunca compartas PINs por chat
3. Registra lo que vas a hacer antes de operaciones críticas
4. Haz backup antes de restaurar
5. Revisa la auditoría después de operaciones críticas

---

**Versión**: 1.0 - Sistema PIN Dinámico (TOTP)
