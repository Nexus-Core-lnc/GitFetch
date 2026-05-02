import os
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from models import db, Utilisateur
from routes import auth_bp, main_bp, admin_bp, portfolio_bp, github_bp

# Charger .env.production (optionnel, Vercel utilise ses propres vars)
# load_dotenv('.env.production')  # Commenté car Vercel injecte directement

def create_application():
    # Configuration Flask pour Vercel (dossiers parents)
    application = Flask(__name__,
                        static_folder='../static',
                        template_folder='../templates')

    # ============================================
    # CONFIGURATION BASE DE DONNÉES - POSTGRESQL
    # ============================================
    
  # Vercel Postgres fournit POSTGRES_URL, pas DATABASE_URL
    database_url = os.getenv("POSTGRES_URL")
    
    # Vérification obligatoire - pas de fallback local
    if not database_url:
        raise ValueError("❌ DATABASE_URL non définie dans les variables d'environnement Vercel")
    
    # Correction pour SQLAlchemy 1.4+ / 2.0+ 
    # Vercel ou Heroku fournissent parfois 'postgres://', il faut 'postgresql://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    application.config['SQLALCHEMY_DATABASE_URI'] = database_url
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ============================================
    # CONFIGURATION MAIL (Sans fallback)
    # ============================================
    mail_server = os.getenv('MAIL_SERVER')
    mail_port = os.getenv('MAIL_PORT')
    mail_use_tls = os.getenv('MAIL_USE_TLS')
    mail_username = os.getenv('MAIL_USERNAME')
    mail_password = os.getenv('MESSAGERIE_MOT_DE_PASSE')  # Note: variable différente
    mail_default_sender = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Vérifications pour la messagerie
    if not all([mail_server, mail_port, mail_username, mail_password]):
        raise ValueError("❌ Configuration email incomplète dans Vercel. Vérifiez: MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MESSAGERIE_MOT_DE_PASSE")
    
    application.config['MAIL_SERVER'] = mail_server
    application.config['MAIL_PORT'] = int(mail_port)
    application.config['MAIL_USE_TLS'] = mail_use_tls == 'True' if mail_use_tls else True
    application.config['MAIL_USERNAME'] = mail_username
    application.config['MAIL_PASSWORD'] = mail_password
    application.config['MAIL_DEFAULT_SENDER'] = mail_default_sender

    # ============================================
    # CONFIGURATION SÉCURITÉ / OAUTH (Sans fallback)
    # ============================================
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        raise ValueError("❌ SECRET_KEY non définie dans Vercel")
    application.config['SECRET_KEY'] = secret_key
    
    # GitHub OAuth
    github_client_id = os.getenv('ID_CLIENT_GITHUB')
    github_client_secret = os.getenv('SECRET_DU_CLIENT_GITHUB')
    
    if not github_client_id or not github_client_secret:
        raise ValueError("❌ Configuration GitHub OAuth incomplète. Vérifiez: ID_CLIENT_GITHUB, SECRET_DU_CLIENT_GITHUB")
    
    application.config['GITHUB_CLIENT_ID'] = github_client_id
    application.config['GITHUB_CLIENT_SECRET'] = github_client_secret
    
    # Google OAuth
    google_client_id = os.getenv('ID_CLIENT_GOOGLE')
    google_client_secret = os.getenv('SECRET_DU_CLIENT_GOOGLE')
    
    if not google_client_id or not google_client_secret:
        raise ValueError("❌ Configuration Google OAuth incomplète. Vérifiez: ID_CLIENT_GOOGLE, SECRET_DU_CLIENT_GOOGLE")
    
    application.config['GOOGLE_CLIENT_ID'] = google_client_id
    application.config['GOOGLE_CLIENT_SECRET'] = google_client_secret

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