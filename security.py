import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# Obtenemos las credenciales del entorno
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256") # Mantenemos HS256 como valor por defecto si no se especifica
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# Configuración de Bcrypt para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_password(plain_password, hashed_password):
    """Compara la contraseña en texto plano con el hash de la base de datos"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Convierte la contraseña real en un hash indescifrable"""
    return pwd_context.hash(password)

def crear_token_acceso(data: dict, expires_delta: timedelta = None):
    """Crea la 'pulsera VIP' (JWT) para el frontend"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Agregamos la fecha de expiración al token
    to_encode.update({"exp": expire})
    # Firmamos el token con nuestra clave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt