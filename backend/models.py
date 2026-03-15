from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class BaseModel(db.Model):
    """Modelo base con campos comunes"""
    __abstract__ = True
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
        db.session.commit()

class Usuario(BaseModel):
    """Usuarios administradores"""
    __tablename__ = 'usuarios'
    
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), default='vigilante')
    activo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

class Persona(BaseModel):
    """Aprendices, instructores, visitantes"""
    __tablename__ = 'personas'
    
    nombre = db.Column(db.String(255), nullable=False, index=True)
    tipo_doc = db.Column(db.String(10), nullable=False)
    numero_doc = db.Column(db.String(50), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    perfil = db.Column(db.String(50), nullable=False)
    
    programa = db.Column(db.String(255), nullable=True)
    ficha = db.Column(db.String(50), nullable=True)
    especialidad = db.Column(db.String(255), nullable=True)
    area = db.Column(db.String(255), nullable=True)
    
    verificado = db.Column(db.Boolean, default=False)
    datos_adicionales = db.Column(db.JSON, nullable=True)
    
    creado_por_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    actualizado_por_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    
    def __repr__(self):
        return f'<Persona {self.nombre} ({self.numero_doc})>'

class RegistroAcceso(BaseModel):
    """Log de acceso entrada/salida"""
    __tablename__ = 'registros_acceso'
    
    persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=False, index=True)
    numero_doc = db.Column(db.String(50), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ambiente = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    vigilante_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True, index=True)
    
    persona = db.relationship('Persona', backref='accesos')
    vigilante = db.relationship('Usuario', backref='registros_acceso', foreign_keys=[vigilante_id])
    
    def __repr__(self):
        return f'<RegistroAcceso {self.numero_doc} {self.tipo}>'

class CambioHistorial(BaseModel):
    """Auditoría de cambios"""
    __tablename__ = 'cambios_historial'
    
    persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=False, index=True)
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    campo = db.Column(db.String(255), nullable=False)
    valor_anterior = db.Column(db.JSON, nullable=True)
    valor_nuevo = db.Column(db.JSON, nullable=True)
    
    persona = db.relationship('Persona', backref='cambios')
    usuario = db.relationship('Usuario', backref='cambios')
    
    def __repr__(self):
        return f'<CambioHistorial {self.persona_id} {self.campo}>'

class Respaldo(BaseModel):
    """Historial de respaldos en S3"""
    __tablename__ = 'respaldos'
    
    nombre_archivo = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    s3_key = db.Column(db.String(500), nullable=False)
    tamaño_bytes = db.Column(db.BigInteger, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    creado_por_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    restaurado_en = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Respaldo {self.nombre_archivo}>'

class Computador(BaseModel):
    """Equipos (computadores, laptops, etc.)"""
    __tablename__ = 'computadores'
    
    codigo_barras = db.Column(db.String(100), nullable=False, unique=True, index=True)
    serie = db.Column(db.String(100), nullable=True, unique=True, index=True)
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    asignado_a_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=True, index=True)
    ubicacion = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(50), default='activo')
    
    asignado_a = db.relationship('Persona', backref='computadores')
    
    def __repr__(self):
        return f'<Computador {self.codigo_barras} ({self.marca} {self.modelo})>'

class Foto(BaseModel):
    """Fotos de acceso asociadas a personas"""
    __tablename__ = 'fotos'
    
    persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=False, index=True)
    numero_doc = db.Column(db.String(50), nullable=False, index=True)
    registro_acceso_id = db.Column(db.String(36), db.ForeignKey('registros_acceso.id'), nullable=True, index=True)
    imagen_datos = db.Column(db.LargeBinary, nullable=False)
    tipo_contenido = db.Column(db.String(50), default='image/jpeg')
    tamaño_bytes = db.Column(db.Integer, nullable=True)
    
    persona = db.relationship('Persona', backref='fotos')
    registro_acceso = db.relationship('RegistroAcceso', backref='fotos')
    
    def __repr__(self):
        return f'<Foto {self.numero_doc} {self.created_at}>'

class RegistroAccesoEquipo(BaseModel):
    """Registro de entradas/salidas de equipos asociados a personas"""
    __tablename__ = 'registros_acceso_equipo'
    
    computador_id = db.Column(db.String(36), db.ForeignKey('computadores.id'), nullable=False, index=True)
    persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)  # ENTRADA/SALIDA
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    registro_acceso_id = db.Column(db.String(36), db.ForeignKey('registros_acceso.id'), nullable=True, index=True)
    
    computador = db.relationship('Computador', backref='accesos_equipo')
    persona = db.relationship('Persona', backref='accesos_equipo')
    registro_acceso = db.relationship('RegistroAcceso', backref='equipos_asociados')
    
    def __repr__(self):
        return f'<RegistroAccesoEquipo {self.computador_id} {self.tipo}>'


