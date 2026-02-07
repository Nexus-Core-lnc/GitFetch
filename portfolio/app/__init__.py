import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from dotenv import load_dotenv

db = SQLAlchemy()

def create_app():
    # Chargement du .env
    root_path = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=root_path / ".env")

    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('PORTFOLIO_SECRET_KEY', 'dev_key_123')
    
    # Option 1: Utiliser DATABASE_URL directement
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        # Option 2: Construire l'URL à partir des variables séparées
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'portfolio_db')
        
        app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print(f"📦 DB URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    db.init_app(app)

    from .routes import portfolio_bp
    app.register_blueprint(portfolio_bp)

    return app