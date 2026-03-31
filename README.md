# 🔍 Pesquisa de Licitações - API PNCP

Sistema web para busca, monitoramento e classificação inteligente de licitações públicas brasileiras, integrando diretamente com a **API do PNCP** (Portal Nacional de Contratações Públicas) e utilizando **IA generativa** (Gemini via Genkit) para classificação automática de oportunidades.

## 🚀 Funcionalidades

- **Busca Automatizada via API PNCP** — Pesquisa em múltiplos estados (UFs) simultaneamente usando palavras-chave, com suporte a buscas incrementais.
- **Gestão de Palavras-Chave** — Painel para cadastrar, ativar/desativar e monitorar termos de interesse.
- **Filtros Avançados** — Filtre resultados por valor, data, status, UF, classificação de IA e ordenação flexível.
- **Classificação por IA** — Avaliação automática de editais (Adequado, Não Adequado ou Incerto) com base em um prompt personalizado que descreve o perfil da empresa.
- **Otimização de Prompt** — IA que sugere melhorias no prompt de classificação da empresa.
- **Gestão de Oportunidades** — Salve e gerencie licitações de interesse para acompanhamento.
- **Dashboard de Estatísticas** — Visualize o volume de licitações encontradas e classificadas.

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.9+ / Flask |
| Banco de Dados | SQLite |
| API de Dados | API PNCP (Portal Nacional de Contratações Públicas) |
| IA / Classificação | Firebase Genkit (Node.js/TypeScript) + Google Gemini |
| Frontend | HTML (Jinja2) + CSS + JS puro |

## 📋 Pré-requisitos

- Python 3.9+
- Node.js 18+ (para o servidor de IA)

## 🔧 Instalação

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/pjaragao/pesquisa_licitacoes.git
   cd pesquisa_licitacoes
   ```

2. **Configure o ambiente Python**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**:
   Crie um arquivo `.env` na raiz do projeto:
   ```env
   GOOGLE_GENAI_API_KEY=sua_chave_api_gemini
   GENKIT_PORT=3400
   ```
   > Obtenha sua chave em: https://aistudio.google.com/app/apikey

4. **Instale as dependências do servidor de IA**:
   ```bash
   cd genkit-server
   npm install
   ```

## 🏃 Como Executar

1. **Inicie o servidor de IA** (em um terminal):
   ```bash
   cd genkit-server
   npm run dev
   ```

2. **Inicie a aplicação Flask** (em outro terminal):
   ```bash
   python main.py
   ```

3. Acesse: `http://localhost:5000`

## 📂 Estrutura do Projeto

```
├── main.py                     # Ponto de entrada da aplicação
├── requirements.txt            # Dependências Python
├── app/
│   ├── config.py               # Configurações globais
│   ├── routes/api.py           # Todas as rotas (páginas + API)
│   ├── models/                 # Modelos de dados (SQLite)
│   └── services/               # Lógica de negócio
│       ├── pncp_api_client.py  # Cliente HTTP da API PNCP
│       ├── pncp_search_service.py  # Pesquisa e filtragem
│       ├── search_manager.py   # Buscas em background
│       ├── genkit_service.py   # Integração com IA
│       └── oportunidade_service.py
├── database/                   # Schema e migrações do SQLite
├── genkit-server/              # Servidor de IA (Genkit/TypeScript)
├── templates/                  # Templates HTML (Jinja2)
└── static/                     # CSS e JavaScript
```

## 🤝 Contribuição

Contribuições são bem-vindas! Abra Issues ou envie Pull Requests.

---
Desenvolvido para otimizar o acompanhamento de compras públicas no Brasil.
