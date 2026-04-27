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
    # Configuration Flask pour Vercel (dossiers parents)
    application = Flask(__name__,
                        static_folder='../static',
                        template_folder='../templates')

    # ============================================
    # CONFIGURATION BASE DE DONNÉES - POSTGRESQL
    # ============================================
    
    database_url = "gitfetch_POSTGRES_URL_NON_POOLING=postgresql://neondb_owner:npg_YsNDXI2KxL8m@ep-solitary-sky-am37b693.c-5.us-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"
    
    # # Si aucune URL n'est trouvée (local), utilise ta config locale
    # if not database_url:
    #     database_url = "postgresql://postgres:root@localhost:5432/GitFetch"
    
    application.config['SQLALCHEMY_DATABASE_URI'] = database_url
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ============================================
    # CONFIG MAIL
    # ============================================
    application.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    application.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    application.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    application.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # ============================================
    # CONFIG SÉCURITÉ / OAUTH
    # ============================================
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key-for-dev')
    application.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
    application.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
    application.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    application.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # ============================================
    # INIT EXTENSIONS
    # ============================================
    db.init_app(application)
    Migrate(application, db)
    Mail(application)

    login_manager = LoginManager()
    login_manager.init_app(application)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Utilisateur, int(user_id))

    oauth = OAuth(application)

    # OAUTH GITHUB
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

    # OAUTH GOOGLE
    if application.config['GOOGLE_CLIENT_ID']:
        oauth.register(
            name='google',
            client_id=application.config['GOOGLE_CLIENT_ID'],
            client_secret=application.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    # ============================================
    # BLUEPRINTS
    # ============================================
    application.register_blueprint(auth_bp)
    application.register_blueprint(main_bp)
    application.register_blueprint(admin_bp)
    application.register_blueprint(portfolio_bp)
    application.register_blueprint(github_bp)

    return application

# L'instance nommée 'app' pour Vercel
app = create_application()

if __name__ == "__main__":
    app.run(debug=True)