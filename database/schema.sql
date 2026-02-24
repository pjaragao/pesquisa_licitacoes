-- Schema do Banco de Dados - Sistema de Pesquisa de Licitações
-- Banco: SQLite

-- Tabela de palavras-chave para pesquisa
CREATE TABLE IF NOT EXISTS palavras_chave (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    termo TEXT NOT NULL UNIQUE,
    ativo INTEGER DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultima_pesquisa DATETIME NULL
);

-- Tabela de resultados resumidos (Etapa 1)
CREATE TABLE IF NOT EXISTS pesquisa_resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    palavra_chave_id INTEGER,
    numero_processo TEXT,
    titulo TEXT,
    objeto TEXT,
    orgao TEXT,
    uf TEXT,
    municipio TEXT,
    modalidade TEXT,
    status TEXT,
    data_realizacao TEXT,
    url_processo TEXT,
    valor_estimado TEXT,  -- Valor de referência/estimado da contratação
    inicio_propostas TEXT, -- Data de início das propostas
    limite_recebimento TEXT, -- Data limite para recebimento
    abertura_propostas TEXT, -- Data de abertura das propostas
    selecionado_detalhe INTEGER DEFAULT 0,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (palavra_chave_id) REFERENCES palavras_chave(id),
    UNIQUE (numero_processo, orgao)
);

-- Tabela de oportunidades (Etapa 2 - após detalhamento)
CREATE TABLE IF NOT EXISTS oportunidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,  -- OPXXYYY (ex: OP26001)
    resultado_id INTEGER,
    
    -- Dados básicos
    numero_processo TEXT,
    titulo TEXT,
    objeto TEXT,
    
    -- Órgão/Local
    orgao TEXT,
    uf TEXT,
    municipio TEXT,
    
    -- Tipo/Modalidade
    tipo TEXT,
    modalidade TEXT,
    tratamento_fase_lances TEXT,
    operacao TEXT,
    modo_disputa TEXT,
    
    -- Pessoas envolvidas
    pregoeiro TEXT,
    autoridade_competente TEXT,
    apoio TEXT,
    
    -- Recursos e Legislação
    origem_recursos TEXT,
    legislacao_aplicavel TEXT,
    
    -- Datas importantes
    data_publicacao TEXT,
    inicio_propostas TEXT,
    limite_impugnacoes TEXT,
    limite_esclarecimentos TEXT,
    limite_recebimento_propostas TEXT,
    abertura_propostas TEXT,
    
    -- Status
    status TEXT,
    
    -- Documentos
    pasta_local TEXT,  -- Caminho local dos documentos
    pasta_google_drive TEXT,  -- Link da pasta no Google Drive (futuro)
    
    -- Análise futura
    analisado_ia INTEGER DEFAULT 0,
    resultado_analise TEXT,
    
    -- Timestamps
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (resultado_id) REFERENCES pesquisa_resultados(id)
);

-- Tabela de empresas (para futura análise de atestados)
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT NOT NULL,
    cnpj TEXT NOT NULL UNIQUE,
    ativo INTEGER DEFAULT 1,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de atestados técnicos das empresas
CREATE TABLE IF NOT EXISTS atestados_tecnicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER,
    descricao TEXT,
    categoria TEXT,
    arquivo_path TEXT,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- Tabela de análise oportunidade x empresa
CREATE TABLE IF NOT EXISTS analise_capacidade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oportunidade_id INTEGER,
    empresa_id INTEGER,
    pode_participar INTEGER,
    justificativa TEXT,
    atestados_utilizados TEXT,
    analisado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (oportunidade_id) REFERENCES oportunidades(id),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- Índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_resultados_palavra ON pesquisa_resultados(palavra_chave_id);
CREATE INDEX IF NOT EXISTS idx_resultados_status ON pesquisa_resultados(status);
CREATE INDEX IF NOT EXISTS idx_oportunidades_codigo ON oportunidades(codigo);
CREATE INDEX IF NOT EXISTS idx_atestados_empresa ON atestados_tecnicos(empresa_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pncp ON pesquisa_resultados(numero_controle_pncp) WHERE numero_controle_pncp IS NOT NULL;

-- Tabela de configuração do prompt da empresa (para classificação IA)
CREATE TABLE IF NOT EXISTS configuracao_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_empresa TEXT,
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
