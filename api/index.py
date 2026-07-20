import os
import sys
import requests
import secrets
import uuid
from datetime import datetime
from flask import Flask, render_template, request, url_for, flash, redirect, current_app, send_from_directory, abort, session, Blueprint
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.pool import NullPool
import time
import logging

# Charger .env (optionnel)
load_dotenv()

# ============================================
# MODÈLES (contenu de models.py)
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
    
    # Jeton unique pour l'identification
    jeton_identification = db.Column(db.String(255), nullable=True)
    
    # Photos de profil et couverture
    photo_profil = db.Column(db.String(255), nullable=True, default='default-avatar.jpg')
    photo_couverture = db.Column(db.String(255), nullable=True, default='default-cover.jpg')
    
    # CV
    cv = db.Column(db.String(255)) 
    
    # Informations personnelles
    biographie = db.Column(db.Text, nullable=True)
    poste = db.Column(db.String(100), nullable=True)
    localisation = db.Column(db.String(100), nullable=True)
    site_web = db.Column(db.String(255), nullable=True)
    
    # Réseaux sociaux
    twitter = db.Column(db.String(100), nullable=True)
    linkedin = db.Column(db.String(100), nullable=True)
    github = db.Column(db.String(100), nullable=True)
    github_access_token = db.Column(db.String(255), nullable=True)
    
    # Numéros de téléphone
    telephone_principal = db.Column(db.String(20), nullable=True)
    telephone_mobile = db.Column(db.String(20), nullable=True)
    
    # Préférences
    theme_prefere = db.Column(db.String(20), default='light') 
    
    # Statut
    est_confirme = db.Column(db.Boolean, default=False)
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projets = db.relationship('Projet', backref='proprietaire', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Utilisateur {self.email}>'

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
    
    def __repr__(self):
        return f'<Projet {self.nom}>'
    
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
# CONFIGURATIONS ET FONCTIONS UTILITAIRES
# ============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Récupération des variables d'environnement
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

# Création des blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
portfolio_bp = Blueprint('portfolio', __name__)
github_bp = Blueprint('github_bp', __name__, url_prefix='/github')

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def is_vercel():
    """Détecte si on tourne sur Vercel (environnement serverless)."""
    return bool(os.getenv('VERCEL') or os.getenv('VERCEL_ENV'))


def get_media_base():
    """
    Retourne le répertoire racine des médias.
    Sur Vercel : /tmp/media (seul répertoire writable en serverless).
    En local  : <project_root>/media
    NOTE: Sur Vercel, /tmp est éphémère — pour la prod,
    migrer vers Cloudinary/S3 via la variable MEDIA_BASE_DIR.
    """
    override = os.getenv('MEDIA_BASE_DIR')
    if override:
        return override
    if is_vercel():
        return '/tmp/media'
    return os.path.join(current_app.root_path, 'media')


def get_media_path(subdir=''):
    """Retourne le chemin absolu d'un sous-dossier média et le crée si besoin."""
    base = get_media_base()
    path = os.path.join(base, subdir) if subdir else base
    os.makedirs(path, exist_ok=True)
    return path


def get_upload_path(subdir=''):
    upload_path = get_media_path('uploads')
    if subdir:
        upload_path = os.path.join(upload_path, subdir)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def get_static_path():
    return os.path.join(current_app.root_path, 'static')


# Mapping type → sous-dossier (utilisé dans save/delete/serve)
MEDIA_SUBDIRS = {
    'avatar': 'profiles',
    'cover':  'covers',
    'cv':     'docs',
    'proj':   'projects',
    'about':  'about',
    'upload': 'uploads',
}


def save_media_file(file, type_file, user_id):
    """Sauvegarde un fichier média et retourne son nom de fichier."""
    subdir = MEDIA_SUBDIRS.get(type_file)
    if not subdir:
        logger.error(f"Type de média inconnu : {type_file}")
        return None
    if not file or not getattr(file, 'filename', None):
        return None
    media_dir = get_media_path(subdir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_ext = os.path.splitext(file.filename)[1] if '.' in file.filename else ''
    filename = secure_filename(f"{type_file}_{user_id}_{timestamp}{original_ext}")
    try:
        file.save(os.path.join(media_dir, filename))
        return filename
    except Exception as e:
        logger.error(f"Erreur sauvegarde fichier {filename}: {e}")
        return None


def delete_media_file(filename, type_file):
    """Supprime un fichier média. Retourne True si supprimé."""
    subdir = MEDIA_SUBDIRS.get(type_file)
    if not subdir or not filename:
        return False
    try:
        file_path = os.path.join(get_media_path(subdir), filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Erreur suppression {filename}: {e}")
    return False


def download_and_save_avatar(url, user_id, type_file='avatar'):
    """Télécharge un avatar depuis une URL et le sauvegarde localement."""
    try:
        logger.info(f"Téléchargement de l'avatar depuis: {url}")
        response = requests.get(url, timeout=10, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            ext = '.jpg'
            if 'png' in content_type: ext = '.png'
            elif 'gif' in content_type: ext = '.gif'
            elif 'webp' in content_type: ext = '.webp'
            subdir = MEDIA_SUBDIRS.get(type_file, 'profiles')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            filename = secure_filename(f"{type_file}_{user_id}_{timestamp}_{unique_id}{ext}")
            media_dir = get_media_path(subdir)
            file_path = os.path.join(media_dir, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Avatar sauvegardé: {filename}")
            return filename
        else:
            logger.error(f"Erreur téléchargement avatar: status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erreur téléchargement avatar: {str(e)}")
        return None


def generer_jeton(email, salt):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt=salt)


def verifier_jeton(token, salt, expiration=3600):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serialiseur.loads(token, salt=salt, max_age=expiration)
    except Exception:
        return None


def envoyer_email(destinataire, sujet, template, **kwargs):
    msg = Message(sujet, recipients=[destinataire],
                  sender=current_app.config.get('MAIL_DEFAULT_SENDER'))
    msg.html = render_template(f'auth/{template}', **kwargs)
    mail = current_app.extensions.get('mail')
    if mail:
        try:
            mail.send(msg)
        except Exception as e:
            logger.error(f"ERREUR envoi email: {e}")
    else:
        logger.error("ERREUR: Mail non configuré")


def get_common_context():
    try:
        # Récupère le premier utilisateur confirmé (par exemple le plus ancien)
        user = db.session.execute(
            db.select(Utilisateur)
            .filter(Utilisateur.est_confirme == True)
            .order_by(Utilisateur.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        return {'user': user}
    except Exception as e:
        logger.error(f"Erreur get_common_context (DB): {e}")
        db.session.rollback()
        return {'user': None}


def ensure_token_column_exists():
    """S'assure que la colonne jeton_identification existe dans la table utilisateurs."""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table('utilisateurs'):
            return False
        columns = [col['name'] for col in inspector.get_columns('utilisateurs')]
        if 'jeton_identification' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text(
                    'ALTER TABLE utilisateurs ADD COLUMN jeton_identification VARCHAR(255)'
                ))
                conn.commit()
            logger.info("Colonne jeton_identification ajoutée.")
        return True
    except Exception as e:
        logger.error(f"Erreur ensure_token_column_exists: {e}")
        return False


def fetch_github_repos(token, max_retries=3):
    if not token:
        return [], "Token GitHub non configuré"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    try:
        user_response = requests.get(
            'https://api.github.com/user', headers=headers, timeout=5
        )
        scopes = user_response.headers.get('X-OAuth-Scopes', '')
        logger.info(f"Scopes du token GitHub: {scopes}")
        if 'repo' not in scopes:
            logger.warning("⚠️ Le token n'a pas le scope 'repo'!")
    except Exception as e:
        logger.error(f"Erreur vérification scopes: {e}")
    try:
        invites_response = requests.get(
            'https://api.github.com/user/repository_invitations',
            headers=headers, timeout=5
        )
        if invites_response.status_code == 200:
            pending_invites = invites_response.json()
            if pending_invites:
                logger.info(f"📨 {len(pending_invites)} invitations en attente trouvées")
    except Exception as e:
        logger.error(f"Erreur récupération invitations: {e}")
    all_repos = []
    page = 1
    url = ('https://api.github.com/user/repos'
           '?sort=updated&per_page=100'
           '&affiliation=owner,collaborator,organization_member&visibility=all')
    for attempt in range(max_retries):
        try:
            while True:
                response = requests.get(f'{url}&page={page}', headers=headers, timeout=10)
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
                    return [], "Token GitHub invalide ou expiré"
                elif response.status_code == 403:
                    reset_time = response.headers.get('X-RateLimit-Reset', 'inconnu')
                    return [], f"Limite de taux GitHub atteinte. (Reset: {reset_time})"
                else:
                    return [], f"Erreur GitHub (Code: {response.status_code})"
            break
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erreur connexion (tentative {attempt+1}): {e}")
            if attempt == max_retries - 1:
                return [], "Impossible de se connecter à GitHub."
            time.sleep(2)
        except requests.exceptions.Timeout:
            logger.error(f"Timeout (tentative {attempt+1})")
            if attempt == max_retries - 1:
                return [], "Délai d'attente dépassé."
        except Exception as e:
            return [], f"Erreur inattendue: {str(e)}"
    unique_repos = {repo['id']: repo for repo in all_repos}
    repos_list = list(unique_repos.values())
    public_count  = sum(1 for r in repos_list if not r.get('private', False))
    private_count = sum(1 for r in repos_list if r.get('private', False))
    logger.info(f"📊 Total: {len(repos_list)} dépôts (publics: {public_count}, privés: {private_count})")
    if not repos_list:
        return [], "Aucun dépôt trouvé."
    return repos_list, None


def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except Exception:
        return None

# ============================================
# BLUEPRINT AUTH
# ============================================

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if Utilisateur.query.filter_by(email=email).first():
            flash("Cette adresse email est déjà enregistrée.", "danger")
            return redirect(url_for('auth.login'))
        nouvel_utilisateur = Utilisateur(
            email=email,
            nom_utilisateur=email.split('@')[0],
            mot_de_passe_hache=generate_password_hash(password),
            est_confirme=False
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()
        token = generer_jeton(email, 'email-confirm-salt')
        lien = url_for('auth.confirmer_email', token=token, _external=True)
        envoyer_email(email, "Confirmez votre compte GitFetch",
                      'email_confirmation.html', confirm_url=lien)
        flash("Compte créé ! Vérifiez votre boîte mail pour confirmer.", "success")
        return redirect(url_for('auth.login'))
    return render_template("auth/register.html")


@auth_bp.route("/confirm/<token>")
def confirmer_email(token):
    email = verifier_jeton(token, 'email-confirm-salt')
    if not email:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('auth.register'))
    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()
    if not utilisateur.est_confirme:
        utilisateur.est_confirme = True
        db.session.commit()
        flash("Email validé ! Vous pouvez vous connecter.", "success")
    return redirect(url_for('auth.login'))


@auth_bp.route("/connexion", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        user = Utilisateur.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.mot_de_passe_hache, password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return redirect(url_for('auth.login'))
        if not user.est_confirme:
            flash('Veuillez confirmer votre email avant de vous connecter.', 'warning')
            return redirect(url_for('auth.login'))
        try:
            ensure_token_column_exists()
            nouveau_token = secrets.token_urlsafe(32)
            user.jeton_identification = nouveau_token
            user.derniere_connexion   = datetime.utcnow()
            db.session.commit()
            session['jeton_identification'] = nouveau_token
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Erreur mise à jour token: {e}")
        login_user(user, remember=remember)
        return redirect(url_for('admin.dashboard'))
    return render_template("auth/login.html")


@auth_bp.route("/deconnexion")
@login_required
def logout():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    session.pop('jeton_identification', None)
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('main.index'))


@auth_bp.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        if user:
            token = generer_jeton(email, 'recover-password-salt')
            recover_url = url_for('auth.reset_password', token=token, _external=True)
            envoyer_email(email, "Réinitialisation de mot de passe",
                          'email_reset.html', recover_url=recover_url)
        flash("Si cet email existe, un lien a été envoyé.", "info")
        return redirect(url_for('auth.login'))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    email = verifier_jeton(token, 'recover-password-salt', expiration=1800)
    if not email:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        new_password = request.form.get('newPassword')
        user = Utilisateur.query.filter_by(email=email).first_or_404()
        user.mot_de_passe_hache = generate_password_hash(new_password)
        db.session.commit()
        flash("Mot de passe mis à jour !", "success")
        return redirect(url_for('auth.login'))
    return render_template("auth/reset_password.html", token=token)


@auth_bp.route('/debug-token')
@login_required
def debug_token():
    return {
        'user_id': current_user.id,
        'email': current_user.email,
        'jeton_identification': getattr(current_user, 'jeton_identification', 'Champ non existant'),
        'jeton_github': current_user.jeton_github,
        'session_token': session.get('jeton_identification'),
        'photo_profil': current_user.photo_profil,
        'photo_couverture': current_user.photo_couverture
    }


@auth_bp.route('/login/<name>')
def social_login(name):
    if name == 'github':
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            flash("Erreur de configuration GitHub.", "danger")
            return redirect(url_for('auth.login'))
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        redirect_uri = url_for('auth.auth_callback', name='github', _external=True)
        params = {
            'client_id':    GITHUB_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope':        'user:email repo',
            'state':        state,
            'response_type':'code',
            'allow_signup': 'true'
        }
        return redirect(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")
    elif name == 'google':
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            flash("Erreur de configuration Google.", "danger")
            return redirect(url_for('auth.login'))
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash("Impossible de contacter Google.", "danger")
            return redirect(url_for('auth.login'))
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        redirect_uri = url_for('auth.auth_callback', name='google', _external=True)
        params = {
            'client_id':     GOOGLE_CLIENT_ID,
            'redirect_uri':  redirect_uri,
            'response_type': 'code',
            'scope':         'openid email profile',
            'state':         state,
            'access_type':   'offline',
            'prompt':        'consent'
        }
        return redirect(f"{authorization_endpoint}?{urlencode(params)}")
    else:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))


@auth_bp.route('/auth/<name>')
def auth_callback(name):
    if name == 'github':
        state        = request.args.get('state')
        code         = request.args.get('code')
        error        = request.args.get('error')
        stored_state = session.pop('oauth_state', None)
        if error:
            flash(f"Erreur GitHub: {error}", "danger")
            return redirect(url_for('auth.login'))
        if not state or state != stored_state:
            flash("Erreur de sécurité OAuth (state invalide).", "danger")
            return redirect(url_for('auth.login'))
        if not code:
            flash("Code d'autorisation manquant.", "danger")
            return redirect(url_for('auth.login'))
        try:
            token_response = requests.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id":     GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code":          code,
                    "redirect_uri":  url_for('auth.auth_callback', name='github', _external=True)
                },
                timeout=10
            )
            token_json = token_response.json()
            if "access_token" not in token_json:
                error_desc = token_json.get('error_description', 'Erreur inconnue')
                flash(f"Impossible de récupérer le token GitHub: {error_desc}", "danger")
                return redirect(url_for('auth.login'))
            access_token = token_json["access_token"]
            user_response = requests.get(
                GITHUB_USER_URL,
                headers={"Authorization": f"token {access_token}", "Accept": "application/json"},
                timeout=10
            )
            if user_response.status_code != 200:
                flash("Impossible de récupérer les informations utilisateur GitHub.", "danger")
                return redirect(url_for('auth.login'))
            user_info = user_response.json()
            email = user_info.get('email')
            if not email:
                emails_response = requests.get(
                    'https://api.github.com/user/emails',
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    primary_email = next((e for e in emails if e.get('primary')), None)
                    email = primary_email.get('email') if primary_email else None
            if not email:
                flash("Impossible de récupérer votre email GitHub.", "danger")
                return redirect(url_for('auth.login'))
            pseudo     = user_info.get('login')
            avatar_url = user_info.get('avatar_url')
            user = Utilisateur.query.filter_by(email=email).first()
            is_new_user = user is None
            if is_new_user:
                user = Utilisateur(
                    email=email,
                    nom_utilisateur=pseudo,
                    est_confirme=True,
                    mot_de_passe_hache=None
                )
                db.session.add(user)
                db.session.flush()
            user.jeton_github = access_token
            if is_new_user or not user.photo_profil or user.photo_profil == 'default-avatar.jpg':
                if avatar_url:
                    local_avatar = download_and_save_avatar(avatar_url, user.id, 'avatar')
                    user.photo_profil = local_avatar if local_avatar else 'default-avatar.jpg'
                else:
                    user.photo_profil = 'default-avatar.jpg'
            try:
                ensure_token_column_exists()
                nouveau_token = secrets.token_urlsafe(32)
                user.jeton_identification = nouveau_token
                session['jeton_identification'] = nouveau_token
            except Exception as e:
                logger.warning(f"Erreur génération jeton: {e}")
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            flash(f"Bienvenue {user.nom_utilisateur} ! Connecté avec GitHub.", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur inattendue GitHub: {e}")
            flash(f"Erreur inattendue: {str(e)}", "danger")
            return redirect(url_for('auth.login'))

    elif name == 'google':
        state        = request.args.get('state')
        code         = request.args.get('code')
        error        = request.args.get('error')
        stored_state = session.pop('oauth_state', None)
        if error:
            flash(f"Erreur Google: {error}", "danger")
            return redirect(url_for('auth.login'))
        if not state or state != stored_state:
            flash("Erreur de sécurité OAuth (state invalide).", "danger")
            return redirect(url_for('auth.login'))
        if not code:
            flash("Code d'autorisation manquant.", "danger")
            return redirect(url_for('auth.login'))
        if session.get('oauth_code_used') == code:
            flash("Code d'authentification déjà utilisé.", "warning")
            return redirect(url_for('auth.login'))
        session['oauth_code_used'] = code
        try:
            google_provider_cfg = get_google_provider_cfg()
            if not google_provider_cfg:
                flash("Impossible de contacter Google.", "danger")
                session.pop('oauth_code_used', None)
                return redirect(url_for('auth.login'))
            token_endpoint = google_provider_cfg["token_endpoint"]
            token_response = requests.post(
                token_endpoint,
                data={
                    "client_id":     GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code":          code,
                    "grant_type":    "authorization_code",
                    "redirect_uri":  url_for('auth.auth_callback', name='google', _external=True)
                },
                timeout=10
            )
            token_json = token_response.json()
            if "access_token" not in token_json:
                error_desc = token_json.get('error_description', 'Erreur inconnue')
                flash(f"Erreur lors de l'authentification: {error_desc}", "danger")
                session.pop('oauth_code_used', None)
                return redirect(url_for('auth.login'))
            userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
            user_response = requests.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {token_json['access_token']}"},
                timeout=10
            )
            if user_response.status_code != 200:
                flash("Impossible de récupérer les informations utilisateur Google.", "danger")
                session.pop('oauth_code_used', None)
                return redirect(url_for('auth.login'))
            user_info  = user_response.json()
            email      = user_info.get('email')
            pseudo     = user_info.get('name', email.split('@')[0] if email else 'user')
            avatar_url = user_info.get('picture')
            if not email:
                flash("Impossible de récupérer votre email Google.", "danger")
                session.pop('oauth_code_used', None)
                return redirect(url_for('auth.login'))
            user = Utilisateur.query.filter_by(email=email).first()
            is_new_user = user is None
            if is_new_user:
                user = Utilisateur(
                    email=email,
                    nom_utilisateur=pseudo,
                    est_confirme=True,
                    mot_de_passe_hache=None
                )
                db.session.add(user)
                db.session.flush()
            if is_new_user or not user.photo_profil or user.photo_profil == 'default-avatar.jpg':
                if avatar_url:
                    local_avatar = download_and_save_avatar(avatar_url, user.id, 'avatar')
                    user.photo_profil = local_avatar if local_avatar else 'default-avatar.jpg'
                else:
                    user.photo_profil = 'default-avatar.jpg'
            try:
                ensure_token_column_exists()
                nouveau_token = secrets.token_urlsafe(32)
                user.jeton_identification = nouveau_token
                session['jeton_identification'] = nouveau_token
            except Exception as e:
                logger.warning(f"Erreur génération jeton: {e}")
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            session.pop('oauth_code_used', None)
            login_user(user, remember=True)
            flash(f"Bienvenue {user.nom_utilisateur} ! Connecté avec Google.", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            session.pop('oauth_code_used', None)
            logger.error(f"Erreur inattendue Google: {e}")
            flash(f"Erreur inattendue: {str(e)}", "danger")
            return redirect(url_for('auth.login'))
    else:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))

# ============================================
# BLUEPRINT MAIN
# ============================================

@main_bp.route("/")
def index():
    return render_template('index.html')

# ============================================
# BLUEPRINT ADMIN
# ============================================

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    repos = []
    error_message = None
    if current_user.jeton_github:
        repos, error_message = fetch_github_repos(current_user.jeton_github)
        if error_message:
            flash(error_message, "warning" if "Token" in error_message else "danger")
    else:
        flash("Token GitHub non configuré. Connectez votre compte GitHub pour importer des dépôts.", "info")
    return render_template('admin/dashboard.html', repos=repos)


@admin_bp.route('/import-view')
@login_required
def import_view():
    if not current_user.jeton_github:
        flash("Veuillez connecter votre compte GitHub dans votre profil.", "warning")
        return redirect(url_for('admin.edit_profile'))
    repos, error_message = fetch_github_repos(current_user.jeton_github)
    if error_message:
        flash(error_message, "danger")
        return render_template('admin/import_repos.html', repos=[])
    repos_dict = {}
    for r in repos:
        r['user_role'] = (
            "Propriétaire" if r['owner']['login'].lower() == current_user.nom_utilisateur.lower()
            else f"Invité par {r['owner']['login']}"
        )
        repos_dict[r['id']] = r
    repos_list = sorted(repos_dict.values(), key=lambda x: x.get('updated_at', ''), reverse=True)
    flash(f"✅ {len(repos_list)} dépôts trouvés !", "success")
    return render_template('admin/import_repos.html', repos=repos_list)


@admin_bp.route('/list-repos')
@login_required
def list_repos():
    projets = Projet.query.filter_by(utilisateur_id=current_user.id).order_by(Projet.id.desc()).all()
    return render_template('admin/list_repos.html', projets=projets)


@admin_bp.route('/import-repo/<int:github_id>', methods=['POST'])
@login_required
def import_repo(github_id):
    repo_name = request.form.get('repo_name')
    repo_desc = request.form.get('repo_desc')
    repo_url  = request.form.get('repo_url')
    existant  = Projet.query.filter_by(
        repo_id_github=str(github_id), utilisateur_id=current_user.id
    ).first()
    if existant:
        flash(f"Le projet '{repo_name}' est déjà dans votre base de données.", "info")
        return redirect(url_for('admin.dashboard'))
    try:
        nouveau_projet = Projet(
            nom=repo_name,
            description=repo_desc or "Aucune description GitHub",
            github_url=repo_url,
            repo_id_github=str(github_id),
            utilisateur_id=current_user.id
        )
        db.session.add(nouveau_projet)
        db.session.commit()
        flash(f"Projet '{repo_name}' importé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'importation: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/edit-project/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()
    if request.method == 'POST':
        try:
            projet.nom         = request.form.get('nom', projet.nom)
            projet.description = request.form.get('description', projet.description)
            projet.demo_url    = request.form.get('demo_url', projet.demo_url)
            projet.structure_nom = request.form.get('structure_nom', projet.structure_nom)
            est_collab = request.form.get('est_collaboration')
            projet.est_collaboration = (est_collab == '1') if est_collab is not None else False
            technologies_str = request.form.get('technologies_annexes', '')
            projet.technologies_annexes = (
                [t.strip() for t in technologies_str.split(',') if t.strip()]
                if technologies_str.strip() else []
            )
            # Gestion image couverture
            if request.form.get('delete_image') == '1':
                if projet.image_couverture:
                    delete_media_file(projet.image_couverture, 'proj')
                    projet.image_couverture = None
                    flash('Image de couverture supprimée', 'info')
            image_file = request.files.get('image_file')
            if image_file and image_file.filename and image_file.filename.strip():
                ext = image_file.filename.rsplit('.', 1)[-1].lower() if '.' in image_file.filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    new_filename = save_media_file(image_file, 'proj', projet.id)
                    if new_filename:
                        if projet.image_couverture and projet.image_couverture != new_filename:
                            delete_media_file(projet.image_couverture, 'proj')
                        projet.image_couverture = new_filename
                        flash('Image de couverture mise à jour', 'success')
                else:
                    flash('Format non supporté pour la couverture.', 'warning')
            # Gestion logo
            if request.form.get('delete_logo') == '1':
                if projet.logo_projet:
                    delete_media_file(projet.logo_projet, 'proj')
                    projet.logo_projet = None
                    flash('Logo supprimé', 'info')
            logo_file = request.files.get('logo_file')
            if logo_file and logo_file.filename and logo_file.filename.strip():
                ext = logo_file.filename.rsplit('.', 1)[-1].lower() if '.' in logo_file.filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    new_logo = save_media_file(logo_file, 'proj', projet.id)
                    if new_logo:
                        if projet.logo_projet and projet.logo_projet != new_logo:
                            delete_media_file(projet.logo_projet, 'proj')
                        projet.logo_projet = new_logo
                        flash('Logo mis à jour', 'success')
                else:
                    flash('Format non supporté pour le logo.', 'warning')
            projet.date_mise_a_jour = datetime.utcnow()
            db.session.commit()
            flash("Informations mises à jour avec succès !", "success")
            return redirect(url_for('admin.list_repos'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur edit_project: {e}")
            flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")
            return redirect(url_for('admin.edit_project', id=id))
    technologies_texte = ""
    if projet.technologies_annexes:
        technologies_texte = (
            ", ".join(projet.technologies_annexes)
            if isinstance(projet.technologies_annexes, list)
            else projet.technologies_annexes
        )
    return render_template('admin/edit_project.html',
                           projet=projet,
                           technologies_texte=technologies_texte,
                           projet_phare=None)


@admin_bp.route('/delete-project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()
    if projet.image_couverture:
        delete_media_file(projet.image_couverture, 'proj')
    if projet.logo_projet:
        delete_media_file(projet.logo_projet, 'proj')
    try:
        db.session.delete(projet)
        db.session.commit()
        flash("Projet supprimé de la base de données.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}", "danger")
    return redirect(url_for('admin.list_repos'))


@admin_bp.route('/refresh-github', methods=['POST'])
@login_required
def refresh_repos():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            current_user.nom_utilisateur      = request.form.get('nom_utilisateur', current_user.nom_utilisateur)
            current_user.email                = request.form.get('email', current_user.email)
            current_user.poste                = request.form.get('poste', current_user.poste)
            current_user.localisation         = request.form.get('localisation', current_user.localisation)
            current_user.site_web             = request.form.get('site_web', current_user.site_web)
            current_user.biographie           = request.form.get('biographie', current_user.biographie)
            current_user.telephone_principal  = request.form.get('telephone_principal', current_user.telephone_principal)
            current_user.telephone_mobile     = request.form.get('telephone_mobile', current_user.telephone_mobile)
            current_user.github               = request.form.get('github', current_user.github)
            current_user.linkedin             = request.form.get('linkedin', current_user.linkedin)
            current_user.twitter              = request.form.get('twitter', current_user.twitter)
            new_token = request.form.get('jeton_github', '').strip()
            if new_token:
                current_user.jeton_github = new_token
                flash('Token GitHub mis à jour', 'info')
            current_user.theme_prefere = request.form.get('theme_prefere', current_user.theme_prefere)
            # Avatar
            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename:
                ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    new_avatar = save_media_file(avatar_file, 'avatar', current_user.id)
                    if new_avatar:
                        old = current_user.photo_profil
                        if old and old != 'default-avatar.jpg' and not old.startswith(('http://', 'https://')):
                            delete_media_file(old, 'avatar')
                        current_user.photo_profil = new_avatar
                        flash('Avatar mis à jour', 'success')
                else:
                    flash("Format de fichier non supporté pour l'avatar.", 'warning')
            # Couverture
            cover_file = request.files.get('cover')
            if cover_file and cover_file.filename:
                ext = cover_file.filename.rsplit('.', 1)[-1].lower() if '.' in cover_file.filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
                    new_cover = save_media_file(cover_file, 'cover', current_user.id)
                    if new_cover:
                        old = current_user.photo_couverture
                        if old and old != 'default-cover.jpg' and not old.startswith(('http://', 'https://')):
                            delete_media_file(old, 'cover')
                        current_user.photo_couverture = new_cover
                        flash('Photo de couverture mise à jour', 'success')
                else:
                    flash('Format non supporté pour la couverture.', 'warning')
            # CV
            cv_file = request.files.get('cv')
            if cv_file and cv_file.filename:
                ext = cv_file.filename.rsplit('.', 1)[-1].lower() if '.' in cv_file.filename else ''
                if ext in {'pdf', 'doc', 'docx'}:
                    cv_file.seek(0, os.SEEK_END)
                    file_size = cv_file.tell()
                    cv_file.seek(0)
                    if file_size > 5 * 1024 * 1024:
                        flash('Le fichier CV est trop volumineux (max 5 Mo).', 'warning')
                    else:
                        new_cv = save_media_file(cv_file, 'cv', current_user.id)
                        if new_cv:
                            if current_user.cv:
                                delete_media_file(current_user.cv, 'cv')
                            current_user.cv = new_cv
                            flash('CV mis à jour', 'success')
                else:
                    flash('Format non supporté pour le CV (PDF, DOC, DOCX).', 'warning')
            current_user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil : {str(e)}', 'danger')
        return redirect(url_for('admin.edit_profile'))
    return render_template('admin/edit_profile.html')


@admin_bp.route('/portfolio/edit', methods=['GET', 'POST'])
@login_required
def edit_portfolio_content():
    config = PortfolioConfig.query.filter_by(utilisateur_id=current_user.id).first()
    if not config:
        config = PortfolioConfig(utilisateur_id=current_user.id,
                                 about_skills_json=[], tech_stack_json=[])
        db.session.add(config)
        db.session.commit()
    if request.method == 'POST':
        try:
            config.hero_titre        = request.form.get('hero_titre', config.hero_titre)
            config.hero_description  = request.form.get('hero_description', '')
            config.about_titre       = request.form.get('about_titre', config.about_titre)
            config.about_soustitre   = request.form.get('about_soustitre', config.about_soustitre)
            config.about_description = request.form.get('about_description', config.about_description)
            config.about_lien_texte  = request.form.get('about_lien_texte', config.about_lien_texte)
            config.projects_titre    = request.form.get('projects_titre', config.projects_titre)
            config.cta_titre         = request.form.get('cta_titre', config.cta_titre)
            s_noms  = request.form.getlist('skill_item_nom[]')
            s_icons = request.form.getlist('skill_item_icon[]')
            config.about_skills_json = [
                {"nom": n.strip(), "icon": i or "fas fa-star"}
                for n, i in zip(s_noms, s_icons) if n and n.strip()
            ]
            t_noms     = request.form.getlist('tech_nom[]')
            t_percents = request.form.getlist('tech_pourcent[]')
            t_icons    = request.form.getlist('tech_icon[]')
            t_cats     = request.form.getlist('tech_cat[]')
            config.tech_stack_json = [
                {"nom": n.strip(), "pourcent": p or "0",
                 "icon": i or "fas fa-code", "cat": c or ""}
                for n, p, i, c in zip(t_noms, t_percents, t_icons, t_cats) if n and n.strip()
            ]
            db.session.commit()
            flash("Portfolio mis à jour avec succès !", "success")
            return redirect(url_for('admin.edit_portfolio_content'))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "danger")
    config.about_skills_json = config.about_skills_json or []
    config.tech_stack_json   = config.tech_stack_json or []
    return render_template('admin/edit_portfolio.html', config=config)


@admin_bp.route('/about/edit', methods=['GET', 'POST'])
@login_required
def about_edit():
    config = AboutPage.query.filter_by(utilisateur_id=current_user.id).first()
    if request.method == 'POST':
        if not config:
            config = AboutPage(utilisateur_id=current_user.id)
            db.session.add(config)
        try:
            # Gestion des fichiers image
            for field in ('hero_image', 'philosophie_image', 'parcours_image',
                          'competences_image', 'certifications_image'):
                # Suppression demandée
                if request.form.get(f'{field}_delete'):
                    old = getattr(config, field)
                    if old:
                        delete_media_file(old, 'about')
                        setattr(config, field, None)
                # Nouveau fichier
                file = request.files.get(field)
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        old = getattr(config, field)
                        if old:
                            delete_media_file(old, 'about')
                        setattr(config, field, new_filename)
            # Champs texte
            config.hero_titre             = request.form.get('hero_titre', config.hero_titre)
            config.hero_texte             = request.form.get('hero_texte', config.hero_texte)
            config.hero_bouton_1_texte    = request.form.get('hero_bouton_1_texte', config.hero_bouton_1_texte)
            config.hero_bouton_1_lien     = request.form.get('hero_bouton_1_lien', config.hero_bouton_1_lien)
            config.hero_bouton_2_texte    = request.form.get('hero_bouton_2_texte', config.hero_bouton_2_texte)
            config.hero_bouton_2_lien     = request.form.get('hero_bouton_2_lien', config.hero_bouton_2_lien)
            config.philosophie_titre      = request.form.get('philosophie_titre', config.philosophie_titre)
            config.philosophie_sous_titre = request.form.get('philosophie_sous_titre', config.philosophie_sous_titre)
            config.philosophie_description_1 = request.form.get('philosophie_description_1', config.philosophie_description_1)
            config.philosophie_description_2 = request.form.get('philosophie_description_2', config.philosophie_description_2)
            config.competences_titre      = request.form.get('competences_titre', config.competences_titre)
            config.competences_sous_titre = request.form.get('competences_sous_titre', config.competences_sous_titre)
            config.certifications_titre   = request.form.get('certifications_titre', config.certifications_titre)
            config.certifications_sous_titre = request.form.get('certifications_sous_titre', config.certifications_sous_titre)
            # Champs JSON
            v_icons = request.form.getlist('valeur_icone[]')
            v_titres = request.form.getlist('valeur_titre[]')
            v_descriptions = request.form.getlist('valeur_description[]')
            config.values_json = [
                {"icon": icon, "titre": titre.strip(), "description": desc}
                for icon, titre, desc in zip(v_icons, v_titres, v_descriptions)
                if titre and titre.strip()
            ]
            p_periodes = request.form.getlist('parcours_periode[]')
            p_titres   = request.form.getlist('parcours_titre[]')
            p_descriptions = request.form.getlist('parcours_description[]')
            config.parcours_json = [
                {"periode": periode, "titre": titre.strip(), "description": desc}
                for periode, titre, desc in zip(p_periodes, p_titres, p_descriptions)
                if titre and titre.strip()
            ]
            c_icons = request.form.getlist('competence_icone[]')
            c_titres = request.form.getlist('competence_titre[]')
            c_descriptions = request.form.getlist('competence_description[]')
            config.competences_json = [
                {"icon": icon, "titre": titre.strip(), "description": desc}
                for icon, titre, desc in zip(c_icons, c_titres, c_descriptions)
                if titre and titre.strip()
            ]
            cert_titres      = request.form.getlist('certification_titre[]')
            cert_organismes  = request.form.getlist('certification_organisme[]')
            cert_descriptions = request.form.getlist('certification_description[]')
            config.certifications_json = [
                {"titre": titre.strip(), "organisme": organisme, "description": desc}
                for titre, organisme, desc in zip(cert_titres, cert_organismes, cert_descriptions)
                if titre and titre.strip()
            ]
            config.date_mise_a_jour = datetime.utcnow()
            db.session.commit()
            flash('Page À propos mise à jour avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
        return redirect(url_for('admin.about_edit'))
    return render_template('admin/about_edit.html', config=config)


@admin_bp.route('/media/<type_media>/<filename>')
@login_required
def serve_media(type_media, filename):
    """
    Sert les fichiers média dans l'espace admin.
    Vérifie que l'utilisateur courant est bien le propriétaire du fichier.
    """
    subdir = MEDIA_SUBDIRS.get(type_media)
    if not subdir:
        abort(404)

    # --- Vérification de propriété ---
    OWNED_PREFIXES = {
        'avatar': f'avatar_{current_user.id}_',
        'cover':  f'cover_{current_user.id}_',
        'cv':     f'cv_{current_user.id}_',
        'about':  f'about_{current_user.id}_',
    }
    prefix = OWNED_PREFIXES.get(type_media)
    if prefix and not filename.startswith(prefix):
        abort(403)

    if type_media == 'proj':
        # Vérifie que le projet appartient à l'utilisateur courant
        try:
            parts = filename.split('_')
            if len(parts) >= 2 and parts[1].isdigit():
                projet = Projet.query.filter_by(
                    id=int(parts[1]), utilisateur_id=current_user.id
                ).first()
                if not projet:
                    abort(403)
        except (IndexError, ValueError):
            abort(403)

    media_dir = get_media_path(subdir)
    try:
        return send_from_directory(media_dir, filename)
    except FileNotFoundError:
        abort(404)


@admin_bp.route('/migrate-avatars')
@login_required
def migrate_avatars():
    if current_user.role != 'admin':
        abort(403)
    users = Utilisateur.query.all()
    migrated_avatars = migrated_covers = errors = 0
    for user in users:
        if user.photo_profil and user.photo_profil.startswith(('http://', 'https://')):
            try:
                local_avatar = download_and_save_avatar(user.photo_profil, user.id, 'avatar')
                if local_avatar:
                    user.photo_profil = local_avatar
                    migrated_avatars += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
        if user.photo_couverture and user.photo_couverture.startswith(('http://', 'https://')):
            try:
                local_cover = download_and_save_avatar(user.photo_couverture, user.id, 'cover')
                if local_cover:
                    user.photo_couverture = local_cover
                    migrated_covers += 1
            except Exception:
                pass
    try:
        db.session.commit()
        flash(f"Migration terminée : {migrated_avatars} avatars, {migrated_covers} couvertures, {errors} erreurs.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur sauvegarde: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/init-media-folders')
@login_required
def init_media_folders():
    try:
        for subdir in MEDIA_SUBDIRS.values():
            get_media_path(subdir)
        return "Structure media créée. <a href='/admin/edit-profile'>Retour</a>"
    except Exception as e:
        return f"Erreur: {str(e)}", 500


@admin_bp.route('/debug-github-token')
@login_required
def debug_github_token():
    if not current_user.jeton_github:
        return {"error": "Pas de token GitHub"}
    headers = {
        'Authorization': f'token {current_user.jeton_github}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get('https://api.github.com/user', headers=headers)
    scopes = response.headers.get('X-OAuth-Scopes', 'Non spécifié')
    invites_response = requests.get(
        'https://api.github.com/user/repository_invitations', headers=headers
    )
    pending_invites = invites_response.json() if invites_response.status_code == 200 else []
    return {
        "scopes": scopes,
        "has_repo_scope": "repo" in scopes,
        "pending_invites_count": len(pending_invites),
        "pending_invites": pending_invites,
        "token_preview": current_user.jeton_github[:10] + "..."
    }


@admin_bp.route('/accept-invitations')
@login_required
def accept_invitations():
    if not current_user.jeton_github:
        flash("Token GitHub non configuré", "danger")
        return redirect(url_for('admin.edit_profile'))
    headers = {
        'Authorization': f'token {current_user.jeton_github}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get(
        'https://api.github.com/user/repository_invitations', headers=headers
    )
    if response.status_code != 200:
        flash("Impossible de récupérer les invitations", "danger")
        return redirect(url_for('admin.import_view'))
    accepted = 0
    for invite in response.json():
        invite_id = invite['id']
        repo_name = invite['repository']['full_name']
        accept_response = requests.patch(
            f'https://api.github.com/user/repository_invitations/{invite_id}',
            headers=headers
        )
        if accept_response.status_code == 204:
            accepted += 1
            flash(f"Invitation acceptée pour {repo_name}", "success")
        else:
            flash(f"Erreur pour {repo_name}", "danger")
    if accepted > 0:
        flash(f"{accepted} invitation(s) acceptée(s)!", "success")
    return redirect(url_for('admin.import_view'))


@admin_bp.route('/authorize')
@login_required
def authorize_page():
    if current_user.jeton_github:
        flash("Vous êtes déjà connecté à GitHub.", "info")
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/authorize.html')


@admin_bp.route('/start-github-auth')
@login_required
def start_github_auth():
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        flash("Erreur de configuration GitHub.", "danger")
        return redirect(url_for('admin.authorize_page'))
    return redirect(url_for('auth.social_login', name='github'))


@admin_bp.route('/skipp-authorize')
@login_required
def skipp_authorize():
    flash("Vous pourrez connecter GitHub plus tard depuis la page de profil.", "info")
    return redirect(url_for('admin.dashboard'))

# ============================================
# BLUEPRINT GITHUB
# ============================================

@github_bp.route('/authorize')
@login_required
def authorize():
    flash("Veuillez utiliser le lien 'Se connecter avec GitHub' sur la page de connexion.", "info")
    return redirect(url_for('auth.social_login', name='github'))


@github_bp.route('/callback')
@login_required
def callback():
    flash("Veuillez utiliser le lien 'Se connecter avec GitHub' sur la page de connexion.", "info")
    return redirect(url_for('auth.social_login', name='github'))


@github_bp.route('/revoke')
@login_required
def revoke():
    try:
        current_user.jeton_github = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la révocation : {str(e)}', 'error')
    finally:
        for key in ('github_token', 'github_user', 'oauth_state', 'next_url'):
            session.pop(key, None)
    flash('🔐 Accès GitHub révoqué', 'success')
    return redirect(url_for('admin.dashboard'))


@github_bp.route('/check')
@login_required
def check():
    return {'connected': bool(current_user.jeton_github), 'authenticated': True}


@github_bp.route('/debug')
def debug_github():
    return {
        'GITHUB_CLIENT_ID':    GITHUB_CLIENT_ID[:5] + '...' if GITHUB_CLIENT_ID else 'NON DÉFINI',
        'GITHUB_CLIENT_SECRET':'Défini' if GITHUB_CLIENT_SECRET else 'NON DÉFINI',
        'GOOGLE_CLIENT_ID':    GOOGLE_CLIENT_ID[:10] + '...' if GOOGLE_CLIENT_ID else 'NON DÉFINI',
        'GOOGLE_CLIENT_SECRET':'Défini' if GOOGLE_CLIENT_SECRET else 'NON DÉFINI',
        'authenticated': getattr(current_user, 'is_authenticated', False),
        'jeton_github':  'Présent' if getattr(current_user, 'jeton_github', None) else 'Absent'
    }

# ============================================
# BLUEPRINT PORTFOLIO (public)
# ============================================

@portfolio_bp.route('/portfolio')
def home():
    context = get_common_context()
    user    = context.get('user')
    projets = []
    config  = None
    if user:
        projets = Projet.query.filter_by(utilisateur_id=user.id).limit(3).all()
        config  = PortfolioConfig.query.filter_by(utilisateur_id=user.id).first()
    return render_template('portfolio/portfolio.html',
                           projets=projets, config=config, **context)


@portfolio_bp.route('/me_connaitre')
def me_connaitre():
    context = get_common_context()
    if not context['user']:
        abort(404)
    about_config = AboutPage.query.filter_by(
        utilisateur_id=context['user'].id
    ).first()
    return render_template('portfolio/me_connaitre.html',
                           about_config=about_config, **context)


@portfolio_bp.route('/projets')
def projets_liste():
    """
    Page publique listant tous les projets.
    `projet_phare` = premier projet avec image (mis en avant en tête de page).
    """
    context = get_common_context()
    if not context['user']:
        abort(404)
    tous_les_projets = (
        Projet.query
        .filter_by(utilisateur_id=context['user'].id)
        .order_by(Projet.id.desc())
        .all()
    )
    # Projet mis en avant : premier projet ayant une image de couverture
    projet_phare = next(
        (p for p in tous_les_projets if p.image_couverture), None
    ) or (tous_les_projets[0] if tous_les_projets else None)

    return render_template('portfolio/projet.html',
                           projets=tous_les_projets,
                           projet_phare=projet_phare,
                           **context)


@portfolio_bp.route('/contact')
def contact():
    context = get_common_context()
    if not context['user']:
        abort(404)
    return render_template('portfolio/contact.html', **context)


@portfolio_bp.route('/media/<folder>/<path:filename>')
def serve_public_media(folder, filename):
    """
    Sert les fichiers média publics (profils, projets, about…).
    Retourne une image placeholder si le fichier est absent ou si filename vaut 'None'.
    """
    allowed_folders = set(MEDIA_SUBDIRS.values())
    if folder not in allowed_folders:
        abort(404)

    # Sécurité : on refuse les filenames manifestement invalides
    if not filename or filename in ('None', 'null', 'undefined'):
        abort(404)

    media_dir = get_media_path(folder)
    file_path = os.path.join(media_dir, filename)

    if os.path.exists(file_path):
        return send_from_directory(media_dir, filename)

    # --- Fallback vers une image statique par défaut ---
    defaults = {
        'profiles': 'img/avatar.png',
        'covers':   'img/default-cover.jpg',
        'projects': 'img/default-project.jpg',
        'about':    'img/default-about.jpg',
        'docs':     'img/default-doc.jpg',
        'uploads':  'img/default-file.jpg',
    }
    static_fallback = defaults.get(folder)
    if static_fallback:
        static_dir = get_static_path()
        fallback_path = os.path.join(static_dir, static_fallback)
        if os.path.exists(fallback_path):
            return send_from_directory(
                os.path.dirname(fallback_path),
                os.path.basename(fallback_path)
            )
    abort(404)

# ============================================
# CRÉATION DE L'APPLICATION FLASK
# ============================================

app = Flask(__name__,
            static_folder='../static',
            template_folder='../templates')

# --- Base de données ---
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("❌ DATABASE_URL non définie dans les variables d'environnement")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI']        = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Paramètres du pool SQLAlchemy — critiques pour Vercel (serverless)
# NullPool désactive le pool : chaque requête ouvre/ferme sa propre connexion,
# ce qui est le comportement correct en environnement sans état.
if os.getenv('VERCEL') or os.getenv('VERCEL_ENV'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': NullPool,
        'connect_args': {'connect_timeout': 10},
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,   # vérifie la connexion avant chaque usage
        'pool_recycle':  300,    # recycle les connexions toutes les 5 min
        'pool_size':     5,
        'max_overflow':  10,
    }

# --- Configuration mail (optionnelle) ---
mail_server         = os.getenv('MAIL_SERVER')
mail_port           = os.getenv('MAIL_PORT')
mail_use_tls        = os.getenv('MAIL_USE_TLS')
mail_username       = os.getenv('MAIL_USERNAME')
mail_password       = os.getenv('MESSAGERIE_MOT_DE_PASSE')
mail_default_sender = os.getenv('MAIL_DEFAULT_SENDER')

if all([mail_server, mail_port, mail_username, mail_password]):
    app.config.update(
        MAIL_SERVER         = mail_server,
        MAIL_PORT           = int(mail_port),
        MAIL_USE_TLS        = (mail_use_tls == 'True') if mail_use_tls else True,
        MAIL_USERNAME       = mail_username,
        MAIL_PASSWORD       = mail_password,
        MAIL_DEFAULT_SENDER = mail_default_sender,
        MAIL_SUPPRESS_SEND  = False,
    )
    logger.info("✅ Configuration email chargée")
else:
    logger.warning("⚠️ Configuration email manquante – emails désactivés (mode dégradé)")
    app.config.update(
        MAIL_SUPPRESS_SEND  = True,
        MAIL_DEFAULT_SENDER = 'noreply@example.com',
    )

# --- Sécurité et OAuth ---
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    raise ValueError("❌ SECRET_KEY non définie")
app.config['SECRET_KEY'] = secret_key

github_client_id     = os.getenv('GITHUB_CLIENT_ID')
github_client_secret = os.getenv('GITHUB_CLIENT_SECRET')
if not github_client_id or not github_client_secret:
    raise ValueError("❌ Configuration GitHub OAuth incomplète")
app.config['GITHUB_CLIENT_ID']     = github_client_id
app.config['GITHUB_CLIENT_SECRET'] = github_client_secret

google_client_id     = os.getenv('GOOGLE_CLIENT_ID')
google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
if not google_client_id or not google_client_secret:
    raise ValueError("❌ Configuration Google OAuth incomplète")
app.config['GOOGLE_CLIENT_ID']     = google_client_id
app.config['GOOGLE_CLIENT_SECRET'] = google_client_secret

# --- Initialisation des extensions ---
db.init_app(app)
Migrate(app, db)
Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(Utilisateur, int(user_id))
    except Exception:
        return None

# Nettoyage de session SQLAlchemy après chaque requête (important en serverless)
@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()

oauth = OAuth(app)
oauth.register(
    name='github',
    client_id=app.config['GITHUB_CLIENT_ID'],
    client_secret=app.config['GITHUB_CLIENT_SECRET'],
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com',
    client_kwargs={'scope': 'user:email repo'},
)
oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- Enregistrement des blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(github_bp)

# --- Initialisation base de données ---
with app.app_context():
    db.create_all()
    try:
        ensure_token_column_exists()
    except Exception as e:
        logger.warning(f"ensure_token_column_exists: {e}")

if __name__ == "__main__":
    app.run(debug=True)