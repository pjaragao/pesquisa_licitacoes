"""
Migração do Schema - Adiciona campos da API PNCP
Execute com: python database/migrate_schema_pncp.py
"""
import sqlite3
import os
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent / "licitacoes.db"

# Novos campos a adicionar
NOVOS_CAMPOS = [
    ("numero_controle_pncp", "TEXT"),           # ID único no PNCP
    ("processo", "TEXT"),                        # Número do processo administrativo
    ("valor_estimado_numerico", "REAL"),        # Valor como número para ordenação/filtros
    ("valor_homologado", "REAL"),               # Valor homologado (se houver)
    ("cnpj_orgao", "TEXT"),                     # CNPJ do órgão
    ("codigo_ibge", "TEXT"),                    # Código IBGE do município
    ("modalidade_id", "INTEGER"),               # ID da modalidade
    ("modo_disputa", "TEXT"),                   # Aberto/Fechado
    ("srp", "INTEGER DEFAULT 0"),               # Sistema de Registro de Preços
    ("amparo_legal", "TEXT"),                   # Lei aplicável
    ("data_publicacao_pncp", "TEXT"),           # Data publicação no PNCP
    ("informacao_complementar", "TEXT"),        # Informações adicionais
    ("link_processo_eletronico", "TEXT"),       # Link do processo eletrônico
    ("data_atualizacao_api", "TEXT"),           # Última atualização na API
]


def migrate():
    """Executa a migração adicionando novos campos"""
    print(f"📦 Conectando ao banco: {DB_PATH}")
    
    if not DB_PATH.exists():
        print("❌ Banco de dados não encontrado!")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verifica colunas existentes
    cursor.execute("PRAGMA table_info(pesquisa_resultados)")
    colunas_existentes = {row['name'] for row in cursor.fetchall()}
    
    print(f"📋 Colunas existentes: {len(colunas_existentes)}")
    
    campos_adicionados = 0
    
    for campo, tipo in NOVOS_CAMPOS:
        if campo in colunas_existentes:
            print(f"   ⏭️  {campo} já existe")
            continue
        
        try:
            sql = f"ALTER TABLE pesquisa_resultados ADD COLUMN {campo} {tipo}"
            cursor.execute(sql)
            print(f"   ✅ Adicionado: {campo} ({tipo})")
            campos_adicionados += 1
        except sqlite3.Error as e:
            print(f"   ❌ Erro ao adicionar {campo}: {e}")
    
    # Cria índice para número de controle PNCP
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_numero_controle_pncp 
            ON pesquisa_resultados(numero_controle_pncp)
        """)
        print("   ✅ Índice idx_numero_controle_pncp criado")
    except sqlite3.Error as e:
        print(f"   ⚠️  Índice já existe ou erro: {e}")
    
    # Cria índice para CNPJ
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cnpj_orgao 
            ON pesquisa_resultados(cnpj_orgao)
        """)
        print("   ✅ Índice idx_cnpj_orgao criado")
    except sqlite3.Error as e:
        print(f"   ⚠️  Índice já existe ou erro: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Migração concluída! {campos_adicionados} campos adicionados.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRAÇÃO: Expansão do Schema para API PNCP")
    print("=" * 60)
    migrate()
