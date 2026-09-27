from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# En producción, esto va en un archivo .env oculto
SECRET_KEY = "1894"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 # El token dura 2 horas

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