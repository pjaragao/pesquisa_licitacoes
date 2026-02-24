
import sqlite3
conn = sqlite3.connect('database/licitacoes.db')
cursor = conn.execute("PRAGMA table_info(pesquisa_resultados)")
for row in cursor.fetchall():
    print(row)
conn.close()
