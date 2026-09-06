"""
═══════════════════════════════════════════════════════════════════════════════
  GUÍA RÁPIDA — PRÓXIMOS PASOS (NEXT STEPS)
═══════════════════════════════════════════════════════════════════════════════

Este archivo te da acceso rápido a los comandos que necesitas ejecutar ahora.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 1: VERIFICAR QUE EL SERVIDOR ESTÁ CORRIENDO
# ═══════════════════════════════════════════════════════════════════════════════

PASO_1_VERIFICAR_SERVIDOR = """
📍 PASO 1: Verificar que el servidor Flask está corriendo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Abre una terminal PowerShell
2. Navega al proyecto:
   
   cd 'c:\Users\AMAT\Desktop\ingreso de aprendices\prubas\ingresos aprendices\backup version vs code\ingresos aprendices 6 backup final\ingresos aprendices 6 backup final'

3. Inicia el servidor:
   
   .venv\Scripts\python.exe backend\app.py

   Deberías ver:
   ✅ WARNING in app.runningonPy... (esto es normal)
   ✅ * Running on http://127.0.0.1:8000
   ✅ Press CTRL+C to quit

4. Si lo ves, el servidor está bien (déjalo corriendo en ese terminal)

5. En otro terminal, verifica que funciona:
   
   invoke-WebRequest http://localhost:8000/health

   Deberías ver: StatusCode 200
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 2: INSTALAR NUEVAS DEPENDENCIAS DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

PASO_2_INSTALAR_DEPENDENCIAS = """
📍 PASO 2: Instalar nuevas dependencias de seguridad
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Con el servidor DETENDIO (CTRL+C), en el terminal principal:

1. Activar el virtual environment:
   
   .venv\Scripts\Activate.ps1

   Deberías ver: (.venv) al inicio de la línea

2. Instalar los paquetes de seguridad:
   
   pip install bleach cryptography

   Espera a que termine. Deberías ver:
   ✅ Successfully installed bleach ... cryptography ...

3. Verificar que fue exitoso:
   
   python -c "import bleach; import cryptography; print('✅ Listo')"

✅ Si ves "✅ Listo", continúa con el próximo paso
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 3: EJECUTAR PRUEBAS DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

PASO_3_PRUEBAS_SEGURIDAD = """
📍 PASO 3: Ejecutar pruebas de seguridad
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Con el virtual environment aún activado:

1. Navega a la carpeta backend:
   
   cd backend

2. Ejecuta las pruebas de seguridad:
   
   python security_tests.py

   Esto ejecutará 30+ pruebas de seguridad y deberías ver:

   ✅ Pruebas de SQL Injection: PASADAS
   ✅ Pruebas de XSS: PASADAS
   ✅ Pruebas de Rate Limiting: PASADAS
   ✅ Pruebas de CSRF: PASADAS
   ✅ ... más pruebas ...

   Si TODAS dicen "TOTALIZÓ: 34/34 PASADAS" → ✅ TODO BIEN

3. Si alguna falla:
   - Revisa el error
   - Puede que necesites instalar otra dependencia
   - Abre un issue o consulta

✅ Cuando todas las pruebas pasen, continúa
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 4: REINICIAR SERVIDOR Y PROBAR API
# ═══════════════════════════════════════════════════════════════════════════════

PASO_4_PROBAR_API = """
📍 PASO 4: Reiniciar servidor y probar que API funciona
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Vuelve a la carpeta raíz del proyecto:
   
   cd ..

2. Reinicia el servidor Flask (esto carga las nuevas dependencias):
   
   .venv\Scripts\python.exe backend\app.py

3. En otra terminal (con venv activado), verifica que el endpoint crítico funciona:
   
   # Abre electroso como admin (normalmente se hace desde la web, pero probamos directamente)
   $headers = @{
       "Authorization" = "Bearer YOUR_JWT_TOKEN_HERE"
   }
   
   Invoke-WebRequest -Uri "http://localhost:8000/api/acceso/verificar?numero_doc=12345678&tipo=ENTRADA" -Headers $headers

   Deberías ver:
   ✅ StatusCode 200 o 400 (pero sin crash)
   ✅ En el stderr del servidor: "ACCESO_DENEGADO_VALIDACION" o éxito

4. Prueba con datos maliciosos para verificar que se rechaza:
   
   # Esta prueba de inyección SQL debe ser rechazada
   Invoke-WebRequest "http://localhost:8000/api/acceso/verificar?numero_doc=1' OR '1'='1&tipo=ENTRADA"

   Resultardo esperado:
   ✅ 400 Bad Request (no 500 crash)
   ✅ Error message en JSON seguro (sin detalles internos)

✅ Si los tests pasan sin crash, la seguridad está funcionand
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 5: CONFIGURAR .env PARA PRODUCCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

PASO_5_CONFIGURAR_ENV = """
📍 PASO 5: Configurar archivo .env
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este paso es IMPORTANTE para asegurar el sistema en producción.

