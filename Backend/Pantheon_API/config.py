# ================================================
# config for database connection and JWT settings
# ================================================

import os

#DB_HOST = os.getenv("PANTHEON_DB_HOST")
#DB_PORT = os.getenv("PANTHEON_DB_PORT", "5432")
#DB_NAME = os.getenv("PANTHEON_DB_NAME")
#DB_USER = os.getenv("PANTHEON_DB_USER")
#DB_PASS = os.getenv("PANTHEON_DB_PASSWORD")

DB_HOST = "pantheon-db.c3eceugucfdv.us-east-2.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "Pantheon_db"
DB_USER = "Pantheon"
DB_PASS = "pantheon11!"


#S3_BUCKET = os.getenv("PANTHEON_S3_BUCKET")
S3_BUCKET = "pantheon-submissions"

#JWT_SECRET_KEY = os.getenv("PANTHEON_JWT_SECRET_KEY", "change_this_secret_key")
JWT_SECRET_KEY = "secretkey"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINS = 60