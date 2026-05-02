import os
import sys
import requests
import secrets
import uuid
from datetime import datetime
from flask import Flask, Blueprint, render_template, request, url_for, flash, redirect, current_app, send_from_directory, abort, session
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from sqlalchemy import inspect, text
import time
import logging

# ============================================
# CONFIGURATION INITIALE
# ============================================

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# BASE DE DONNÉES ET MODÈLES
# ============================================

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateurs'
    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hache = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), default='user')
    jeton_github = db.Column(db.String(255), nullable=True)
    jeton_identification = db.Column(db.String(255), nullable=True)
    photo_profil = db.Column(db.String(255), nullable=True, default='default-avatar.jpg')
    photo_couverture = db.Column(db.String(255), nullable=True, default='default-cover.jpg')
    cv = db.Column(db.String(255))
    biographie = db.Column(db.Text, nullable=True)
    poste = db.Column(db.String(100), nullable=True)
    localisation = db.Column(db.String(100), nullable=True)
    site_web = db.Column(db.String(255), nullable=True)
    twitter = db.Column(db.String(100), nullable=True)
    linkedin = db.Column(db.String(100), nullable=True)
    github = db.Column(db.String(100), nullable=True)
    github_access_token = db.Column(db.String(255), nullable=True)
    telephone_principal = db.Column(db.String(20), nullable=True)
    telephone_mobile = db.Column(db.String(20), nullable=True)
    theme_prefere = db.Column(db.String(20), default='light')
    est_confirme = db.Column(db.Boolean, default=False)
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Projet(db.Model):
    __tablename__ = 'projets'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    github_url = db.Column(db.String(255))
    demo_url = db.Column(db.String(255))
    image_couverture = db.Column(db.String(255))
    logo_projet = db.Column(db.String(255))
    repo_id_github = db.Column(db.String(100), unique=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    est_collaboration = db.Column(db.Boolean, default=False)
    structure_nom = db.Column(db.String(100))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    technologies_annexes = db.Column(db.JSON, default=list)

class PortfolioConfig(db.Model):
    __tablename__ = 'portfolio_config'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    hero_titre = db.Column(db.String(200), default="CONSTRUIRE LE FUTUR DU CODE")
    hero_description = db.Column(db.Text, default="")
    about_titre = db.Column(db.String(200), default="Spécialiste IT multi-domaines")
    about_soustitre = db.Column(db.String(200), default="Précision. Performance. Innovation.")
    about_description = db.Column(db.Text)
    about_lien_texte = db.Column(db.String(100), default="EN SAVOIR PLUS SUR MON PARCOURS")
    about_skills_json = db.Column(db.JSON, default=list)
    tech_stack_json = db.Column(db.JSON, default=list)
    projects_titre = db.Column(db.String(200), default="PROJETS RÉCENTS")
    cta_titre = db.Column(db.String(200), default="PRÊT À LANCER VOTRE PROCHAIN PROJET")

class AboutPage(db.Model):
    __tablename__ = 'about_pages'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, nullable=False, index=True)
    hero_titre = db.Column(db.String(255), default="PLUS QU'UN DÉVELOPPEUR")
    hero_texte = db.Column(db.Text, default="Une passion pour l'innovation...")
    hero_image = db.Column(db.String(500), nullable=True)
    hero_bouton_1_texte = db.Column(db.String(100), default="Mon parcours")
    hero_bouton_1_lien = db.Column(db.String(255), default="#formation")
    hero_bouton_2_texte = db.Column(db.String(100), default="Échanger ensemble")
    hero_bouton_2_lien = db.Column(db.String(255), default="#contact")
    philosophie_titre = db.Column(db.String(255), default="MA PHILOSOPHIE")
    philosophie_sous_titre = db.Column(db.String(255), default="L'humain au centre de la technologie")
    philosophie_description_1 = db.Column(db.Text, default="...")
    philosophie_description_2 = db.Column(db.Text, default="...")
    philosophie_image = db.Column(db.String(500), nullable=True)
    parcours_image = db.Column(db.String(500), nullable=True)
    competences_titre = db.Column(db.String(255), default="COMPÉTENCES CLÉS")
    competences_sous_titre = db.Column(db.String(255), default="...")
    competences_image = db.Column(db.String(500), nullable=True)
    certifications_titre = db.Column(db.String(255), default="CERTIFICATIONS RECONNUES")
    certifications_sous_titre = db.Column(db.String(255), default="...")
    certifications_image = db.Column(db.String(500), nullable=True)
    values_json = db.Column(db.JSON, default=list)
    parcours_json = db.Column(db.JSON, default=list)
    competences_json = db.Column(db.JSON, default=list)
    certifications_json = db.Column(db.JSON, default=list)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def generer_jeton(email, salt):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt=salt)

def verifier_jeton(token, salt, expiration=3600):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serialiseur.loads(token, salt=salt, max_age=expiration)
    except:
        return None

def get_media_path(subdir=''):
    project_root = current_app.root_path
    media_path = os.path.join(project_root, 'media')
    if subdir:
        media_path = os.path.join(media_path, subdir)
    if not os.path.exists(media_path):
        os.makedirs(media_path, exist_ok=True)
    return media_path

