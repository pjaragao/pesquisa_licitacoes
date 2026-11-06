"""
Script de migração para adicionar suporte à classificação por IA
Adiciona:
- Tabela configuracao_empresa
- Campos classificacao_ia, explicacao_ia, classificado_em na tabela pesquisa_resultados
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "licitacoes.db"


def migrate():
    """Executa a migração do banco de dados"""
    print("🔧 Iniciando migração para suporte à classificação IA...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Criar tabela configuracao_empresa se não existir
        print("  → Criando tabela configuracao_empresa...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracao_empresa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_empresa TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Verificar se campos já existem na tabela pesquisa_resultados
        cursor.execute("PRAGMA table_info(pesquisa_resultados)")
        colunas_existentes = [row[1] for row in cursor.fetchall()]
        
        # 3. Adicionar campos de IA se não existirem
        novos_campos = [
            ('classificacao_ia', 'TEXT'),
            ('explicacao_ia', 'TEXT'),
            ('classificado_em', 'DATETIME')
        ]
        
        for campo, tipo in novos_campos:
            if campo not in colunas_existentes:
                print(f"  → Adicionando campo {campo}...")
                cursor.execute(f'''
                    ALTER TABLE pesquisa_resultados 
                    ADD COLUMN {campo} {tipo}
                ''')
            else:
                print(f"  ✓ Campo {campo} já existe")
        
        conn.commit()
        print("✅ Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
