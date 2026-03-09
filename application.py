# application.py
import os
import sys
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from models import db, Utilisateur
from routes import auth_bp, main_bp, admin_bp, portfolio_bp, github_bp

# NE PAS charger .env sur PythonAnywhere (les variables sont dans l'interface Web)
# load_dotenv()

def create_application():
    application = Flask(__name__)
    
    # ============================================
    # CONFIGURATION NEON POSTGRESQL
    # ============================================
    
    # URI de connexion Neon (à définir dans les variables d'environnement PythonAnywhere)
    NEON_URI = os.environ.get('NEON_DATABASE_URL')
    
    if not NEON_URI:
        print("❌ ERREUR CRITIQUE: NEON_DATABASE_URL non définie dans les variables d'environnement")
        print("Allez dans l'onglet Web > Environment variables pour l'ajouter")
        # Valeur par défaut pour le développement (à NE PAS utiliser en production)
        NEON_URI = "postgresql://neondb_owner:npg_9hzCZXFQW1no@ep-damp-star-a8osm2xg-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"
    
    # Configuration PostgreSQL pour Neon
    application.config['SQLALCHEMY_DATABASE_URI'] = NEON_URI
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configuration spécifique pour Neon (SSL requis)
    application.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 300,  # Recycle les connexions toutes les 5 minutes
        'pool_pre_ping': True,  # Vérifie la connexion avant utilisation
        'max_overflow': 10,  # Connexions supplémentaires si nécessaire
        'pool_timeout': 30,  # Timeout d'attente pour une connexion
    }
    
    # Afficher la configuration (sans le mot de passe complet)
    db_display = NEON_URI.replace(NEON_URI.split(':')[2].split('@')[0], '*****')
    print(f"✅ Connexion à Neon PostgreSQL: {db_display}")
    
    # ============================================
    # CONFIGURATION SECRET_KEY
    # ============================================
    
    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production-pythonanywhere-2025')
    
    # ============================================
    # CONFIGURATION DES EMAILS
    # ============================================
    
    application.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    application.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    application.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    application.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
    
    # ============================================
    # CONFIGURATION OAUTH
    # ============================================
    
    application.config['GITHUB_CLIENT_ID'] = os.environ.get('GITHUB_CLIENT_ID', '')
    application.config['GITHUB_CLIENT_SECRET'] = os.environ.get('GITHUB_CLIENT_SECRET', '')
    application.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    application.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
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
    
    # Sur PythonAnywhere, chemin absolu
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    media_folders = [
        os.path.join(base_dir, 'media', 'profiles'),
        os.path.join(base_dir, 'media', 'covers'),
        os.path.join(base_dir, 'media', 'docs'),
        os.path.join(base_dir, 'media', 'projects'),
        os.path.join(base_dir, 'media', 'about'),
        os.path.join(base_dir, 'media', 'uploads'),
    ]
    
    for folder in media_folders:
        os.makedirs(folder, exist_ok=True)
        print(f"📁 Dossier vérifié: {folder}")
    
    # ============================================
    # TEST DE CONNEXION À LA BASE DE DONNÉES
    # ============================================
    
    with application.app_context():
        try:
            # Test simple de connexion
            db.session.execute('SELECT 1')
            db.session.commit()
            print("✅ Connexion à Neon PostgreSQL établie avec succès!")
        except Exception as e:
            print(f"❌ Erreur de connexion à Neon: {e}")
            print("Vérifiez votre URI de connexion et les paramètres SSL")
    
    return application

# ============================================
# POINT D'ENTRÉE POUR PYTHONANYWHERE
# ============================================

application = create_application()

# Alias pour compatibilité
app = application

if __name__ == "__main__":
    # Ce bloc ne sera pas exécuté sur PythonAnywhere
    # Il est utile uniquement pour le développement local
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True") == "True"
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║   🚀 GitFetch - Serveur de Développement                 ║")
    print(f"║   📍 Accès : http://{host}:{port}                         ║")
    print(f"║   📦 Base de données: Neon PostgreSQL                     ║")
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    application.run(host=host, port=port, debug=debug)