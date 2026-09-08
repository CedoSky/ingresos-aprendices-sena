import json
import os
import shutil
from datetime import datetime
from models import db, Respaldo
from config import Config


# ── Importación diferida para evitar import circular con sync_manager ──────────
def _guardar_respaldo_local(tipo, datos, descripcion, usuario_id):
    try:
        from sync_manager import guardar_pendiente
        return guardar_pendiente(tipo, datos, descripcion, usuario_id)
    except Exception as e:
        print(f"[CLOUD] ✗ No se pudo guardar en cola local: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# USB Storage Manager — escribe directamente en el pendrive
# ══════════════════════════════════════════════════════════════════════════════

class USBStorageManager:
    """
    Gestiona respaldos en un pendrive (o carpeta de red).
    Detecta automáticamente el pendrive conectado en Windows escaneando
    las letras de unidad D:..Z:. Si se define USB_PATH_OVERRIDE en .env
    se usa esa ruta directamente.
    """

    def __init__(self):
        self.carpeta_usb = Config.USB_BACKUP_FOLDER  # Subcarpeta dentro de la USB
        self._ruta_usb   = None                       # Se resuelve al primer uso

    # ── Detección de la USB ────────────────────────────────────────────────────

    def _detectar_usb(self) -> str | None:
        """
        Devuelve la ruta base de la USB disponible, o None si no hay ninguna.
        Primero revisa USB_PATH_OVERRIDE; luego escanea D: … Z: en Windows.
        """
        override = Config.USB_PATH_OVERRIDE
        if override and os.path.exists(override):
            return os.path.abspath(override)

        # Escanear letras de unidad en Windows (excluir A: B: C:)
        for letra in 'DEFGHIJKLMNOPQRSTUVWXYZ':
            ruta = f"{letra}:\\"
            if os.path.exists(ruta):
                # Verificar que podemos escribir (no es solo lectura)
                try:
                    test = os.path.join(ruta, '_sena_test_write')
                    with open(test, 'w') as f:
                        f.write('ok')
                    os.remove(test)
                    return ruta
                except (OSError, PermissionError):
                    continue

        return None

    def _ruta_respaldos(self) -> str | None:
        """
        Devuelve la carpeta de respaldos dentro de la USB, creándola si no existe.
        Retorna None si no hay USB disponible.
        """
        usb = self._detectar_usb()
        if not usb:
            return None
        ruta = os.path.join(usb, self.carpeta_usb)
        os.makedirs(ruta, exist_ok=True)
        return ruta

    # ── Interfaz pública (misma que S3Manager) ─────────────────────────────────

    def verificar_conexion(self) -> bool:
        """Comprueba si el pendrive está conectado y es escribible."""
        resultado = self._ruta_respaldos() is not None
        if not resultado:
            print("[USB] ⚠ Pendrive no detectado")
        return resultado

    def subir_respaldo(self, datos: dict, nombre_archivo: str, descripcion: str = "") -> dict:
        """
        Guarda el snapshot JSON + copia de sena.db en el pendrive.
        'subir' se llama igual que en S3 para mantener la misma interfaz.
        """
        carpeta = self._ruta_respaldos()
        if not carpeta:
            return {'success': False, 'error': 'Pendrive no disponible'}

        try:
            timestamp      = datetime.now().strftime('%Y%m%d_%H%M%S')
            respaldo_dir   = os.path.join(carpeta, f'respaldo_{timestamp}')
            os.makedirs(respaldo_dir, exist_ok=True)

            # 1. JSON con el snapshot de datos
            json_path = os.path.join(respaldo_dir, nombre_archivo)
            body = json.dumps(datos, ensure_ascii=False, indent=2).encode('utf-8')
            with open(json_path, 'wb') as f:
                f.write(body)

            # 2. Copia binaria de sena.db (para restauración directa)
            db_origen = self._buscar_db()
            if db_origen:
                db_destino = os.path.join(respaldo_dir, 'sena.db')
                shutil.copy2(db_origen, db_destino)

            # 3. Nota informativa
            info_path = os.path.join(respaldo_dir, 'INFO_RESPALDO.txt')
            with open(info_path, 'w', encoding='utf-8') as f:
                fecha = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"RESPALDO SENA — {fecha}\n")
                f.write(f"Descripción: {descripcion or 'Automático'}\n")
                f.write(f"Archivos: {nombre_archivo}, sena.db\n")

            usb_key = respaldo_dir.replace('\\', '/')
            print(f"[USB] ✅ Respaldo guardado: {respaldo_dir}")
            return {'success': True, 's3_key': usb_key, 'size': len(body)}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def descargar_respaldo(self, usb_key: str) -> dict:
        """Lee el JSON de respaldo desde la carpeta del pendrive."""
        try:
            # usb_key es la ruta de la carpeta del respaldo
            carpeta = usb_key.replace('/', os.sep)
            # Buscar el primer .json que no sea INFO
            for nombre in os.listdir(carpeta):
                if nombre.endswith('.json'):
                    with open(os.path.join(carpeta, nombre), 'r', encoding='utf-8') as f:
                        datos = json.load(f)
                    return {'success': True, 'datos': datos}
            return {'success': False, 'error': 'No se encontró archivo JSON en el respaldo'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def listar_respaldos(self) -> dict:
        """Lista las carpetas de respaldo disponibles en la USB."""
        carpeta = self._ruta_respaldos()
        if not carpeta:
            return {'success': False, 'error': 'Pendrive no disponible'}
        try:
            respaldos = []
            for item in sorted(os.listdir(carpeta), reverse=True):
                ruta_item = os.path.join(carpeta, item)
                if os.path.isdir(ruta_item) and item.startswith('respaldo_'):
                    tamaño = sum(
                        os.path.getsize(os.path.join(ruta_item, f))
                        for f in os.listdir(ruta_item)
                        if os.path.isfile(os.path.join(ruta_item, f))
                    )
                    respaldos.append({
                        'key':   ruta_item.replace('\\', '/'),
                        'size':  tamaño,
                        'fecha': item.replace('respaldo_', '')
                    })
            return {'success': True, 'respaldos': respaldos}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _buscar_db() -> str | None:
        """Localiza sena.db en la carpeta habitual del backend."""
        base = os.path.dirname(__file__)
        for ruta in [
            os.path.join(base, 'instance', 'sena.db'),
            os.path.join(base, 'sena.db'),
        ]:
            if os.path.exists(ruta):
                return ruta
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Network Drive Manager — escribe en una carpeta compartida de otra laptop
# ══════════════════════════════════════════════════════════════════════════════

class NetworkDriveManager:
    """
    Guarda respaldos en una carpeta compartida de otra laptop en la red local.

    Configuración en backend/.env:
        STORAGE_BACKEND=network
        NETWORK_BACKUP_PATH=\\\\192.168.1.50\\SENA_RESPALDOS
        NETWORK_USERNAME=usuario_remoto   # solo si la carpeta pide contraseña
        NETWORK_PASSWORD=clave_remota     # solo si la carpeta pide contraseña

    Cómo compartir la carpeta en la otra laptop (Windows):
        1. Crear carpeta SENA_RESPALDOS en el disco duro de la otra laptop.
        2. Click derecho → Propiedades → Compartir → Uso compartido avanzado.
        3. Marcar "Compartir esta carpeta", dar permisos de escritura.
        4. Anotar la IP de esa laptop (ipconfig en cmd) y ponerla en NETWORK_BACKUP_PATH.
    """

    def __init__(self):
        self.ruta_red  = Config.NETWORK_BACKUP_PATH.strip()
        self.usuario   = Config.NETWORK_USERNAME.strip()
        self.password  = Config.NETWORK_PASSWORD.strip()
        self.timeout   = Config.NETWORK_TIMEOUT
        self._montado  = False   # True si ya se ejecutó 'net use' exitosamente

    # ── Conexión a la carpeta compartida ──────────────────────────────────────

    def _montar_recurso(self) -> bool:
        """
        En Windows, si la carpeta compartida requiere credenciales ejecuta
        'net use' para autenticarse. Solo lo hace una vez por sesión.
        """
        if self._montado:
            return True
        if not self.ruta_red:
            return False
        # Si no hay credenciales, Windows usa las del usuario actual
        if not self.usuario:
            self._montado = True
            return True
        try:
            import subprocess
            resultado = subprocess.run(
                ['net', 'use', self.ruta_red, f'/user:{self.usuario}', self.password,
                 '/persistent:no'],
                capture_output=True, text=True, timeout=self.timeout
            )
            if resultado.returncode == 0:
                self._montado = True
                print(f"[NETWORK] ✅ Conectado a {self.ruta_red}")
                return True
            # Error 2 = ya estaba conectado
            if resultado.returncode == 2:
                self._montado = True
                return True
            print(f"[NETWORK] ⚠ net use retornó código {resultado.returncode}: {resultado.stderr.strip()}")
            return False
        except Exception as e:
            print(f"[NETWORK] ✗ Error al montar recurso: {e}")
            return False

    def verificar_conexion(self) -> bool:
        """Comprueba si la carpeta remota es accesible."""
        if not self.ruta_red:
            print("[NETWORK] ⚠ NETWORK_BACKUP_PATH no configurado en .env")
            return False
        self._montar_recurso()
        try:
            accesible = os.path.exists(self.ruta_red)
            if not accesible:
                print(f"[NETWORK] ⚠ No se puede acceder a {self.ruta_red} — ¿la otra laptop está encendida?")
            return accesible
        except Exception as e:
            print(f"[NETWORK] ✗ Error verificando red: {e}")
            return False

    # ── Operaciones de respaldo ────────────────────────────────────────────────

    def subir_respaldo(self, datos: dict, nombre_archivo: str, descripcion: str = "") -> dict:
        """Copia el snapshot JSON + sena.db en la carpeta remota."""
        if not self.verificar_conexion():
            return {'success': False, 'error': 'Carpeta remota no accesible'}

        try:
            timestamp    = datetime.now().strftime('%Y%m%d_%H%M%S')
            respaldo_dir = os.path.join(self.ruta_red, f'respaldo_{timestamp}')
            os.makedirs(respaldo_dir, exist_ok=True)

            # 1. JSON con snapshot de datos
            json_path = os.path.join(respaldo_dir, nombre_archivo)
            body = json.dumps(datos, ensure_ascii=False, indent=2).encode('utf-8')
            with open(json_path, 'wb') as f:
                f.write(body)

            # 2. Copia binaria de sena.db
            db_origen = self._buscar_db()
            if db_origen:
                shutil.copy2(db_origen, os.path.join(respaldo_dir, 'sena.db'))

            # 3. Nota informativa
            with open(os.path.join(respaldo_dir, 'INFO_RESPALDO.txt'), 'w', encoding='utf-8') as f:
                fecha = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                f.write(f"RESPALDO SENA — {fecha}\n")
                f.write(f"Origen: {os.environ.get('COMPUTERNAME', 'servidor')}\n")
                f.write(f"Descripción: {descripcion or 'Automático'}\n")
                f.write(f"Archivos: {nombre_archivo}, sena.db\n")

            net_key = respaldo_dir.replace('\\', '/')
            print(f"[NETWORK] ✅ Respaldo guardado en red: {respaldo_dir}")
            return {'success': True, 's3_key': net_key, 'size': len(body)}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def descargar_respaldo(self, net_key: str) -> dict:
        """Lee el JSON de respaldo desde la carpeta remota."""
        try:
            carpeta = net_key.replace('/', os.sep)
            for nombre in os.listdir(carpeta):
                if nombre.endswith('.json'):
                    with open(os.path.join(carpeta, nombre), 'r', encoding='utf-8') as f:
                        datos = json.load(f)
                    return {'success': True, 'datos': datos}
            return {'success': False, 'error': 'No se encontró JSON en el respaldo'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def listar_respaldos(self) -> dict:
        """Lista los respaldos disponibles en la carpeta remota."""
        if not self.verificar_conexion():
            return {'success': False, 'error': 'Carpeta remota no accesible'}
        try:
            respaldos = []
            for item in sorted(os.listdir(self.ruta_red), reverse=True):
                ruta_item = os.path.join(self.ruta_red, item)
                if os.path.isdir(ruta_item) and item.startswith('respaldo_'):
                    tamaño = sum(
                        os.path.getsize(os.path.join(ruta_item, f))
                        for f in os.listdir(ruta_item)
                        if os.path.isfile(os.path.join(ruta_item, f))
                    )
                    respaldos.append({
                        'key':   ruta_item.replace('\\', '/'),
                        'size':  tamaño,
                        'fecha': item.replace('respaldo_', '')
                    })
            return {'success': True, 'respaldos': respaldos}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _buscar_db() -> str | None:
        base = os.path.dirname(__file__)
        for ruta in [
            os.path.join(base, 'instance', 'sena.db'),
            os.path.join(base, 'sena.db'),
        ]:
            if os.path.exists(ruta):
                return ruta
        return None


# ══════════════════════════════════════════════════════════════════════════════
# S3 Storage Manager — sube a AWS S3 (opción alternativa)
# ══════════════════════════════════════════════════════════════════════════════

class S3Manager:
    def __init__(self):
        import boto3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        self.bucket = Config.AWS_S3_BUCKET

    def verificar_conexion(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            print(f"[S3] Error conectando: {e}")
            return False

    def subir_respaldo(self, datos, nombre_archivo, descripcion=""):
        try:
            s3_key = f"respaldos/{nombre_archivo}"
            body   = json.dumps(datos).encode('utf-8')
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=body,
                ContentType='application/json',
                Metadata={'descripcion': descripcion, 'fecha': datetime.utcnow().isoformat()}
            )
            return {'success': True, 's3_key': s3_key, 'size': len(body)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def descargar_respaldo(self, s3_key):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            datos = json.loads(response['Body'].read().decode('utf-8'))
            return {'success': True, 'datos': datos}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def listar_respaldos(self):
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix='respaldos/')
            respaldos = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    respaldos.append({'key': obj['Key'], 'size': obj['Size'],
                                      'fecha': obj['LastModified'].isoformat()})
            return {'success': True, 'respaldos': respaldos}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def eliminar_respaldo(self, s3_key):
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# Fábrica: elige USB o S3 según STORAGE_BACKEND en .env
# ══════════════════════════════════════════════════════════════════════════════

def crear_storage_manager():
    """
    Retorna el manager de almacenamiento configurado.
    STORAGE_BACKEND=network → NetworkDriveManager  (disco duro de otra laptop en red)
    STORAGE_BACKEND=usb     → USBStorageManager    (pendrive)
    STORAGE_BACKEND=s3      → S3Manager            (AWS S3)
    """
    backend = getattr(Config, 'STORAGE_BACKEND', 'usb').lower()
    if backend == 'network':
        return NetworkDriveManager()
    if backend == 's3':
        return S3Manager()
    return USBStorageManager()


# ══════════════════════════════════════════════════════════════════════════════
# Database Backup Manager
# ══════════════════════════════════════════════════════════════════════════════

class DatabaseBackupManager:
    def __init__(self):
        self.storage = crear_storage_manager()

    # ── Extracción de datos ────────────────────────────────────────────────────

    @staticmethod
    def _extraer_datos_bd():
        from models import Persona, RegistroAcceso
        datos = {
            'timestamp': datetime.utcnow().isoformat(),
            'tipo': 'completo',
            'personas': [],
            'registros_acceso': []
        }
        for p in Persona.query.filter_by(deleted_at=None).all():
            datos['personas'].append({
                'id': p.id, 'nombre': p.nombre, 'tipo_doc': p.tipo_doc,
                'numero_doc': p.numero_doc, 'email': p.email,
                'perfil': p.perfil, 'programa': p.programa, 'ficha': p.ficha
            })
        for r in RegistroAcceso.query.filter_by(deleted_at=None).all():
            datos['registros_acceso'].append({
                'id': r.id, 'numero_doc': r.numero_doc, 'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat(), 'ambiente': r.ambiente
            })
        return datos

    # ── Respaldo con fallback local ────────────────────────────────────────────

    def crear_respaldo_completo(self, usuario_id, descripcion=""):
        """
        Crea un respaldo completo.
        - Si el pendrive/S3 está disponible → guarda allí de inmediato.
        - Si no está disponible → guarda en pending_sync/ para sincronizar
          automáticamente cuando el destino vuelva a estar accesible.
        """
        try:
            timestamp      = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"respaldo_completo_{timestamp}.json"
            datos          = self._extraer_datos_bd()

            if not self.storage.verificar_conexion():
                ruta_local = _guardar_respaldo_local('completo', datos, descripcion, usuario_id)
                return {
                    'success': True,
                    'modo': 'local',
                    'mensaje': 'Pendrive/destino no disponible — respaldo en cola, se sincronizará automáticamente',
                    'ruta_local': ruta_local
                }

            resultado = self.storage.subir_respaldo(datos, nombre_archivo, descripcion)

            if resultado['success']:
                respaldo = Respaldo(
                    nombre_archivo=nombre_archivo,
                    tipo='completo',
                    s3_key=resultado['s3_key'],
                    tamaño_bytes=resultado['size'],
                    descripcion=descripcion,
                    creado_por_id=usuario_id
                )
                db.session.add(respaldo)
                db.session.commit()
                return {'success': True, 'modo': getattr(Config, 'STORAGE_BACKEND', 'usb'),
                        'respaldo_id': respaldo.id}
            else:
                print(f"[CLOUD] ⚠ Error al guardar: {resultado.get('error')} — encolando localmente")
                ruta_local = _guardar_respaldo_local('completo', datos, descripcion, usuario_id)
                return {
                    'success': True,
                    'modo': 'local',
                    'mensaje': f"Error destino: {resultado.get('error')} — respaldo guardado localmente",
                    'ruta_local': ruta_local
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def restaurar_desde_respaldo(self, respaldo_id, usuario_id):
        from models import Persona, RegistroAcceso
        try:
            respaldo = Respaldo.query.get(respaldo_id)
            if not respaldo:
                return {'success': False, 'error': 'Respaldo no encontrado'}

            descarga = self.storage.descargar_respaldo(respaldo.s3_key)
            if not descarga['success']:
                return descarga

            datos = descarga['datos']
            for p_data in datos.get('personas', []):
                persona = Persona.query.filter_by(numero_doc=p_data['numero_doc']).first()
                if not persona:
                    persona = Persona(
                        nombre=p_data.get('nombre'), tipo_doc=p_data.get('tipo_doc'),
                        numero_doc=p_data.get('numero_doc'), email=p_data.get('email'),
                        perfil=p_data.get('perfil'), programa=p_data.get('programa'),
                        ficha=p_data.get('ficha')
                    )
                    db.session.add(persona)
            db.session.commit()

            respaldo.restaurado_en = datetime.utcnow()
            db.session.commit()
            return {'success': True, 'mensaje': 'Respaldo restaurado'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Importación diferida para evitar import circular con sync_manager
def _guardar_respaldo_local(tipo, datos, descripcion, usuario_id):
    """Delega al sync_manager para guardar localmente cuando S3 no está disponible."""
    try:
        from sync_manager import guardar_pendiente
        return guardar_pendiente(tipo, datos, descripcion, usuario_id)
    except Exception as e:
        print(f"[CLOUD] ✗ No se pudo guardar en cola local: {e}")
        return None

class S3Manager:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        self.bucket = Config.AWS_S3_BUCKET
    
    def verificar_conexion(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            print(f"Error conectando S3: {e}")
            return False
    
    def subir_respaldo(self, datos, nombre_archivo, descripcion=""):
        try:
            s3_key = f"respaldos/{nombre_archivo}"
            body = json.dumps(datos).encode('utf-8')
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=body,
                ContentType='application/json',
                Metadata={
                    'descripcion': descripcion,
                    'fecha': datetime.utcnow().isoformat()
                }
            )
            
            return {'success': True, 's3_key': s3_key, 'size': len(body)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def descargar_respaldo(self, s3_key):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            datos = json.loads(response['Body'].read().decode('utf-8'))
            return {'success': True, 'datos': datos}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def listar_respaldos(self):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix='respaldos/'
            )
            
            respaldos = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    respaldos.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'fecha': obj['LastModified'].isoformat()
                    })
            
            return {'success': True, 'respaldos': respaldos}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def eliminar_respaldo(self, s3_key):
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generar_url_descarga(self, s3_key, expiracion=3600):
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expiracion
            )
            return {'success': True, 'url': url}
        except Exception as e:
            return {'success': False, 'error': str(e)}

class DatabaseBackupManager:
    def __init__(self):
        self.s3 = S3Manager()

    # ── Extracción de datos ────────────────────────────────────────────────────

    @staticmethod
    def _extraer_datos_bd():
        """Construye el snapshot completo de la BD para respaldar."""
        from models import Persona, RegistroAcceso

        datos = {
            'timestamp': datetime.utcnow().isoformat(),
            'tipo': 'completo',
            'personas': [],
            'registros_acceso': []
        }

        personas = Persona.query.filter_by(deleted_at=None).all()
        for p in personas:
            datos['personas'].append({
                'id': p.id,
                'nombre': p.nombre,
                'tipo_doc': p.tipo_doc,
                'numero_doc': p.numero_doc,
                'email': p.email,
                'perfil': p.perfil,
                'programa': p.programa,
                'ficha': p.ficha
            })

        registros = RegistroAcceso.query.filter_by(deleted_at=None).all()
        for r in registros:
            datos['registros_acceso'].append({
                'id': r.id,
                'numero_doc': r.numero_doc,
                'tipo': r.tipo,
                'timestamp': r.timestamp.isoformat(),
                'ambiente': r.ambiente
            })

        return datos

    # ── Respaldo con fallback local ────────────────────────────────────────────

    def crear_respaldo_completo(self, usuario_id, descripcion=""):
        """
        Crea un respaldo completo e intenta subirlo a S3.
        Si S3 no está disponible, guarda los datos localmente en la cola de
        sincronización (pending_sync/) para ser subidos cuando la nube vuelva.
        """
        try:
            timestamp      = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"respaldo_completo_{timestamp}.json"
            datos          = self._extraer_datos_bd()

            # ── Intentar subir a S3 ────────────────────────────────────────────
            if not self.s3.verificar_conexion():
                ruta_local = _guardar_respaldo_local('completo', datos, descripcion, usuario_id)
                return {
                    'success': True,
                    'modo': 'local',
                    'mensaje': 'Nube no disponible — respaldo guardado localmente, se sincronizará automáticamente',
                    'ruta_local': ruta_local
                }

            resultado = self.s3.subir_respaldo(datos, nombre_archivo, descripcion)

            if resultado['success']:
                respaldo = Respaldo(
                    nombre_archivo=nombre_archivo,
                    tipo='completo',
                    s3_key=resultado['s3_key'],
                    tamaño_bytes=resultado['size'],
                    descripcion=descripcion,
                    creado_por_id=usuario_id
                )
                db.session.add(respaldo)
                db.session.commit()
                return {'success': True, 'modo': 'nube', 'respaldo_id': respaldo.id}
            else:
                # S3 reportó error — guardar local como respaldo de seguridad
                print(f"[CLOUD] ⚠ S3 retornó error: {resultado.get('error')} — guardando localmente")
                ruta_local = _guardar_respaldo_local('completo', datos, descripcion, usuario_id)
                return {
                    'success': True,
                    'modo': 'local',
                    'mensaje': f"Error S3: {resultado.get('error')} — respaldo guardado localmente",
                    'ruta_local': ruta_local
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def restaurar_desde_respaldo(self, respaldo_id, usuario_id):
        from models import Persona, RegistroAcceso
        
        try:
            respaldo = Respaldo.query.get(respaldo_id)
            if not respaldo:
                return {'success': False, 'error': 'Respaldo no encontrado'}
            
            descarga = self.s3.descargar_respaldo(respaldo.s3_key)
            if not descarga['success']:
                return descarga
            
            datos = descarga['datos']
            
            for p_data in datos.get('personas', []):
                persona = Persona.query.filter_by(numero_doc=p_data['numero_doc']).first()
                if not persona:
                    persona = Persona(
                        nombre=p_data.get('nombre'),
                        tipo_doc=p_data.get('tipo_doc'),
                        numero_doc=p_data.get('numero_doc'),
                        email=p_data.get('email'),
                        perfil=p_data.get('perfil'),
                        programa=p_data.get('programa'),
                        ficha=p_data.get('ficha')
                    )
                    db.session.add(persona)
            
            db.session.commit()
            
            respaldo.restaurado_en = datetime.utcnow()
            db.session.commit()
            
            return {'success': True, 'mensaje': 'Respaldo restaurado'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
