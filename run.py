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
    
    # Clé secrète pour les sessions
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Configuration de la base de données
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///gitfetch.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuration des emails
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@gitfetch.com')
    
    # Configuration OAuth
    app.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    app.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # ============================================
    # INITIALISATION DES EXTENSIONS
    # ============================================
    
    # Initialisation de la base de données
    db.init_app(app)
    
    # Initialisation de Flask-Mail
    mail = Mail()
    mail.init_app(app)
    
    # Initialisation de Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))
    
    # Initialisation de OAuth avec Authlib
    oauth = OAuth(app)
    
    # Enregistrement explicite des providers OAuth
    # Provider GitHub
    oauth.register(
        name='github',
        client_id=app.config['GITHUB_CLIENT_ID'],
        client_secret=app.config['GITHUB_CLIENT_SECRET'],
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )
    
    # Provider Google
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        access_token_url='https://oauth2.googleapis.com/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'openid email profile'},
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )
    
    # Stocker les extensions dans app.extensions pour y accéder dans les routes
    app.extensions['mail'] = mail
    app.extensions['oauth'] = oauth
    app.extensions['login_manager'] = login_manager
    
    # ============================================
    # CRÉATION DES TABLES
    # ============================================
    
    with app.app_context():
        db.create_all()
        print("✅ Tables de la base de données vérifiées/créées")
    
    # ============================================
    # ENREGISTREMENT DES BLUEPRINTS
    # ============================================
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(github_bp)
    
    print("✅ Blueprints enregistrés : auth, main, admin, portfolio, github")
    
    # ============================================
    # CRÉATION DES DOSSIERS MÉDIA
    # ============================================
    
    media_folders = [
        os.path.join(app.root_path, 'media', 'profiles'),
        os.path.join(app.root_path, 'media', 'covers'),
        os.path.join(app.root_path, 'media', 'docs'),
        os.path.join(app.root_path, 'media', 'projects'),
        os.path.join(app.root_path, 'media', 'about'),
        os.path.join(app.root_path, 'media', 'uploads'),
    ]
    
    for folder in media_folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"📁 Dossier créé : {folder}")
    
    print("🚀 Application Flask initialisée avec succès")
    
    return app

# ============================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================

if __name__ == "__main__":
    app = create_app()
    
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"
    host = os.getenv("HOST", "127.0.0.1")
    
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║                                                          ║")
    print(f"║   🚀 GitFetch - Application Monolithique                 ║")
    print(f"║                                                          ║")
    print(f"║   📍 Accès local : http://{host}:{port}                   ║")
    print(f"║   🔧 Mode debug : {'Activé' if debug else 'Désactivé'}                   ║")
    print(f"║                                                          ║")
    print(f"║   📋 Routes disponibles :                                ║")
    print(f"║   • Accueil : /                                          ║")
    print(f"║   • Auth : /auth/*                                       ║")
    print(f"║   • Admin : /admin/*                                     ║")
    print(f"║   • Portfolio : /portfolio/*                             ║")
    print(f"║   • GitHub OAuth : /github/*                             ║")
    print(f"║                                                          ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    app.run(host=host, port=port, debug=debug)