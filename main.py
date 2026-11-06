"""
Sistema de Pesquisa de Licitações - Portal de Compras Públicas
Arquivo principal para execução da aplicação Flask
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask
from app.config import FLASK_SECRET_KEY, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, DATABASE_PATH
from app.routes.api import main as main_bp



def create_app():
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    app.secret_key = FLASK_SECRET_KEY
    
    # Registra blueprint
    app.register_blueprint(main_bp)
    
    return app


def init_database():
    """Inicializa o banco de dados se não existir"""
    if not DATABASE_PATH.exists():
        print("🔧 Inicializando banco de dados...")
        from database.init_db import init_database as db_init
        db_init()
        print("✓ Banco de dados criado!")
    else:
        print(f"✓ Banco de dados encontrado: {DATABASE_PATH}")


def run_app():
    """Função principal"""
    print("=" * 60)
    print("🔍 Sistema de Pesquisa de Licitações")
    print("   Portal de Compras Públicas")
    print("=" * 60)
    
    # Inicializa banco
    init_database()
    
    # Cria e executa aplicação
    app = create_app()
    
    print(f"\n🚀 Servidor iniciando em http://{FLASK_HOST}:{FLASK_PORT}")
    print("   Pressione Ctrl+C para parar\n")
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )


if __name__ == "__main__":
    run_app()

