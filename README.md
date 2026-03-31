# 🔍 Sistema de Pesquisa de Licitações - Portal de Compras Públicas

Este sistema automatiza a busca, monitoramento e classificação de licitações públicas, integrando-se diretamente com a API do **PNCP (Portal Nacional de Contratações Públicas)**. Além da pesquisa, o sistema utiliza Inteligência Artificial (via **Genkit**) para classificar as oportunidades de acordo com o perfil da sua empresa.

## 🚀 Funcionalidades

- **Busca Automatizada**: Pesquisa em múltiplos estados (UFs) simultaneamente usando palavras-chave.
- **Gestão de Palavras-Chave**: Painel para cadastrar e monitorar termos de interesse.
- **Filtros Avançados**: Filtre resultados por valor, data, status, UF e classificação de IA.
- **Classificação por IA**: Avaliação automática de editais (Adequado, Não Adequado ou Incerto) com base em um prompt personalizado da empresa.
- **Gestão de Oportunidades**: Salve e gerencie licitações de interesse para acompanhamento posterior.
- **Dashboard de Estatísticas**: Visualize o volume de licitações por status e relevância.

## 🛠️ Tecnologias Utilizadas

### Backend (Python)
- **Flask**: Framework web para a interface e API.
- **SQLite**: Banco de dados leve para armazenamento local.
- **Requests / Selenium**: Integração com a API do PNCP e scrapers auxiliares.
- **Python-dotenv**: Gerenciamento de variáveis de ambiente.

### IA & Classificação (Genkit/Node.js)
- **Firebase Genkit**: Framework para fluxos de IA generativa.
- **Node.js**: Backend para o servidor de classificação.

## 📋 Pré-requisitos

- Python 3.9+
- Node.js 18+ (para o servidor de IA)
- Navegador Google Chrome (caso utilize as funções de scraper legadas)

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
   Crie um arquivo `.env` na raiz do projeto com as seguintes chaves (conforme necessário):
   ```env
   FLASK_APP=main.py
   FLASK_DEBUG=True
   FLASK_SECRET_KEY=sua_chave_secreta
   GENKIT_URL=http://localhost:3100
   ```

4. **Inicie o servidor de IA (Genkit)**:
   ```bash
   cd genkit-server
   npm install
   npm run dev
   ```

## 🏃 Como Executar

1. Com o servidor Genkit rodando (passo 4 acima), volte à raiz e inicie o app Flask:
   ```bash
   python main.py
   ```

2. Acesse a aplicação em: `http://localhost:5000`

## 📂 Estrutura do Projeto

- `app/`: Lógica central (rotas, modelos, serviços).
- `database/`: Scripts de inicialização e migração do SQLite.
- `genkit-server/`: Código do servidor de Inteligência Artificial.
- `static/`: Arquivos CSS, JS e imagens.
- `templates/`: Templates HTML do Flask.
- `main.py`: Ponto de entrada da aplicação.

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir Issues ou enviar Pull Requests.

---
Desenvolvido para otimizar o acompanhamento de compras públicas no Brasil.
