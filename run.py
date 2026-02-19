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

def create_app():
    """Fonction de création de l'application Flask"""
    app = Flask(__name__)
    
    # ============================================
    # CONFIGURATION DE L'APPLICATION
    # ============================================
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///gitfetch.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@gitfetch.com')
    
    app.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    app.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # ============================================
    # INITIALISATION DES EXTENSIONS
    # ============================================
    
    db.init_app(app)
    
    mail = Mail()
    mail.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))
    
    oauth = OAuth(app)
    
    oauth.register(
        name='github',
        client_id=app.config['GITHUB_CLIENT_ID'],
        client_secret=app.config['GITHUB_CLIENT_SECRET'],
        access_token_url='https://github.com',
        authorize_url='https://github.com',
        api_base_url='https://api.github.com',
        client_kwargs={'scope': 'user:email'},
    )
    
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    app.extensions['mail'] = mail
    app.extensions['oauth'] = oauth
    app.extensions['login_manager'] = login_manager
    
    # ============================================
    # CRÉATION DES TABLES & DOSSIERS
    # ============================================
    
    with app.app_context():
        db.create_all()
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(github_bp)
    
    media_folders = [
        os.path.join(app.root_path, 'media', 'profiles'),
        os.path.join(app.root_path, 'media', 'covers'),
        os.path.join(app.root_path, 'media', 'docs'),
        os.path.join(app.root_path, 'media', 'projects'),
        os.path.join(app.root_path, 'media', 'about'),
        os.path.join(app.root_path, 'media', 'uploads'),
    ]
    
    for folder in media_folders:
        os.makedirs(folder, exist_ok=True)
    
    return app

# ============================================
# POINT D'ENTRÉE POUR GUNICORN ET LOCAL
# ============================================

# Indispensable pour Gunicorn : app doit être défini au niveau du module
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║   🚀 GitFetch - Serveur de Développement                 ║")
    print(f"║   📍 Accès : http://{host}:{port}                         ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    app.run(host=host, port=port, debug=debug)
