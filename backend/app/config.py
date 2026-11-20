import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://planta:planta@localhost:5432/planta")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
PLANTA_TZ = os.getenv("PLANTA_TZ", "America/Argentina/Buenos_Aires")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
