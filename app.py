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

# Charger .env
load_dotenv()

def create_application():
    application = Flask(__name__)

    # ============================================
    # CONFIGURATION BASE DE DONNÉES - SQLITE
    # ============================================
    
    # Utiliser SQLite (par défaut)
    database_url = "sqlite:///gitfetch.db"
    
    # Optionnel: Vous pouvez aussi garder la possibilité de passer à PostgreSQL plus tard
    # en commentant/décommentant cette ligne
    # if os.getenv("DATABASE_URL"):
    #     database_url = os.getenv("DATABASE_URL")
    
    application.config['SQLALCHEMY_DATABASE_URI'] = database_url
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print(f"✅ Base de données utilisée: SQLite (gitfetch.db)")

    # ============================================
    # CONFIG MAIL
    # ============================================

    application.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    application.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    application.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    application.config['MAIL_DEFAULT_SENDER'] = os.getenv(
        'MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME')
    )

    # ============================================
    # CONFIG SÉCURITÉ / OAUTH
    # ============================================

    application.config['SECRET_KEY'] = os.getenv(
        'SECRET_KEY', 'change-this-in-production'
    )

    application.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    application.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')

    application.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    application.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # ============================================
    # INIT EXTENSIONS
    # ============================================

    db.init_app(application)
    Migrate(application, db)

    mail = Mail(application)

    login_manager = LoginManager()
    login_manager.init_app(application)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Utilisateur, int(user_id))

    oauth = OAuth(application)

    # ============================================
    # OAUTH GITHUB
    # ============================================

    if application.config['GITHUB_CLIENT_ID']:
        oauth.register(
            name='github',
            client_id=application.config['GITHUB_CLIENT_ID'],
            client_secret=application.config['GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com',
            client_kwargs={'scope': 'user:email'},
        )
        print("✅ GitHub OAuth OK")

    # ============================================
    # OAUTH GOOGLE
    # ============================================

    if application.config['GOOGLE_CLIENT_ID']:
        oauth.register(
            name='google',
            client_id=application.config['GOOGLE_CLIENT_ID'],
            client_secret=application.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        print("✅ Google OAuth OK")

    # ============================================
    # BLUEPRINTS
    # ============================================

    application.register_blueprint(auth_bp)
    application.register_blueprint(main_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(portfolio_bp)
    application.register_blueprint(github_bp)

    # ============================================
    # DOSSIERS MEDIA
    # ============================================

    media_folders = [
        'profiles', 'covers', 'docs', 'projects', 'about', 'uploads'
    ]

    for folder in media_folders:
        path = os.path.join(application.root_path, 'media', folder)
        os.makedirs(path, exist_ok=True)

    return application


# ============================================
# ENTRYPOINT
# ============================================

application = create_application()
app = application

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True") == "True"

    print("🚀 GitFetch lancé avec SQLite")
    application.run(host="0.0.0.0", port=port, debug=debug)