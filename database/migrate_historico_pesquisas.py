"""
Migração do Schema - Adiciona tabela historico_pesquisas
Execute com: python database/migrate_historico_pesquisas.py
"""
import sqlite3
import os
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent / "licitacoes.db"

def migrate():
    """Executa a migração criando a tabela de histórico"""
    print(f"📦 Conectando ao banco: {DB_PATH}")
    
    if not DB_PATH.exists():
        print("❌ Banco de dados não encontrado!")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Lê o schema e tenta criar a tabela caso não exista
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_pesquisas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                termos TEXT NOT NULL,         -- JSON list
                ufs TEXT,                     -- JSON list
                incremental INTEGER DEFAULT 0, 
                status TEXT DEFAULT 'pendente',
                progresso INTEGER DEFAULT 0,
                uf_atual TEXT,
                total_encontrados INTEGER DEFAULT 0,
                novos_salvos INTEGER DEFAULT 0,
                atualizados INTEGER DEFAULT 0,
                logs_auditoria TEXT,          -- JSON list
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                finalizado_em DATETIME NULL
            );
        """)
        print("✅ Tabela historico_pesquisas criada/verificada com sucesso!")
        
        # Cria índices básicos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_pesq_status ON historico_pesquisas(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_pesq_criacao ON historico_pesquisas(criado_em);")
        print("✅ Índices criados.")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Erro ao criar tabela: {e}")
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRAÇÃO: Adicionando tabela Historico Pesquisas")
    print("=" * 60)
    migrate()
