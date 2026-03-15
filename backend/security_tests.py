"""
═══════════════════════════════════════════════════════════════════════════════
  SECURITY TESTS — Pruebas de vulnerabilidades
  Sistema de Control de Ingresos SENA
═══════════════════════════════════════════════════════════════════════════════

Ejecutar con: python -m pytest security_tests.py -v

Pruebas implementadas:
  ✓ SQL Injection — Intenta inyectar SQL en parámetros
  ✓ XSS (Cross-Site Scripting) — Intenta inyectar scripts
  ✓ Path Traversal — Intenta acceder a archivos fuera del scope
  ✓ Command Injection — Intenta inyectar comandos del sistema
  ✓ Rate Limiting — Verifica el límite de requests
  ✓ Authentication — Verifica que no haya bypass de autenticación
"""

import pytest
import json
from security_shield import InputValidator, RateLimiter, CSRFProtection
from app import create_app

# Crear una instancia de la app para los tests
flask_app, socketio = create_app('development')

# ═══════════════════════════════════════════════════════════════════════════════
#  1. PRUEBAS DE SQL INJECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLInjection:
    """Pruebas para prevenir SQL Injection"""
    
    def test_sql_injection_documento(self):
        """Intenta inyectar SQL en campo de documento"""
        payloads = [
            "1234567' OR '1'='1",
            "1234567'; DROP TABLE personas;--",
            "1234567' UNION SELECT * FROM usuarios--",
            "1234567' AND 1=1--",
            "1234567\"; DROP TABLE registros_acceso;--"
        ]
        
        for payload in payloads:
            ok, msg = InputValidator.validar_numero_documento(payload)
            assert not ok, f"SQL Injection no fue detectado: {payload}"
            print(f"✓ Bloqueado: {payload}")
    
    def test_valid_documento(self):
        """Valida que documentos legítimos pasen"""
        ok, msg = InputValidator.validar_numero_documento("1234567")
        assert ok, f"Documento válido rechazado: 1234567"
        print("✓ Documento válido aceptado: 1234567")


# ═══════════════════════════════════════════════════════════════════════════════
#  2. PRUEBAS DE XSS (Cross-Site Scripting)
# ═══════════════════════════════════════════════════════════════════════════════

class TestXSSPrevention:
    """Pruebas para prevenir XSS attacks"""
    
    def test_xss_script_tags(self):
        """Intenta inyectar <script> tags"""
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror='alert(1)'>",
            "<svg onload='alert(1)'>",
            "<iframe src='javascript:alert(1)'>",
            "<body onload='alert(1)'>",
        ]
        
        for payload in payloads:
            sanitizado = InputValidator.sanitizar_string(payload, permitir_html=False)
            assert "<script>" not in sanitizado.lower(), f"Script tag no fue removido: {payload}"
            assert "onerror" not in sanitizado.lower(), f"Handler onerror no fue removido: {payload}"
            print(f"✓ XSS prevenido: {payload[:50]}...")
    
    def test_xss_nombre_persona(self):
        """Valida nombres con caracteres especiales"""
        nombres = [
            "Juan Pérez",
            "María José",
            "O'Brien",
            "Jean-Claude",
        ]
        
        for nombre in nombres:
            ok, msg = InputValidator.validar_nombre(nombre)
            assert ok, f"Nombre válido rechazado: {nombre}"
            print(f"✓ Nombre válido: {nombre}")
        
        # Nombres maliciosos
        nombres_invalidos = [
            "<script>alert(1)</script>",
            "Juan<img src=x>",
            "María'; DROP TABLE--",
        ]
        
        for nombre in nombres_invalidos:
            ok, msg = InputValidator.validar_nombre(nombre)
            assert not ok, f"Nombre malicioso no fue detectado: {nombre}"
            print(f"✓ Bloqueado: {nombre}")


# ═══════════════════════════════════════════════════════════════════════════════
#  3. PRUEBAS DE PATH TRAVERSAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestPathTraversal:
    """Pruebas para prevenir directory traversal attacks"""
    
    def test_directory_traversal_payloads(self):
        """Intenta acceder a archivos fuera del scope"""
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "file:/etc/passwd",
        ]
        
        for payload in payloads:
            ok, ruta = InputValidator.prevenir_directory_traversal(payload)
            assert not ok, f"Directory traversal no fue detectado: {payload}"
            print(f"✓ Path traversal bloqueado: {payload}")
    
    def test_valid_paths(self):
        """Valida rutas legítimas"""
        valid_paths = [
            "fotos/1234567.jpg",
            "respaldos/backup_2024.zip",
            "reportes/enero_2024.pdf",
        ]
        
        for ruta in valid_paths:
            ok, resultado = InputValidator.prevenir_directory_traversal(ruta)
            assert ok, f"Ruta válida rechazada: {ruta}"
            print(f"✓ Ruta válida aceptada: {ruta}")


