"""
Configurações do Sistema de Pesquisa de Licitações
"""
import os
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurações do Banco de Dados (SQLite)
DATABASE_PATH = BASE_DIR / "database" / "licitacoes.db"

# URL base do Portal de Compras Públicas
PORTAL_BASE_URL = "https://www.portaldecompraspublicas.com.br"
PORTAL_SEARCH_URL = f"{PORTAL_BASE_URL}/processos"

# Configurações do Selenium
SELENIUM_HEADLESS = True  # True para rodar sem abrir navegador
SELENIUM_TIMEOUT = 30  # Timeout em segundos

# Configurações do Google Drive (a ser configurado futuramente)
GOOGLE_DRIVE_ENABLED = False
GOOGLE_DRIVE_FOLDER_ID = ""  # ID da pasta raiz no Google Drive

# Pasta local para downloads temporários
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Configurações da aplicação Flask
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
FLASK_DEBUG = True
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
