# application.py
import os
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from models import db, Utilisateur
from routes import auth_bp, main_bp, admin_bp, portfolio_bp, github_bp

# Charger les variables d'environnement depuis .env
load_dotenv()

def create_application():
    application = Flask(__name__)
    
    # ============================================
    # CONFIGURATION DE LA BASE DE DONNÉES POSTGRESQL
    # ============================================
    
    # Utilisation directe de DATABASE_URL depuis .env
    application.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///gitfetch.db')
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Afficher la base de données utilisée (sans le mot de passe pour la sécurité)
    db_uri = application.config['SQLALCHEMY_DATABASE_URI']
    if 'postgresql' in db_uri:
        print(f"✅ Connexion à PostgreSQL: {db_uri.split('@')[1] if '@' in db_uri else db_uri}")
    else:
        print(f"⚠️ Utilisation de SQLite: {db_uri}")
    
    # ============================================
    # CONFIGURATION DES EMAILS
    # ============================================
    
    application.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    application.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    application.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    application.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    
    # ============================================
    # CONFIGURATION OAUTH
    # ============================================
    
    application.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    application.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
    application.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    application.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # ============================================
    # INITIALISATION DES EXTENSIONS
    # ============================================
    
    # Initialisation SQLAlchemy
    db.init_app(application)
    
    # Initialisation Flask-Migrate
    migrate = Migrate(application, db)
    
    # Initialisation Flask-Mail
    mail = Mail()
    mail.init_app(application)
    
    # Initialisation Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(application)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Utilisateur, int(user_id))
    
    # Initialisation OAuth
    oauth = OAuth(application)
    
    # Configuration GitHub OAuth
    if application.config['GITHUB_CLIENT_ID'] and application.config['GITHUB_CLIENT_SECRET']:
        oauth.register(
            name='github',
            client_id=application.config['GITHUB_CLIENT_ID'],
            client_secret=application.config['GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com',
            client_kwargs={'scope': 'user:email'},
        )
        print("✅ GitHub OAuth configuré")
    else:
        print("⚠️ GitHub OAuth non configuré (clés manquantes)")
    
    # Configuration Google OAuth
    if application.config['GOOGLE_CLIENT_ID'] and application.config['GOOGLE_CLIENT_SECRET']:
        oauth.register(
            name='google',
            client_id=application.config['GOOGLE_CLIENT_ID'],
            client_secret=application.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        print("✅ Google OAuth configuré")
    else:
        print("⚠️ Google OAuth non configuré (clés manquantes)")
    
    # Stockage des extensions
    application.extensions['mail'] = mail
    application.extensions['oauth'] = oauth
    application.extensions['login_manager'] = login_manager
    
    # ============================================
    # ENREGISTREMENT DES BLUEPRINTS
    # ============================================
    
    application.register_blueprint(auth_bp)
    application.register_blueprint(main_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(portfolio_bp)
    application.register_blueprint(github_bp)
    
    # ============================================
    # CRÉATION DES DOSSIERS MEDIA
    # ============================================
    
    media_folders = [
        os.path.join(application.root_path, 'media', 'profiles'),
        os.path.join(application.root_path, 'media', 'covers'),
        os.path.join(application.root_path, 'media', 'docs'),
        os.path.join(application.root_path, 'media', 'projects'),
        os.path.join(application.root_path, 'media', 'about'),
        os.path.join(application.root_path, 'media', 'uploads'),
    ]
    
    for folder in media_folders:
        os.makedirs(folder, exist_ok=True)
    
    return application

# ============================================
# POINT D'ENTRÉE POUR GUNICORN ET COMMANDES FLASK
# ============================================

# Création de l'application
application = create_application()

# Alias pour Flask CLI (certaines commandes attendent 'app')
app = application

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║   🚀 GitFetch - Serveur de Développement                 ║")
    print(f"║   📍 Accès : http://{host}:{port}                         ║")
    print(f"║   📦 Base de données: {'PostgreSQL' if 'postgresql' in str(application.config['SQLALCHEMY_DATABASE_URI']) else 'SQLite'} ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    application.run(host=host, port=port, debug=debug)