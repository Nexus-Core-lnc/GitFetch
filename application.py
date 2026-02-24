# run.py
import os
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from models import db, Utilisateur
from routes import auth_bp, main_bp, admin_bp, portfolio_bp, github_bp

# Charger les variables d'environnement
load_dotenv()

def create_application():
    """Fonction de création de l'applicationlication Flask"""
    application = Flask(__name__)
    
    # ============================================
    # CONFIGURATION DE L'applicationLICATION
    # ============================================
    
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    application.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///gitfetch.db')
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    application.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    application.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    application.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    application.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@gitfetch.com')
    
    application.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    application.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
    application.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    application.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # ============================================
    # INITIALISATION DES EXTENSIONS
    # ============================================
    
    db.init_application(application)
    
    mail = Mail()
    mail.init_application(application)
    
    login_manager = LoginManager()
    login_manager.init_application(application)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))
    
    oauth = OAuth(application)
    
    oauth.register(
        name='github',
        client_id=application.config['GITHUB_CLIENT_ID'],
        client_secret=application.config['GITHUB_CLIENT_SECRET'],
        access_token_url='https://github.com',
        authorize_url='https://github.com',
        api_base_url='https://api.github.com',
        client_kwargs={'scope': 'user:email'},
    )
    
    oauth.register(
        name='google',
        client_id=application.config['GOOGLE_CLIENT_ID'],
        client_secret=application.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    application.extensions['mail'] = mail
    application.extensions['oauth'] = oauth
    application.extensions['login_manager'] = login_manager
    
    # ============================================
    # CRÉATION DES TABLES & DOSSIERS
    # ============================================
    
    with application.application_context():
        db.create_all()
    
    application.register_blueprint(auth_bp)
    application.register_blueprint(main_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(portfolio_bp)
    application.register_blueprint(github_bp)
    
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
# POINT D'ENTRÉE POUR GUNICORN ET LOCAL
# ============================================

# Indispensable pour Gunicorn : application doit être défini au niveau du module
application = create_application()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║   🚀 GitFetch - Serveur de Développement                 ║")
    print(f"║   📍 Accès : http://{host}:{port}                         ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    application.run(host=host, port=port, debug=debug)