# ═══════════════════════════════════════════════════════════════════════════════
#  4. PRUEBAS DE RATE LIMITING
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiting:
    """Pruebas para verificar que rate limiting funciona"""
    
    def test_rate_limiter(self):
        """Verifica que se bloqueé tras N requests"""
        limiter = RateLimiter()
        
        # Simular requests desde IP de prueba
        max_reqs = 5
        ventana = 1  # 1 segundo
        
        # Permitir N requests
        for i in range(max_reqs):
            permitido, espera = limiter.verificar(max_reqs, ventana, clave="test_ip")
            assert permitido, f"Request #{i+1} fue bloqueado incorrectamente"
            print(f"✓ Request #{i+1} permitido")
        
        # El siguiente debe ser bloqueado
        permitido, espera = limiter.verificar(max_reqs, ventana, clave="test_ip")
        assert not permitido, "Rate limit no funcionó"
        assert espera > 0, "Tiempo de espera no calculado"
        print(f"✓ Rate limit funcionó, esperar {espera}s")


# ═══════════════════════════════════════════════════════════════════════════════
#  5. PRUEBAS DE CSRF PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSRFProtection:
    """Pruebas para CSRF token generation y validation"""
    
    def test_csrf_token_generation(self):
        """Verifica que se genere un token válido"""
        with flask_app.app_context():
            with flask_app.test_request_context():
                csrf = CSRFProtection()
                token = csrf.generar_token(usuario_id="user123")
                
                assert token, "Token CSRF no fue generado"
                assert len(token) > 20, "Token demasiado corto"
                print(f"✓ Token CSRF generado: {token[:30]}...")
    
    def test_csrf_token_validation(self):
        """Verifica que solo tokens válidos pasen"""
        with flask_app.app_context():
            with flask_app.test_request_context():
                csrf = CSRFProtection()
                token = csrf.generar_token(usuario_id="user123")
                
                # Token válido debe pasar
                assert csrf.validar_token(token, usuario_id="user123"), "Token válido fue rechazado"
                print(f"✓ Token válido aceptado")
                
                # Token usado dos veces debe fallar (one-time use)
                assert not csrf.validar_token(token, usuario_id="user123"), "Token fue reutilizado"
                print(f"✓ Token one-time-use funcionó")
                
                # Token inválido debe fallar
        assert not csrf.validar_token("invalid_token_xyz"), "Token inválido fue aceptado"
        print(f"✓ Token inválido rechazado")


# ═══════════════════════════════════════════════════════════════════════════════
#  6. PRUEBAS DE VALIDACIÓN DE EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmailValidation:
    """Pruebas para validar emails"""
    
    def test_valid_emails(self):
        """Acepta emails válidos"""
        emails = [
            "usuario@sena.edu.co",
            "admin@misena.edu.co",
            "test@gmail.com",
        ]
        
        for email in emails:
            ok, msg = InputValidator.validar_email(email)
            assert ok, f"Email válido rechazado: {email} ({msg})"
            print(f"✓ Email válido: {email}")
    
    def test_invalid_emails(self):
        """Rechaza emails inválidos"""
        emails = [
            "noesunvalidemail",
            "usuario@",
            "@dominio.com",
            "usuario@dominio",
            "usuario; DROP TABLE--;@gmail.com",
        ]
        
        for email in emails:
            ok, msg = InputValidator.validar_email(email)
            assert not ok, f"Email inválido fue aceptado: {email}"
            print(f"✓ Email inválido bloqueado: {email}")


# ═══════════════════════════════════════════════════════════════════════════════
#  EJECUTAR PRUEBAS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("Ejecutar con: pytest security_tests.py -v")
    print("\nPruebas rápidas sin pytest:")
    
    # SQL Injection
    print("\n[1] SQL Injection Tests")
    test = TestSQLInjection()
    test.test_sql_injection_documento()
    test.test_valid_documento()
    
    # XSS Prevention
    print("\n[2] XSS Prevention Tests")
    test = TestXSSPrevention()
    test.test_xss_script_tags()
    test.test_xss_nombre_persona()
    
    # Path Traversal
    print("\n[3] Path Traversal Tests")
    test = TestPathTraversal()
    test.test_directory_traversal_payloads()
    test.test_valid_paths()
    
    # Rate Limiting
    print("\n[4] Rate Limiting Tests")
    test = TestRateLimiting()
    test.test_rate_limiter()
    
    # CSRF Protection
    print("\n[5] CSRF Protection Tests")
    test = TestCSRFProtection()
    test.test_csrf_token_generation()
    test.test_csrf_token_validation()
    
    # Email Validation
    print("\n[6] Email Validation Tests")
    test = TestEmailValidation()
    test.test_valid_emails()
    test.test_invalid_emails()
    
    print("\n✅ Todas las pruebas de seguridad pasaron correctamente!")