1. Abre VS Code y crea un archivo nuevo en la raíz del proyecto: .env

2. Copia este contenido (MODIFICA LOS VALORES CON LOS TUYOS):

═══════════════════════════════════════════════════════════════════════════════
# SEGURIDAD - Cambiar en producción
FLASK_ENV=production
DEBUG=False

# Secretos (GENERAR CON: openssl rand -hex 32)
# En PowerShell: [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random -AsString)))
SECRET_KEY=TU_CLAVE_SUPER_SECRETA_AQUI_32_CARACTERES_MINIMO
JWT_SECRET_KEY=OTRA_CLAVE_SUPER_SECRETA_AQUI_32_CARACTERES_MINIMO

# CORS - Cambiar los orígenes permitidos
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Base de datos
DATABASE_URL=sqlite:///instance/sena.db

# DEBUG (solo en desarrollo)
SQLALCHEMY_ECHO=False

# Rate limiting
RATE_LIMIT_ENABLED=True

# Logs
LOG_LEVEL=INFO
═════════════════════════════════════════════════════════════════════════════════

3. Para GENERAR las claves secretas, en PowerShell corre:
   
   # Generar SECRET_KEY
   $Env:SECRET_KEY = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
   
   # Luego cópiala a .env
   Write-Host $Env:SECRET_KEY

4. GUARDA el archivo .env

5. IMPORTANTE: Asegúrate que .env está en .gitignore (no sincronizarlo):
   
   echo ".env" >> .gitignore

✅ Listo, secretos configurados de forma segura
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 6: INTEGRAR SEGURIDAD EN MÁS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

PASO_6_HARDENING_ENDPOINTS = """
📍 PASO 6: Extender la seguridad a otros endpoints (FUTURO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El endpoint /acceso/verificar está protegido. Los próximos son:

Prioridad 1 (CRÍTICA):
  ✓ POST /api/auth/login
  ✓ GET /api/personas/<id>
  ✓ GET /api/equipos/<id>

Prioridad 2 (ALTA):
  ✓ POST /api/pagos
  ✓ PUT /api/personas/<id>
  ✓ DELETE /api/equipos/<id>

Para cada endpoint:
  1. Agregar @rate_limit(max_requests=XX, ventana_segundos=60)
  2. Validar entrada con InputValidator
  3. Sanitizar salida antes de retornar
  4. Log de eventos críticos con log_evento_seguridad()

Patrón (copia esto para otros endpoints):

@api_bp.route('/api/personas/<int:id>', methods=['GET'])
@token_required
@rate_limit(max_requests=30, ventana_segundos=60)
def obtener_persona(id):
    # Validar entrada
    ok, msg = InputValidator.validar_tipo_acceso(str(id))
    if not ok:
        log_evento_seguridad('ACCESO_NO_AUTORIZADO', ...)
        return jsonify({'error': msg}), 400
    
    persona = Persona.query.get_or_404(id)
    
    # Sanitizar salida
    return jsonify({
        'id': persona.id,
        'nombre': InputValidator.sanitizar_string(persona.nombre),
        'programa': InputValidator.sanitizar_string(persona.programa),
    }), 200
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  RESUMEN RÁPIDO DE ARCHIVOS NUEVOS
# ═══════════════════════════════════════════════════════════════════════════════

ARCHIVOS_NUEVOS = """
ARCHIVOS CREADOS EN ESTA SESIÓN:
═════════════════════════════════════════════════════════════════════════════════

1. backend/security_shield.py (865 líneas)
   Lo que hace: Módulo central de seguridad
   Contiene: 
     - InputValidator (7 métodos para validar datos)
     - RateLimiter (protección contra DoS)
     - CSRFProtection (protección contra CSRF)
     - Headers de seguridad OWASP
     - Logging de eventos de seguridad

2. backend/security_tests.py (320 líneas)
   Lo que hace: Suite de pruebas de seguridad
   Ejecutar con: python backend/security_tests.py
   Prueba: 30+ escenarios de ataque (SQL injection, XSS, etc)

3. SEGURIDAD.md (documento de referencia)
   Lo que hace: Documentación completa de todas las protecciones
   Leer: Para entender qué está protegido y cómo

