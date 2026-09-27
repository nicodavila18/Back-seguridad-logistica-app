# models.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) # NUNCA guardamos la clave real
    area = Column(String) # Mantenimiento, Desarrollo, etc.
    rol = Column(String, default="operario") # operario, rrhh, admin
    is_active = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    # Relación: Un usuario puede tener muchas certificaciones
    certificaciones = relationship("Certificacion", back_populates="usuario")


class Modulo(Base):
    __tablename__ = "modulos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    publico_objetivo = Column(String)
    url_pdf = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # CAMPOS DEL LOBBY
    cant_preguntas_practica = Column(Integer, default=5)
    cant_preguntas_evaluacion = Column(Integer, default=10)
    porcentaje_aprobacion = Column(Integer, default=70)
    fecha_vencimiento = Column(String, nullable=True)

    # RELACIONES RESTAURADAS
    preguntas = relationship("Pregunta", back_populates="modulo")
    certificaciones = relationship("Certificacion", back_populates="modulo") # ¡Esta era la línea que faltaba!


class Certificacion(Base):
    __tablename__ = "certificaciones"

    id = Column(Integer, primary_key=True, index=True)
    
    # Claves foráneas
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    modulo_id = Column(Integer, ForeignKey("modulos.id", ondelete="SET NULL"), nullable=True)

    # La "Fotografía" Inmutable del Logro
    titulo_modulo_aprobado = Column(String, index=True)
    puntaje = Column(Integer)
    fecha_aprobacion = Column(DateTime, default=datetime.utcnow)

    # Relaciones inversas
    modulo = relationship("Modulo", back_populates="certificaciones")
    usuario = relationship("Usuario", back_populates="certificaciones")


class Pregunta(Base):
    __tablename__ = "preguntas"

    id = Column(Integer, primary_key=True, index=True)
    modulo_id = Column(Integer, ForeignKey("modulos.id"))
    enunciado = Column(String)
    opcion_a = Column(String)
    opcion_b = Column(String)
    opcion_c = Column(String)
    opcion_correcta = Column(String) # Guardará 'a', 'b' o 'c'

    modulo = relationship("Modulo")

class Manual(Base):
    __tablename__ = "manuales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    peso = Column(String)
    url_cloudinary = Column(String)