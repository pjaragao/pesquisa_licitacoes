
import sqlite3
conn = sqlite3.connect('database/licitacoes.db')
try:
    print("Criando índice único para numero_controle_pncp...")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pncp ON pesquisa_resultados(numero_controle_pncp) WHERE numero_controle_pncp IS NOT NULL")
    conn.commit()
    print("✓ Índice de proteção contra duplicatas criado com sucesso!")
except Exception as e:
    print(f"Erro ao criar índice: {e}")
conn.close()
