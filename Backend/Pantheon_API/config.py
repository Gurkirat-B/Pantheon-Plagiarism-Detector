# ================================================
# config for database connection and JWT settings
# ================================================

DB_HOST = "pantheon-db.c3eceugucfdv.us-east-2.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "Pantheon_db"
DB_USER = "Pantheon"
DB_PASS = "pantheon11!"

S3_BUCKET = "pantheon-submissions"

JWT_SECRET_KEY = "secretkey"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINS = 60