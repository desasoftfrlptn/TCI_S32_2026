import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://planta:planta@localhost:5432/planta")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
PLANTA_TZ = os.getenv("PLANTA_TZ", "America/Argentina/Buenos_Aires")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Autenticación. En producción JWT_SECRET debe venir del entorno.
JWT_SECRET = os.getenv("JWT_SECRET", "solo-para-desarrollo-cambiar-en-produccion")
JWT_HORAS = int(os.getenv("JWT_HORAS", "8"))
PBKDF2_ITERACIONES = int(os.getenv("PBKDF2_ITERACIONES", "600000"))
SEED_PASSWORD = os.getenv("SEED_PASSWORD", "planta123")

# Notificaciones (RN-09): "log" (adaptador falso) o "smtp" (Mailhog o un servidor real).
NOTIFICADOR = os.getenv("NOTIFICADOR", "log")
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
SMTP_REMITENTE = os.getenv("SMTP_REMITENTE", "planta-en-orden@planta.local")
