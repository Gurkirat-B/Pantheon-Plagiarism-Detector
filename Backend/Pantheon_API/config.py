# ================================================
# config for database connection and JWT settings
# ================================================

import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("PANTHEON_DB_HOST")
DB_PORT = os.getenv("PANTHEON_DB_PORT", "5432")
DB_NAME = os.getenv("PANTHEON_DB_NAME")
DB_USER = os.getenv("PANTHEON_DB_USER")
DB_PASS = os.getenv("PANTHEON_DB_PASSWORD")

S3_BUCKET = os.getenv("PANTHEON_S3_BUCKET")

JWT_SECRET_KEY = os.getenv("PANTHEON_JWT_SECRET_KEY", "pantheon_secret_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINS = 60