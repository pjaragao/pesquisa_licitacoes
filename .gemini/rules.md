# Regras do Projeto: Pesquisa de Licitações

## Visão Geral
Sistema web para busca, monitoramento e classificação de licitações públicas brasileiras. Integra com a **API PNCP** (Portal Nacional de Contratações Públicas) para dados e o **Firebase Genkit** para classificação por IA.

## Idioma
- Todo o código (variáveis, funções, classes, docstrings, mensagens) é escrito em **português brasileiro**.
- Comentários no código em português.
- Nomes de arquivos e pastas em português sem acentos (usar underscore `_`).

## Stack Tecnológico

### Backend Python (Flask)
- **Framework**: Flask com Blueprints.
- **Banco de dados**: SQLite (`database/licitacoes.db`). Usar `app.get_db()` (context manager) para conexões.
- **Entrada principal**: `main.py` → `create_app()` (factory pattern).
- **Ponto de início**: sempre executar com `python main.py`.

### Frontend
- Templates Jinja2 em `templates/`.
- CSS puro em `static/css/`.
- JavaScript puro em `static/js/`.
- Sem frameworks frontend (sem React, Vue, etc).

### Servidor de IA (Genkit)
- Projeto Node.js/TypeScript separado em `genkit-server/`.
- Rodar com `cd genkit-server && npm run dev`.
- Comunicação via HTTP (porta 3400 por padrão, configurável via `GENKIT_URL`).
- Chave de API do Gemini definida em `.env` como `GOOGLE_GENAI_API_KEY`.

## Estrutura do Projeto

```
├── main.py                  # Ponto de entrada Flask
├── requirements.txt         # Dependências Python
├── .env                     # Variáveis de ambiente (NÃO versionar)
├── app/
│   ├── __init__.py          # get_db(), get_db_connection()
│   ├── config.py            # Constantes globais (BASE_DIR, DATABASE_PATH, etc)
│   ├── routes/
│   │   └── api.py           # Todas as rotas (Blueprint 'main')
│   ├── models/
│   │   ├── palavra_chave.py        # Termos de busca
│   │   ├── resultado_pesquisa.py   # Licitações encontradas
│   │   ├── oportunidade.py         # Licitações selecionadas para acompanhar
│   │   └── configuracao_empresa.py # Prompt para classificação IA
│   └── services/
│       ├── pncp_api_client.py      # Cliente HTTP da API PNCP
│       ├── pncp_search_service.py  # Lógica de pesquisa/filtragem
│       ├── search_manager.py       # Coordenação de buscas em background (threads)
│       ├── genkit_service.py       # Comunicação com servidor Genkit
│       └── oportunidade_service.py # Lógica de criação de oportunidades
├── database/
│   ├── schema.sql           # Schema completo do banco
│   ├── init_db.py           # Inicialização do banco
│   ├── migrate_ia.py        # Migração para campos de IA
│   └── migrate_schema_pncp.py  # Migração para campos da API PNCP
├── genkit-server/
│   ├── src/index.ts         # Fluxos Genkit (classificação, otimização de prompt)
│   └── package.json
├── templates/               # HTML (Jinja2)
└── static/                  # CSS e JS
```

## Padrões de Código

### Models
- Cada model é uma classe com métodos estáticos de CRUD (`criar`, `listar_todos`, `buscar_por_id`, `deletar`).
- Todos usam `app.get_db()` como context manager para transações.
- Conversão para dict via método `to_dict()`.

### Services
- Lógica de negócio fica nos services, nunca nas rotas.
- Singletons instanciados no final do módulo (ex: `genkit_service = GenkitService()`).
- `search_manager` é um Singleton com thread daemon para buscas em background.

### Routes
- Todas as rotas estão em `app/routes/api.py` sob o Blueprint `main`.
- Prefixo `/api/` para endpoints JSON (retornam `jsonify()`).
- Rotas sem prefixo são páginas HTML (retornam `render_template()`).
- Rotas `/form_*` são handlers de formulário que usam `redirect()` + `flash()`.

## API PNCP

- **Base URL**: `https://pncp.gov.br/api/consulta`
- **Documentação**: https://pncp.gov.br/api/consulta/swagger-ui/index.html
- **Endpoint principal**: `/v1/contratacoes/proposta` (contratações com propostas abertas)
- **Rate limiting**: usar delay entre requisições (0.3s) e retry com backoff exponencial.
- A busca é feita por **UF** (a API não aceita busca por texto livre), e a filtragem por palavra-chave é feita localmente no Python (`PncpSearchService`).
- Máximo de 50 resultados por página na API.

## Classificação por IA

- O usuário configura um "prompt da empresa" descrevendo o perfil de atuação.
- A classificação é feita em lotes de 20 resultados.
- Categorias: `ADEQUADO`, `NAO_ADEQUADO`, `INCERTO`.
- Delay de 1.5s entre lotes para respeitar cotas da API Gemini.
- O Genkit expõe endpoints: `/api/classificar`, `/api/classificar-lote`, `/api/otimizar-prompt`, `/api/modelos`.

## Regras Importantes

1. **NÃO usar web scraping** – O projeto migrou integralmente para a API PNCP.
2. **NÃO criar scripts de debug/migração soltos na raiz** – Se necessário, colocar em `database/` para migrações ou usar scripts temporários em `/tmp/`.
3. **Variáveis sensíveis** (API keys, secrets) devem ficar exclusivamente no `.env`.
4. **Migrations de banco** devem ser adicionados em `database/` com nomes descritivos.
5. A pasta `downloads/` armazena arquivos de oportunidades — é mantida no `.gitignore`.
6. Os documentos de referência da API estão em `app/docs_API_PNCP/` (PDFs).
