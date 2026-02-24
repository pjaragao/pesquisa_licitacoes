
import sqlite3
conn = sqlite3.connect('database/licitacoes.db')
cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pesquisa_resultados'")
print("Schema atual da tabela pesquisa_resultados:")
print(cursor.fetchone()[0])

print("\nÍndices da tabela:")
cursor = conn.execute("PRAGMA index_list(pesquisa_resultados)")
for row in cursor.fetchall():
    print(row)
    idx_name = row[1]
    cursor2 = conn.execute(f"PRAGMA index_info({idx_name})")
    print(f"  Colunas do índice {idx_name}: {cursor2.fetchall()}")

conn.close()
