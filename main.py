import requests
import httpx
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from pydantic import BaseModel

from database import engine, get_db, Base
import models, schemas, crud, security

# Crea las tablas si no existen
Base.metadata.create_all(bind=engine)

# Lee el archivo .env y carga las variables en la memoria del servidor
load_dotenv()

app = FastAPI()

# Reemplazá esto con el link exacto que te dio Vercel
frontend_url = os.getenv("FRONTEND_URL", "https://front-seguridad-logistica-app.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "https://front-seguridad-logistica-app.vercel.app"  # <-- Faltaba agregar la variable aquí
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Cloudinary
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

@app.get("/")
def read_root():
    return {"estado": "Servidor Dervinsa operando correctamente con Seguridad JWT"}

# --- ENDPOINTS DE USUARIOS ---

@app.post("/registro", response_model=schemas.UsuarioRespuesta)
def registrar_usuario(usuario: schemas.UsuarioCrear, db: Session = Depends(get_db)):
    # 1. Verificamos que el email no exista
    db_user = crud.get_usuario_por_email(db, email=usuario.email)
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado en el sistema")
    
    # 2. Creamos al usuario de forma segura
    return crud.crear_usuario(db=db, usuario=usuario)

@app.post("/token", response_model=schemas.Token)
def login_generar_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Buscamos al usuario
    usuario = crud.get_usuario_por_email(db, email=form_data.username)
    
    # 2. Verificamos credenciales
    if not usuario or not security.verificar_password(form_data.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales corporativas incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Creamos el Token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.crear_token_acceso(
        data={"sub": usuario.email, "rol": usuario.rol}, expires_delta=access_token_expires
    )
    
    # 4. Devolvemos TODO (incluyendo el ID para los certificados)
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "rol": usuario.rol,
        "usuario_id": usuario.id
    }

# --- ENDPOINTS DE INTEGRACIÓN CON n8n ---

@app.post("/webhook/n8n/preguntas", status_code=status.HTTP_201_CREATED)
def recibir_preguntas_ia(preguntas: List[schemas.PreguntaCrear], db: Session = Depends(get_db)):
    """
    Este endpoint es exclusivo para que n8n entregue los resultados de Gemini.
    Recibe un array de preguntas y las guarda en la base de datos.
    """
    preguntas_guardadas = []
    
    for p in preguntas:
        nueva_pregunta = crud.crear_pregunta(db, p)
        preguntas_guardadas.append(nueva_pregunta)
        
    return {
        "mensaje": f"Se insertaron {len(preguntas_guardadas)} preguntas generadas por IA exitosamente.",
        "modulo_id": preguntas[0].modulo_id if preguntas else None
    }

# --- ENDPOINTS DE MÓDULOS ---

# 1. CREAR EL BORRADOR
@app.post("/api/modulos")
def crear_borrador_modulo(datos: schemas.ModuloNuevoForm, db: Session = Depends(get_db)):
    url_pdf = ""
    
    # Si eligió IA, buscamos la URL de Cloudinary en la tabla Manuales
    if datos.manual_id:
        manual = db.query(models.Manual).filter(models.Manual.id == datos.manual_id).first()
        if manual:
            url_pdf = manual.url_cloudinary # Usamos url_cloudinary como lo guardaste en tu upload_pdf
            
    # Creamos el registro como borrador (is_active=False)
    nuevo_modulo = models.Modulo(
        titulo=datos.titulo,
        publico_objetivo=datos.publico_objetivo,
        url_pdf=url_pdf,
        is_active=False,
        cant_preguntas_practica=datos.cant_preguntas_practica,
        cant_preguntas_evaluacion=datos.cant_preguntas_evaluacion,
        porcentaje_aprobacion=datos.porcentaje_aprobacion,
        fecha_vencimiento=datos.fecha_vencimiento
    )
    
    db.add(nuevo_modulo)
    db.commit()
    db.refresh(nuevo_modulo)
    
    return {"id": nuevo_modulo.id, "mensaje": "Borrador creado"}


# 2. OBTENER PREGUNTAS PARA EL EDITOR
@app.get("/api/modulos/{modulo_id}/preguntas")
def obtener_preguntas_editor(modulo_id: int, db: Session = Depends(get_db)):
    preguntas = db.query(models.Pregunta).filter(models.Pregunta.modulo_id == modulo_id).all()
    return preguntas


# 3. GUARDAR CAMBIOS Y ACTIVAR
@app.post("/api/modulos/{modulo_id}/activar")
async def activar_modulo_final(modulo_id: int, request: Request, db: Session = Depends(get_db)):
    modulo = db.query(models.Modulo).filter(models.Modulo.id == modulo_id).first()
    if modulo:
        modulo.is_active = True
        
    db.commit()
    return {"mensaje": "¡Módulo publicado con éxito!"}


@app.post("/test-ia")
def disparar_n8n(solicitud: SolicitudIA):
    """Este endpoint simula al frontend pidiéndole a FastAPI que despierte a n8n"""
    url_n8n = "http://localhost:5678/webhook/generar-preguntas"
    
    payload = {
        "texto": solicitud.texto_manual,
        "modulo_id": solicitud.modulo_id
    }
    
    # Le disparamos a n8n y esperamos que termine
    respuesta = requests.post(url_n8n, json=payload)
    
    return {"status_n8n": respuesta.status_code, "detalle": "Petición enviada a la IA exitosamente"}

@app.post("/upload-pdf")
async def subir_pdf_cloudinary(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Sube a Cloudinary y guarda el registro en PostgreSQL"""
    try:
        resultado = cloudinary.uploader.upload(
            file.file, 
            resource_type="raw",
            folder="manuales_induccion",
            public_id=file.filename
        )
        
        peso_formateado = f"{(resultado.get('bytes') / (1024 * 1024)):.2f} MB"
        
        # Guardamos en la base de datos
        nuevo_manual = models.Manual(
            nombre=file.filename,
            peso=peso_formateado,
            url_cloudinary=resultado.get("secure_url")
        )
        db.add(nuevo_manual)
        db.commit()
        db.refresh(nuevo_manual)
        
        return {
            "mensaje": "Archivo guardado exitosamente",
            "manual": nuevo_manual
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/manuales")
def obtener_manuales(db: Session = Depends(get_db)):
    """Devuelve la lista de todos los manuales subidos"""
    # Los ordenamos por ID descendente para ver el más nuevo arriba
    return db.query(models.Manual).order_by(models.Manual.id.desc()).all()

# 1. ACTUALIZAMOS EL ESQUEMA: Esto le dice a FastAPI qué datos exactos debe esperar ahora
class SolicitudIA(BaseModel):
    manual_id: int
    url_pdf: str
    cantidad_preguntas: int
    tipo_modulo: str

# 2. LA RUTA QUE RECIBE ESTE ESQUEMA
@app.post("/api/generar-evaluacion")
async def iniciar_generacion_ia(solicitud: SolicitudIA, background_tasks: BackgroundTasks):
    
    async def notificar_n8n():
        # Usamos la URL de test temporalmente para poder ver la magia en n8n
        url_webhook_n8n = os.getenv("N8N_WEBHOOK_URL")
        
        payload = {
            "manual_id": solicitud.manual_id,
            "url_pdf": solicitud.url_pdf,
            "cantidad_preguntas": solicitud.cantidad_preguntas,
            "contexto": f"Genera preguntas para un módulo de tipo: {solicitud.tipo_modulo}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url_webhook_n8n, json=payload, timeout=10.0)
            except Exception as e:
                print(f"Error contactando a n8n: {e}")

    background_tasks.add_task(notificar_n8n)
    
    return {
        "mensaje": "Proceso de IA iniciado", 
        "estado": "procesando",
        "detalles": f"Generando {solicitud.cantidad_preguntas} preguntas."
    }

@app.post("/api/guardar-preguntas")
async def recibir_preguntas_ia(
    request: Request, 
    modulo_id: int, 
    db: Session = Depends(get_db)
):
    try:
        # El JSON que nos manda n8n con la lista de preguntas
        lista_preguntas = await request.json()
        
        # Iteramos sobre el array y creamos los registros en PostgreSQL
        for p in lista_preguntas:
            nueva_pregunta = models.Pregunta(
                modulo_id=modulo_id,
                enunciado=p.get("pregunta"),
                opcion_a=p.get("opciones", {}).get("a"),
                opcion_b=p.get("opciones", {}).get("b"),
                opcion_c=p.get("opciones", {}).get("c"),
                opcion_correcta=p.get("correcta")
            )
            db.add(nueva_pregunta)
            
        # Guardamos todo de una sola vez
        db.commit()
        
        return {"mensaje": "Preguntas guardadas en BD con éxito", "estado": "ok"}
    
    except Exception as e:
        db.rollback()
        return {"error": f"Fallo al guardar en BD: {str(e)}"}


# OBTENER TODOS LOS MÓDULOS (Para llenar las tarjetas)
@app.get("/api/modulos")
def listar_modulos(db: Session = Depends(get_db)):
    # Los ordenamos para que el más nuevo salga primero
    return db.query(models.Modulo).order_by(models.Modulo.id.desc()).all()

# ELIMINAR UN MÓDULO
@app.delete("/api/modulos/{modulo_id}")
def eliminar_modulo(modulo_id: int, db: Session = Depends(get_db)):
    modulo = db.query(models.Modulo).filter(models.Modulo.id == modulo_id).first()
    if modulo:
        # Al borrar el módulo, SQLAlchemy borrará automáticamente sus preguntas asociadas 
        # (siempre que la base de datos esté configurada en cascada, de lo contrario se borran a mano)
        db.query(models.Pregunta).filter(models.Pregunta.modulo_id == modulo_id).delete()
        db.delete(modulo)
        db.commit()
        return {"mensaje": "Módulo eliminado con éxito"}
    return {"error": "Módulo no encontrado"}


# GUARDAR CERTIFICADO (Se dispara al terminar el examen)
@app.post("/api/certificaciones", response_model=schemas.CertificacionRespuesta)
def registrar_certificacion(cert: schemas.CertificacionCrear, db: Session = Depends(get_db)):
    nueva_cert = models.Certificacion(
        usuario_id=cert.usuario_id,
        modulo_id=cert.modulo_id,
        titulo_modulo_aprobado=cert.titulo_modulo_aprobado,
        puntaje=cert.puntaje
    )
    db.add(nueva_cert)
    db.commit()
    db.refresh(nueva_cert)
    return nueva_cert

# OBTENER CERTIFICADOS DEL USUARIO (Para la pantalla de Perfil)
@app.get("/api/usuarios/{usuario_id}/certificaciones")
def obtener_certificaciones(usuario_id: int, db: Session = Depends(get_db)):
    # Trae todas las certificaciones del usuario, ordenadas por la más reciente
    certificaciones = db.query(models.Certificacion).filter(
        models.Certificacion.usuario_id == usuario_id
    ).order_by(models.Certificacion.fecha_aprobacion.desc()).all()
    
    return certificaciones

@app.post("/api/chat-asistente")
async def chat_con_manuales(chat: schemas.ChatMensaje, db: Session = Depends(get_db)):
    """
    Recibe la pregunta del operario, la vincula con los manuales de la BD 
    y consulta a n8n/Gemini para obtener una respuesta contextualizada.
    """
    # 1. Buscamos el último manual subido para usarlo como contexto base (o podrías buscar en todos)
    manual_reciente = db.query(models.Manual).order_by(models.Manual.id.desc()).first()
    
    url_webhook_n8n = os.getenv("N8N_CHAT_WEBHOOK_URL")
    
    payload = {
        "pregunta": chat.pregunta,
        "manual_url": manual_reciente.url_cloudinary if manual_reciente else ""
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Llamamos a n8n para que Gemini procese la consulta con el PDF
            respuesta_n8n = await client.post(url_webhook_n8n, json=payload, timeout=15.0)
            datos_ia = respuesta_n8n.json()
            
            # 1. Buscamos en todas las posibles claves que usa n8n por defecto
            texto_final = datos_ia.get("text") or datos_ia.get("output") or datos_ia.get("texto_respuesta")
            
            # 2. Si n8n manda la información con otra estructura, la imprimimos en pantalla para verla
            if not texto_final:
                texto_final = f"Datos recibidos (debug): {datos_ia}"
                
            return {"respuesta": texto_final}
            
        except Exception as e:
            print(f"ERROR CRÍTICO N8N: {str(e)}")
            # Fallback de seguridad si n8n no está activo en ese segundo
            return {"respuesta": f"Consultando protocolos de Planta Sur sobre: '{chat.pregunta}'. Todos los operarios deben regirse bajo la Ley N° 25.877."}


# ruta para borrar manuales
@app.delete("/manuales/{manual_id}")
def eliminar_manual(manual_id: int, db: Session = Depends(get_db)):
    manual = db.query(models.Manual).filter(models.Manual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
    
    db.delete(manual)
    db.commit()
    return {"mensaje": "Manual eliminado correctamente"}

# @app.get("/setup-demo")
# def setup_demo_users(db: Session = Depends(get_db)):
#     usuarios_demo = [
#         {"email": "operario@empresa.com", "rol": "operario"},
#         {"email": "rrhh@empresa.com", "rol": "rrhh"},
#         {"email": "admin@empresa.com", "rol": "admin"}
#     ]
#    
#     creados = []
#     for u in usuarios_demo:
#         usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == u["email"]).first()
#         if not usuario_existente:
#             # Asegurate de usar tu función de encriptación real aquí
#             clave_encriptada = security.get_password_hash("demo1234") 
#             nuevo_usuario = models.Usuario(
#                 email=u["email"], 
#                 hashed_password=clave_encriptada, 
#                 rol=u["rol"]
#             )
#             db.add(nuevo_usuario)
#             creados.append(u["email"])
#            
#     db.commit()
#     return {"mensaje": "Ejecución completada", "cuentas_creadas": creados}