"""
Configurações do Sistema de Pesquisa de Licitações
"""
import os
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações do Banco de Dados (SQLite)
DATABASE_PATH = BASE_DIR / "database" / "licitacoes.db"

# Pasta local para downloads de oportunidades
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Configurações da aplicação Flask
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
FLASK_DEBUG = True
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