def save_media_file(file, type_file, user_id):
    subdirs = {'avatar': 'profiles', 'cover': 'covers', 'cv': 'docs', 'proj': 'projects', 'about': 'about'}
    subdir = subdirs.get(type_file)
    if not subdir:
        return None
    media_dir = get_media_path(subdir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_ext = os.path.splitext(file.filename)[1] if '.' in file.filename else ''
    filename = f"{type_file}_{user_id}_{timestamp}{original_ext}"
    filename = secure_filename(filename)
    full_path = os.path.join(media_dir, filename)
    file.save(full_path)
    return filename

def delete_media_file(filename, type_file):
    subdirs = {'avatar': 'profiles', 'cover': 'covers', 'cv': 'docs', 'proj': 'projects', 'about': 'about'}
    subdir = subdirs.get(type_file)
    if not subdir or not filename:
        return False
    try:
        file_path = os.path.join(get_media_path(subdir), filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Erreur suppression: {e}")
    return False

def download_and_save_avatar(url, user_id, type_file='avatar'):
    try:
        response = requests.get(url, timeout=10, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            ext = '.jpg'
            if 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            folder = 'profiles' if type_file == 'avatar' else 'covers'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{type_file}_{user_id}_{timestamp}_{unique_id}{ext}"
            filename = secure_filename(filename)
            media_dir = get_media_path(folder)
            file_path = os.path.join(media_dir, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return filename
        return None
    except Exception as e:
        logger.error(f"Erreur téléchargement avatar: {e}")
        return None

def fetch_github_repos(token, max_retries=3):
    if not token:
        return [], "Token GitHub non configuré"
    headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
    all_repos = []
    page = 1
    url = 'https://api.github.com/user/repos?sort=updated&per_page=100&affiliation=owner,collaborator,organization_member&visibility=all'
    for attempt in range(max_retries):
        try:
            while True:
                paginated_url = f'{url}&page={page}'
                response = requests.get(paginated_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    repos = response.json()
                    if not repos:
                        break
                    all_repos.extend(repos)
                    if 'Link' in response.headers and 'rel="next"' in response.headers['Link']:
                        page += 1
                        continue
                    break
                elif response.status_code == 401:
                    return [], "Token GitHub invalide"
                elif response.status_code == 403:
                    return [], "Limite de taux GitHub atteinte"
                else:
                    return [], f"Erreur GitHub: {response.status_code}"
            break
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return [], "Impossible de se connecter à GitHub"
        except Exception as e:
            return [], f"Erreur: {str(e)}"
    unique_repos = {repo['id']: repo for repo in all_repos}
    return list(unique_repos.values()), None

def ensure_token_column_exists():
    try:
        inspector = inspect(db.engine)
        if inspector.has_table('utilisateurs'):
            columns = [col['name'] for col in inspector.get_columns('utilisateurs')]
            if 'jeton_identification' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE utilisateurs ADD COLUMN jeton_identification VARCHAR(255)'))
                    conn.commit()
        return True
    except Exception as e:
        print(f"Erreur création colonne: {e}")
        return False

# ============================================
# CRÉATION DE L'APPLICATION FLASK
# ============================================

def create_application():
    application = Flask(__name__, static_folder='../static', template_folder='../templates')

    # Base de données
    database_url = os.getenv("POSTGRES_URL")
    if not database_url:
        raise ValueError("❌ POSTGRES_URL non définie")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    application.config['SQLALCHEMY_DATABASE_URI'] = database_url
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email
    application.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    application.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    application.config['MAIL_USE_TLS'] = True
    application.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    application.config['MAIL_PASSWORD'] = os.getenv('MESSAGERIE_MOT_DE_PASSE')
    application.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # Sécurité
    application.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not application.config['SECRET_KEY']:
        raise ValueError("❌ SECRET_KEY non définie")

    # OAuth
    application.config['GITHUB_CLIENT_ID'] = os.getenv('ID_CLIENT_GITHUB')
    application.config['GITHUB_CLIENT_SECRET'] = os.getenv('SECRET_DU_CLIENT_GITHUB')
    application.config['GOOGLE_CLIENT_ID'] = os.getenv('ID_CLIENT_GOOGLE')
    application.config['GOOGLE_CLIENT_SECRET'] = os.getenv('SECRET_DU_CLIENT_GOOGLE')

    # Initialisation extensions
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
    oauth.register(
        name='github',
        client_id=application.config['GITHUB_CLIENT_ID'],
        client_secret=application.config['GITHUB_CLIENT_SECRET'],
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com',
        client_kwargs={'scope': 'user:email repo'},
    )
    oauth.register(
        name='google',
        client_id=application.config['GOOGLE_CLIENT_ID'],
        client_secret=application.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    return application

# ============================================
# BLUEPRINTS (simplifiés pour test)
# ============================================

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
portfolio_bp = Blueprint('portfolio', __name__)
github_bp = Blueprint('github_bp', __name__, url_prefix='/github')

@main_bp.route("/")
def index():
    return "Bienvenue sur GitFetch - L'application fonctionne!"

@auth_bp.route("/login")
def login():
    return "Page de connexion"

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    return "Dashboard admin"

@portfolio_bp.route("/portfolio")
def portfolio():
    return "Portfolio"

@github_bp.route("/callback")
def callback():
    return "GitHub callback"

# ============================================
# LANCEMENT
# ============================================

app = create_application()

# Enregistrement des blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(github_bp)

if __name__ == "__main__":
    app.run(debug=True)