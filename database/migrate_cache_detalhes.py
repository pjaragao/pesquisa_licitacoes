import sqlite3
import os

def migrate():
    db_path = 'database/licitacoes.db'
    if not os.path.exists(db_path):
        # Tenta o path absoluto se o relativo falhar (como dentro do docker)
        db_path = '/app/database/licitacoes.db'

    print(f"🔄 Conectando ao banco de dados em: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Tabela de Itens
        print("➕ Criando tabela 'oportunidade_itens'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oportunidade_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oportunidade_id INTEGER,
                numero_item INTEGER,
                descricao TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario_estimado REAL,
                valor_total REAL,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (oportunidade_id) REFERENCES oportunidades(id) ON DELETE CASCADE
            )
        ''')

        # 2. Tabela de Arquivos
        print("➕ Criando tabela 'oportunidade_arquivos'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oportunidade_arquivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oportunidade_id INTEGER,
                titulo TEXT,
                url TEXT,
                tipo_documento TEXT,
                data_publicacao TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (oportunidade_id) REFERENCES oportunidades(id) ON DELETE CASCADE
            )
        ''')

        # 3. Tabela de Historico
        print("➕ Criando tabela 'oportunidade_historico'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oportunidade_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oportunidade_id INTEGER,
                situacao TEXT,
                data_hora TEXT,
                observacao TEXT,
                usuario TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (oportunidade_id) REFERENCES oportunidades(id) ON DELETE CASCADE
            )
        ''')

        # 4. Indices para performance
        print("⚡ Criando índices...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_itens_oportunidade ON oportunidade_itens(oportunidade_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_arquivos_oportunidade ON oportunidade_arquivos(oportunidade_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historico_oportunidade ON oportunidade_historico(oportunidade_id)')

        conn.commit()
        print("🎉 Migração de cache de detalhes concluída com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
