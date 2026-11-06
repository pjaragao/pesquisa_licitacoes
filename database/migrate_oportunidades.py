import sqlite3
import os
import sys

def migrate():
    # Caminho para o banco de dados
    db_path = os.path.join(os.path.dirname(__file__), 'licitacoes.db')
    print(f"🔄 Conectando ao banco de dados em: {db_path}", flush=True)
    
    try:
        # Usar timeout curto para falhar rápido se estiver travado
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        
        # Array de colunas a verificar e adicionar
        columns_to_add = [
            ("url_processo", "TEXT"),
            ("valor_estimado", "TEXT")
        ]
        
        # Verificar quais colunas já existem
        cursor.execute("PRAGMA table_info(oportunidades)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"➕ Adicionando coluna '{col_name}'...", flush=True)
                cursor.execute(f"ALTER TABLE oportunidades ADD COLUMN {col_name} {col_type}")
                print(f"✅ Coluna '{col_name}' adicionada com sucesso.", flush=True)
            else:
                print(f"⚠️ Coluna '{col_name}' já existe. Ignorando.", flush=True)
                
        conn.commit()
        print("🎉 Migração concluída com sucesso!", flush=True)
        
    except sqlite3.OperationalError as e:
         print(f"❌ Erro operacional (provável banco lockado): {e}", flush=True)
         print("Por favor, reinicie a aplicação Flask para liberar o banco de dados e tente novamente.", flush=True)
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}", flush=True)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