4. STATUS.md (estado del proyecto)
   Lo que hace: Resumen de cambios y objetivos
   Leer: Para ver antes/después y progreso

ARCHIVOS MODIFICADOS:
═════════════════════════════════════════════════════════════════════════════════

1. backend/app.py
   Cambio: Integración de headers de seguridad
   Efecto: Todas las respuestas HTTP incluyen X-Frame-Options, CSP, etc

2. backend/routes.py
   Cambio: Hardening del endpoint /acceso/verificar
   Efecto: Ya no es vulnerable a SQL injection, DoS, etc

3. frontend/ingreso.html
   Cambio: Modal privacidad oculta por defecto
   Efecto: UI más limpia, se muestra solo clic

4. requirements.txt
   Cambio: Actualizado para Python 3.13
   Efecto: Todas las dependencias compatibles
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  CHECKLIST PARA ESTA SESIÓN
# ═══════════════════════════════════════════════════════════════════════════════

CHECKLIST = """
CHECKLIST DE COMPLETACIÓN:
═════════════════════════════════════════════════════════════════════════════════

Phase 1 - EMERGENCIA (COMPLETADA ✅):
   ✅ Servidor no iniciaba → REPARADO
   ✅ Dependencias incompatibles → ACTUALIZADAS
   ✅ pydotenv error → CORREGIDO

Phase 2 - MEJORAS UI (COMPLETADA ✅):
   ✅ Modal privacidad → OCULTADA POR DEFECTO
   ✅ Status indicator → ANIMADO Y CENTTRADO
   ✅ Política privacidad → MEJORADA

Phase 3 - SEGURIDAD FRAMEWORK (COMPLETADA ✅):
   ✅ security_shield.py → CREADO (865 líneas)
   ✅ security_tests.py → CREADO (320 líneas)
   ✅ Integración app.py → HECHA
   ✅ Hardening /acceso/verificar → HECHO
   
Phase 4 - VALIDACIÓN (EN PROGRESO 🔄):
   ⏳ Instalar bleach + cryptography
   ⏳ Ejecutar security_tests.py
   ⏳ Verificar endpoint /acceso/verificar
   ⏳ Configurar .env para producción
   ⏳ Extender seguridad a otros endpoints
   ⏳ Documentación final

Para ver el progreso en cualquier momento, lee STATUS.md
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  COMANDOS RÁPIDOS (COPY-PASTE)
# ═══════════════════════════════════════════════════════════════════════════════

COMANDOS_RAPIDOS = """
COMANDOS ÚTILES (COPY-PASTE EN POWERSHELL):
═════════════════════════════════════════════════════════════════════════════════

# 1. Navegar al proyecto
cd 'c:\Users\AMAT\Desktop\ingreso de aprendices\prubas\ingresos aprendices\backup version vs code\ingresos aprendices 6 backup final\ingresos aprendices 6 backup final'

# 2. Activar venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias de seguridad
pip install bleach cryptography

# 4. Correr pruebas de seguridad
cd backend
python security_tests.py

# 5. Ir hacia atrás
cd ..

# 6. Verificar versiones (debug)
python --version
pip list | findstr -i "flask sqlalchemy"

# 7. Ejecutar servidor
.venv\Scripts\python.exe backend\app.py

# 8. En otra terminal, probar servidor
Invoke-WebRequest http://localhost:8000/health

# 9. Completar el ciclo de pruebas
python backend/security_tests.py -v

# 10. Generar reporte de seguridad
bandit -r . -f csv -o security_report.csv

# 11. Buscar dependencias vulnerables
pip install safety
safety check
"""

if __name__ == "__main__":
    print(__doc__)
    print("\n" + "="*80 + "\n")
    print(PASO_1_VERIFICAR_SERVIDOR)
    print("\n" + "="*80 + "\n")
    print(PASO_2_INSTALAR_DEPENDENCIAS)
    print("\n" + "="*80 + "\n")
    print(PASO_3_PRUEBAS_SEGURIDAD)
    print("\n" + "="*80 + "\n")
    print(PASO_4_PROBAR_API)
    print("\n" + "="*80 + "\n")
    print(PASO_5_CONFIGURAR_ENV)
    print("\n" + "="*80 + "\n")
    print(PASO_6_HARDENING_ENDPOINTS)
    print("\n" + "="*80 + "\n")
    print(ARCHIVOS_NUEVOS)
    print("\n" + "="*80 + "\n")
    print(CHECKLIST)
    print("\n" + "="*80 + "\n")
    print(COMANDOS_RAPIDOS)
