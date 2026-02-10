import os
import sys
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

# --- LOGIQUE DE PARTAGE DES MODÈLES ---
# On remonte au dossier racine GitFetch/
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# On importe db et Utilisateur depuis le models.py à la racine
from models import db, Utilisateur 

# Instance locale pour gérer la session admin
login_manager = LoginManager()

def create_app():
    # Chargement du .env racine
    load_dotenv(dotenv_path=root_path / ".env")

    app = Flask(__name__)

    # --- CONFIGURATION ---
    app.config['SECRET_KEY'] = os.getenv('ADMIN_SECRET_KEY') or os.getenv('SECRET_KEY')
    
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- INITIALISATION ---
    db.init_app(app)
    login_manager.init_app(app)
    
    # Si un utilisateur non connecté tente d'accéder à l'admin, 
    # on le renvoie vers le port 5001 (Auth)
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    login_manager.login_view = f"{auth_url}/login"

    # --- USER LOADER ---
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))

    # --- BLUEPRINTS ---
    from .routes import admin_bp
    app.register_blueprint(admin_bp)

    return app