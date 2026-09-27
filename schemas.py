from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- ESQUEMAS DE USUARIO ---
class UsuarioBase(BaseModel):
    nombre_completo: str
    email: EmailStr
    area: str
    rol: str = "operario"

class UsuarioCrear(UsuarioBase):
    password: str # Solo se usa al crear, viaja encriptada a la BD

class UsuarioRespuesta(UsuarioBase):
    id: int
    is_active: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True # Permite leer datos de SQLAlchemy

# --- ESQUEMAS DE LOGIN ---
class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    usuario_id: int


# --- ESQUEMAS PARA PREGUNTAS (IA) ---
class PreguntaCrear(BaseModel):
    modulo_id: int
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_correcta: str # Debe ser 'a', 'b' o 'c'

class PreguntaRespuesta(PreguntaCrear):
    id: int

    class Config:
        from_attributes = True


# --- ESQUEMAS DE MÓDULOS ---
class ModuloBase(BaseModel):
    titulo: str
    publico_objetivo: str
    url_pdf: str = ""

class ModuloCrear(ModuloBase):
    pass

class ModuloRespuesta(ModuloBase):
    id: int
    is_active: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# AGREGAR ESTE NUEVO ESQUEMA:
class ModuloNuevoForm(BaseModel):
    titulo: str
    publico_objetivo: str
    fecha_vencimiento: Optional[str] = None
    metodo_creacion: str
    manual_id: Optional[int] = None
    
    # Reemplazamos 'tipo' y 'cantidad_preguntas' por las nuevas reglas
    cant_preguntas_practica: int
    cant_preguntas_evaluacion: int
    porcentaje_aprobacion: int = 70

# --- ESQUEMAS DE CERTIFICACIONES ---
class CertificacionCrear(BaseModel):
    usuario_id: int
    modulo_id: int
    titulo_modulo_aprobado: str
    puntaje: int

class CertificacionRespuesta(CertificacionCrear):
    id: int
    fecha_aprobacion: datetime

    class Config:
        from_attributes = True

# --- endpoint de chat ---
class ChatMensaje(BaseModel):
    pregunta: str