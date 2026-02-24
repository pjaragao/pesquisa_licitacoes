
import sqlite3
conn = sqlite3.connect('database/licitacoes.db')
cursor = conn.execute("""
    SELECT numero_controle_pncp, COUNT(*) as qtd 
    FROM pesquisa_resultados 
    WHERE numero_controle_pncp IS NOT NULL
    GROUP BY numero_controle_pncp 
    HAVING qtd > 1
""")
dupes = cursor.fetchall()
if dupes:
    print(f"Foram encontrados {len(dupes)} números de controle PNCP duplicados!")
    for d in dupes:
        print(f"Controle: {d[0]} | Quantidade: {d[1]}")
else:
    print("Nenhuma duplicata de numero_controle_pncp encontrada.")

print("\nVerificando UNIQUE constraints no SQL da tabela...")
cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pesquisa_resultados'")
sql = cursor.fetchone()[0]
print(sql)

conn.close()
