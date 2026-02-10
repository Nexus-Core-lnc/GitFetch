import os
import sys
from flask import Flask
from pathlib import Path
from dotenv import load_dotenv

# --- ÉTAPE 1 : AJOUT DU CHEMIN SYSTÈME ---
# On ajoute le dossier racine "GitFetch" au chemin de recherche Python
# Cela permet d'importer 'models' même si on est dans le dossier 'portfolio'
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

# --- ÉTAPE 2 : IMPORTS ---
# Maintenant que le chemin est ajouté, on peut importer les modèles
from models import db, Projet, Utilisateur 

def create_app():
    # Chargement du .env situé à la racine du projet
    env_path = root_path / ".env"
    load_dotenv(dotenv_path=env_path)

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('PORTFOLIO_SECRET_KEY', 'dev_key_123')
    
    # Configuration de la base de données
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        # Correction pour Heroku/PostgreSQL qui utilise parfois postgres:// au lieu de postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', '')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'portfolio_db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation de la base de données avec l'app
    db.init_app(app)

    # Import et enregistrement du Blueprint
    # On l'importe ici pour éviter les imports circulaires
    from .routes import portfolio_bp
    app.register_blueprint(portfolio_bp)

    return app