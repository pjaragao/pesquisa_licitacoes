
import sqlite3
conn = sqlite3.connect('database/licitacoes.db')
try:
    conn.execute("ALTER TABLE pesquisa_resultados ADD COLUMN atualizado_em DATETIME")
    print("Coluna atualizado_em adicionada com sucesso!")
except Exception as e:
    print(f"Aviso: {e}")
conn.commit()
conn.close()
