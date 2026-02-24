"""
Sistema de Pesquisa de Licitações - Portal de Compras Públicas
"""
import sqlite3
from contextlib import contextmanager
from .config import DATABASE_PATH


def get_db_connection():
    """Retorna uma conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn


@contextmanager
def get_db():
    """Context manager para conexão com o banco"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
