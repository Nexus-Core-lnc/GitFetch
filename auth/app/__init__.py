import os
import sys
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# --- LOGIQUE DE PARTAGE DES MODÈLES ---
# On remonte de 3 niveaux pour atteindre la racine du projet (GitFetch/)
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# Maintenant on peut importer db et les modèles depuis la racine
from models import db, Utilisateur 

# Initialisation des autres extensions
mail = Mail()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()

def create_app():
    # Chargement des variables d'environnement (depuis la racine)
    load_dotenv(dotenv_path=root_path / ".env")
    
    app = Flask(__name__)

    # --- CONFIGURATION DE L'APPLICATION ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    # Configuration de la Base de Données (PostgreSQL)
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuration Mail
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT') or 587)
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

    # --- INITIALISATION DES EXTENSIONS ---
    oauth.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)
    
    # Configuration Login Manager
    login_manager.login_view = 'main.login' 
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"

    # --- ENREGISTREMENT DES CLIENTS OAUTH ---
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    oauth.register(
        name='github',
        client_id=os.getenv('GITHUB_CLIENT_ID'),
        client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        # MODIFICATION : Ajout du scope 'repo' pour voir les collaborations et dépôts privés
        client_kwargs={'scope': 'user:email repo'}
    )

    # --- USER LOADER ---
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))

    # --- BLUEPRINTS ---
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app