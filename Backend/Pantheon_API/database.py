# =======================================================================
# connect to the database using psycopg and return the connection object
# =======================================================================

import psycopg
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def get_db_connection() -> psycopg.Connection:
    """Establishes a connection to the PostgreSQL database."""
    return psycopg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        sslmode="require",
    )