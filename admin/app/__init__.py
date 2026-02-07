import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from dotenv import load_dotenv

# 1. On déclare l'objet db tout de suite
db = SQLAlchemy()

def create_app():
    # Chargement du .env racine
    root_path = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=root_path / ".env")

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('ADMIN_SECRET_KEY')
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 2. Initialisation de la db avec l'app
    db.init_app(app)

    # 3. IMPORTATION DES ROUTES ICI (après la déclaration de db)
    from .routes import admin_bp
    app.register_blueprint(admin_bp)

    return app