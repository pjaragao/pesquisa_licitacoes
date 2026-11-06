"""
Script para inicializar o banco de dados SQLite
"""
import sqlite3
from pathlib import Path

# Caminhos
DB_DIR = Path(__file__).parent
SCHEMA_PATH = DB_DIR / "schema.sql"
DB_PATH = DB_DIR / "licitacoes.db"


def init_database():
    """Inicializa o banco de dados com o schema"""
    print(f"Inicializando banco de dados em: {DB_PATH}")
    
    # Lê o schema SQL
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # Conecta e executa o schema
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema)
        conn.commit()
        print("✓ Banco de dados inicializado com sucesso!")
        
        # Verifica as tabelas criadas
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✓ Tabelas criadas: {', '.join(tables)}")
        
    except Exception as e:
        print(f"✗ Erro ao inicializar banco: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
