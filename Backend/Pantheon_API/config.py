# ================================================
# config for database connection and JWT settings
# ================================================
import os

DB_HOST = os.environ["PANTHEON_DB_HOST"]
DB_PORT = os.environ["PANTHEON_DB_PORT"]
DB_NAME = os.environ["PANTHEON_DB_NAME"]
DB_USER = os.environ["PANTHEON_DB_USER"]
DB_PASS = os.environ["PANTHEON_DB_PASSWORD"]

S3_BUCKET = os.environ["PANTHEON_S3_BUCKET"]

JWT_SECRET_KEY = os.environ["PANTHEON_JWT_SECRET_KEY"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINS = 60