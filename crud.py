from sqlalchemy.orm import Session
import models, schemas, security

def get_usuario_por_email(db: Session, email: str):
    """Busca si el usuario existe en la base de datos"""
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def crear_usuario(db: Session, usuario: schemas.UsuarioCrear):
    """Hashea la clave y guarda al nuevo empleado"""
    hashed_password = security.get_password_hash(usuario.password)
    
    db_usuario = models.Usuario(
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        area=usuario.area,
        rol=usuario.rol,
        hashed_password=hashed_password # Guardamos el Hash, NO la clave
    )
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def crear_pregunta(db: Session, pregunta: schemas.PreguntaCrear):
    """Guarda una pregunta generada por la IA en la base de datos"""
    db_pregunta = models.Pregunta(
        modulo_id=pregunta.modulo_id,
        enunciado=pregunta.enunciado,
        opcion_a=pregunta.opcion_a,
        opcion_b=pregunta.opcion_b,
        opcion_c=pregunta.opcion_c,
        opcion_correcta=pregunta.opcion_correcta
    )
    db.add(db_pregunta)
    db.commit()
    db.refresh(db_pregunta)
    return db_pregunta

def crear_modulo(db: Session, modulo: schemas.ModuloCrear):
    """Guarda una nueva capacitación en la base de datos"""
    db_modulo = models.Modulo(
        titulo=modulo.titulo,
        publico_objetivo=modulo.publico_objetivo,
        url_pdf=modulo.url_pdf
    )
    db.add(db_modulo)
    db.commit()
    db.refresh(db_modulo)
    return db_modulo