class OcupacionAmbiente(BaseModel):
    """Ocupación de ambientes por instructores — solo aplica a perfil instructor"""
    __tablename__ = 'ocupaciones_ambiente'

    persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=False, index=True)
    numero_doc = db.Column(db.String(50), nullable=False, index=True)
    ambiente = db.Column(db.String(200), nullable=False)
    registro_acceso_id = db.Column(db.String(36), db.ForeignKey('registros_acceso.id'), nullable=True)
    # Estado: 'ocupado' | 'liberado'
    estado = db.Column(db.String(20), default='ocupado', nullable=False, index=True)
    liberado_por = db.Column(db.String(100), nullable=True)   # 'vigilante' | 'salida_instructor'
    liberado_at = db.Column(db.DateTime, nullable=True)

    persona = db.relationship('Persona', backref='ocupaciones_ambiente')
    registro_acceso = db.relationship('RegistroAcceso', backref='ocupacion_ambiente')

    def __repr__(self):
        return f'<OcupacionAmbiente {self.ambiente} [{self.estado}]>'


class RegistroInventario(BaseModel):
    """Inventario de equipos, herramientas y objetos que ingresan a la sede"""
    __tablename__ = 'registros_inventario'

    descripcion       = db.Column(db.String(255), nullable=False)
    cantidad          = db.Column(db.Integer, default=1, nullable=False)
    portador_nombre   = db.Column(db.String(255), nullable=False)
    portador_documento= db.Column(db.String(50),  nullable=False)
    destino           = db.Column(db.String(200),  nullable=True)   # ambiente/destino opcional
    estado            = db.Column(db.String(20), default='EN_SEDE', nullable=False, index=True)  # EN_SEDE | RETIRADO
    fecha_entrada     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_salida      = db.Column(db.DateTime, nullable=True)
    observaciones     = db.Column(db.Text, nullable=True)
    registrado_por    = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<RegistroInventario {self.descripcion} [{self.estado}]>'


class Edificio(BaseModel):
    """Edificios o bloques del centro de formación (ej: Comercio, Industria)"""
    __tablename__ = 'edificios'

    nombre = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.String(255), nullable=True)
    num_pisos = db.Column(db.Integer, nullable=False, default=3)
    num_ambientes_por_piso = db.Column(db.Integer, nullable=False, default=10)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    orden = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<Edificio {self.nombre}>'


class AperturaAmbiente(BaseModel):
    """Cerradura electrónica — registro de aperturas de ambientes"""
    __tablename__ = 'aperturas_ambiente'

    ambiente              = db.Column(db.String(200), nullable=False, index=True)
    abierto_por_persona_id = db.Column(db.String(36), db.ForeignKey('personas.id'), nullable=True)
    abierto_por_usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    cerrado_por_usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    origen                = db.Column(db.String(50), nullable=False)  # 'instructor' | 'vigilante' | 'sistema'
    duracion_minutos      = db.Column(db.Integer, default=4, nullable=False)
    abierto_en            = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    cerrado_en            = db.Column(db.DateTime, nullable=True)  # cierre manual anticipado

    persona    = db.relationship('Persona', backref='aperturas_ambiente')
    usuario    = db.relationship('Usuario', foreign_keys=[abierto_por_usuario_id], backref='aperturas_ambiente_abiertas')
    cerrado_by = db.relationship('Usuario', foreign_keys=[cerrado_por_usuario_id], backref='aperturas_ambiente_cerradas')

    @property
    def esta_abierto(self):
        """Abierto cuando ya pasó el tiempo de espera y no fue cerrado."""
        if self.cerrado_en:
            return False
        return self.abierto_en <= datetime.utcnow()

    @property
    def esta_pendiente(self):
        """Pendiente cuando el tiempo de espera aun no ha terminado."""
        if self.cerrado_en:
            return False
        return self.abierto_en > datetime.utcnow()

    def __repr__(self):
        return f'<AperturaAmbiente {self.ambiente} [{self.origen}]>'


# ═══════════════════════════════════════════════════════════════════════════════
#  MODELOS DE SEGURIDAD AVANZADA (Ley 1581/2012 - HABEAS DATA)
# ═══════════════════════════════════════════════════════════════════════════════

class AuditoriaAdministrativa(db.Model):
    """Auditoría de todas las operaciones administrativas - Cumplimiento normativo"""
    __tablename__ = 'auditoria_administrativa'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.String(100), nullable=False, index=True)
    usuario_id = db.Column(db.String(255), nullable=True, index=True)
    operacion = db.Column(db.String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, etc
    tabla = db.Column(db.String(100), nullable=False, index=True)
    registro_id = db.Column(db.String(255), nullable=True, index=True)
    ip_address = db.Column(db.String(50), nullable=False, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    datos_anterior = db.Column(db.Text, nullable=True)  # JSON stringificado
    datos_nuevo = db.Column(db.Text, nullable=True)  # JSON stringificado
    motivo = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<AuditoriaAdministrativa {self.operacion} {self.tabla} {self.timestamp}>'


class BloqueoCuentas(db.Model):
    """Control de intentos fallidos de login y bloqueos por seguridad"""
    __tablename__ = 'bloqueo_cuentas'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    intentos_fallidos = db.Column(db.Integer, default=0)
    timestamp_primer_intento = db.Column(db.String(100), nullable=True)
    timestamp_bloqueo = db.Column(db.String(100), nullable=True)  # Cuándo se bloqueó
    creado_at = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<BloqueoCuentas {self.email} (intentos: {self.intentos_fallidos})>'

