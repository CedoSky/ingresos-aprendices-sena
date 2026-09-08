"""
Stub para lock_scheduler - Sistema de Control de Cerraduras Automáticas.

Este módulo proporciona stubs para el sistema de cerraduras que aún está en desarrollo.
Previene que el servidor falle cuando el código intenta acceder a lock_scheduler.

Estado: IN DEVELOPMENT
TODO: Implementar integración real con ESP32
"""

import logging

logger = logging.getLogger(__name__)


class LockSchedulerStub:
    """Mock del gestor de cerraduras - versión stub."""
    
    def crear_intento(self, persona_id, numero_doc, ambiente):
        """
        Registra un intento de apertura automática de cerradura.
        
        En desarrollo: actualmente no hace nada real,
        pero mantiene la compatibilidad con el código que lo llama.
        """
        logger.debug(f"[LOCK_STUB] crear_intento: {numero_doc} en {ambiente}")
        return type('Intento', (), {'id': 'stub_' + str(persona_id)})()
    
    def buscar_intento_activo(self, persona_id, ambiente):
        """Busca un intento activo para esta persona/ambiente."""
        logger.debug(f"[LOCK_STUB] buscar_intento_activo: {persona_id} en {ambiente}")
        return None
    
    def cancelar_intento(self, intento_id):
        """Cancela un intento de cerradura."""
        logger.debug(f"[LOCK_STUB] cancelar_intento: {intento_id}")
        return True
    
    def obtener_estadisticas_intento(self, intento_id):
        """Obtiene estadísticas de un intento."""
        logger.debug(f"[LOCK_STUB] obtener_estadisticas_intento: {intento_id}")
        return {
            'intentos': 0,
            'estado': 'cancelado',
            'timestamp_creacion': None,
            'timestamp_cancelacion': None
        }
    
    def activar_cerradura(self, duracion=10):
        """Activa la cerradura por N segundos."""
        logger.debug(f"[LOCK_STUB] activar_cerradura por {duracion}s")
        return {'ok': False, 'razon': 'Sistema de cerraduras en desarrollo'}
    
    def desactivar_cerradura(self):
        """Desactiva la cerradura."""
        logger.debug(f"[LOCK_STUB] desactivar_cerradura")
        return True
    
    def limpiar_intentos_expirados(self):
        """Limpia intentos que han expirado."""
        logger.debug(f"[LOCK_STUB] limpiar_intentos_expirados")
        return 0


# Instancia global
lock_scheduler = LockSchedulerStub()

__all__ = ['lock_scheduler']
