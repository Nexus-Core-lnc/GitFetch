# routes.py - Version avec téléchargement local des avatars et correction GitHub OAuth

import os
import requests
import secrets
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app, send_from_directory, abort, session
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from dotenv import load_dotenv
from .models import db, Utilisateur, Projet, PortfolioConfig, AboutPage
from sqlalchemy import inspect, text
import time
import logging

# Charger le fichier .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATIONS ---
# Configuration GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

# Configuration Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

# --- CRÉATION DES BLUEPRINTS ---
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
portfolio_bp = Blueprint('portfolio', __name__)
github_bp = Blueprint('github_bp', __name__, url_prefix='/github')

# --- FONCTIONS UTILITAIRES COMMUNES ---

def download_and_save_avatar(url, user_id, type_file='avatar'):
    """Télécharge un avatar depuis une URL et le sauvegarde localement"""
    try:
        logger.info(f"Téléchargement de l'avatar depuis: {url}")
        response = requests.get(url, timeout=10, stream=True)
        
        if response.status_code == 200:
            # Déterminer l'extension et le dossier
            content_type = response.headers.get('content-type', '').lower()
            ext = '.jpg'
            
            if 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            
            # Déterminer le dossier
            folder = 'profiles' if type_file == 'avatar' else 'covers'
            
            # Générer un nom de fichier unique
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{type_file}_{user_id}_{timestamp}_{unique_id}{ext}"
            filename = secure_filename(filename)
            
            # Sauvegarder le fichier
            media_dir = get_media_path(folder)
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
    """Génère un jeton sécurisé pour les emails"""
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt=salt)

def verifier_jeton(token, salt, expiration=3600):
    """Vérifie un jeton email"""
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serialiseur.loads(token, salt=salt, max_age=expiration)
    except:
        return None

def envoyer_email(destinataire, sujet, template, **kwargs):
    """Envoie un email"""
    msg = Message(
        sujet,
        recipients=[destinataire],
        sender=current_app.config.get('MAIL_DEFAULT_SENDER')
    )
    msg.html = render_template(f'auth/{template}', **kwargs)
    mail = current_app.extensions.get('mail')
    if mail:
        try:
            mail.send(msg)
        except Exception as e:
            print(f"ERREUR envoi email: {e}")
    else:
        print("ERREUR: Mail non configuré")

def get_media_path(subdir=''):
    """Retourne le chemin absolu vers le dossier media et le crée s'il n'existe pas"""
    project_root = current_app.root_path
    media_path = os.path.join(project_root, 'media')
    
    if subdir:
        media_path = os.path.join(media_path, subdir)
    
    if not os.path.exists(media_path):
        os.makedirs(media_path, exist_ok=True)
    
    return media_path

def get_upload_path(subdir=''):
    """Retourne le chemin absolu vers le dossier uploads (dans media) et le crée s'il n'existe pas"""
    upload_path = get_media_path('uploads')
    
    if subdir:
        upload_path = os.path.join(upload_path, subdir)
    
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    
    return upload_path

def get_static_path():
    """Retourne le chemin absolu vers le dossier static"""
    return os.path.join(current_app.root_path, 'static')

def save_media_file(file, type_file, user_id):
    """Sauvegarde un fichier dans le dossier media approprié"""
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs',
        'proj': 'projects',
        'about': 'about'
    }
    
    subdir = subdirs.get(type_file, '')
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
    """Supprime un fichier du dossier media"""
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs',
        'proj': 'projects',
        'about': 'about'
    }
    
    subdir = subdirs.get(type_file, '')
    if not subdir or not filename:
        return False
    
    try:
        file_path = os.path.join(get_media_path(subdir), filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier {filename}: {e}")
    
    return False

def get_common_context():
    user = Utilisateur.query.order_by(Utilisateur.id.asc()).first()
    # ou mieux, prend le user qui a un CV/profil rempli :
    user = Utilisateur.query.filter(Utilisateur.est_confirme == True).first()
    return {'user': user}

def ensure_token_column_exists():
    """Vérifie et crée la colonne jeton_identification si elle n'existe pas"""
    try:
        inspector = inspect(db.engine)
        
        if not inspector.has_table('utilisateurs'):
            print("⚠️ Table utilisateurs n'existe pas encore")
            return False
            
        columns = [col['name'] for col in inspector.get_columns('utilisateurs')]
        
        if 'jeton_identification' not in columns:
            print("⚠️ Colonne jeton_identification manquante, tentative de création...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE utilisateurs ADD COLUMN jeton_identification VARCHAR(255)'))
                    conn.commit()
                print("✅ Colonne 'jeton_identification' ajoutée à la table utilisateurs")
                return True
            except Exception as alter_error:
                print(f"⚠️ Impossible d'ajouter la colonne: {alter_error}")
                return False
        return True
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification/création de la colonne: {e}")
        return False

def fetch_github_repos(token, max_retries=3):
    """Récupère les dépôts GitHub avec gestion des erreurs de connexion"""
    if not token:
        return [], "Token GitHub non configuré"
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Vérifier les scopes du token
    try:
        user_response = requests.get('https://api.github.com/user', headers=headers, timeout=5)
        scopes = user_response.headers.get('X-OAuth-Scopes', '')
        logger.info(f"Scopes du token GitHub: {scopes}")
        
        if 'repo' not in scopes:
            logger.warning("⚠️ Le token n'a pas le scope 'repo'! Les dépôts privés peuvent ne pas être accessibles.")
    except Exception as e:
        logger.error(f"Erreur vérification scopes: {e}")
    
    # Récupérer les invitations en attente
    try:
        invites_response = requests.get('https://api.github.com/user/repository_invitations', headers=headers, timeout=5)
        if invites_response.status_code == 200:
            pending_invites = invites_response.json()
            if pending_invites:
                logger.info(f"📨 {len(pending_invites)} invitations en attente trouvées")
                for invite in pending_invites:
                    logger.info(f"  - Invitation pour: {invite['repository']['full_name']}")
    except Exception as e:
        logger.error(f"Erreur récupération invitations: {e}")
    
    all_repos = []
    page = 1
    
    # URL corrigée pour inclure TOUS les dépôts (publics ET privés, propriétaire ET collaborateur)
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
                    logger.info(f"Page {page}: {len(repos)} dépôts récupérés")
                    
                    # Vérifier s'il y a une page suivante
                    if 'Link' in response.headers and 'rel="next"' in response.headers['Link']:
                        page += 1
                        continue
                    break
                    
                elif response.status_code == 401:
                    return [], "Token GitHub invalide ou expiré"
                elif response.status_code == 403:
                    reset_time = response.headers.get('X-RateLimit-Reset', 'inconnu')
                    return [], f"Limite de taux GitHub atteinte. Réessayez plus tard. (Reset: {reset_time})"
                else:
                    return [], f"Erreur GitHub (Code: {response.status_code})"
                    
            break
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erreur de connexion GitHub (tentative {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return [], "Impossible de se connecter à GitHub. Vérifiez votre connexion internet."
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout GitHub (tentative {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return [], "Délai d'attente dépassé pour la connexion à GitHub."
        
        except Exception as e:
            logger.error(f"Erreur inattendue GitHub: {e}")
            return [], f"Erreur inattendue: {str(e)}"
    
    # Filtrer les doublons
    unique_repos = {}
    for repo in all_repos:
        unique_repos[repo['id']] = repo
    
    repos_list = list(unique_repos.values())
    
    # Compter publics vs privés
    public_count = sum(1 for r in repos_list if not r.get('private', False))
    private_count = sum(1 for r in repos_list if r.get('private', False))
    logger.info(f"📊 Total: {len(repos_list)} dépôts (Publics: {public_count}, Privés: {private_count})")
    
    if len(repos_list) == 0:
        return [], "Aucun dépôt trouvé. Vérifiez que votre compte GitHub a des dépôts."
    
    return repos_list, None

def get_google_provider_cfg():
    """Récupère la configuration Google OAuth"""
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except:
        return None

# ============================================
# BLUEPRINT AUTH (Authentification)
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
        envoyer_email(email, "Confirmez votre compte GitFetch", 'email_confirmation.html', confirm_url=lien)

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
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

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
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            session['jeton_identification'] = nouveau_token
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Erreur lors de la mise à jour du token: {e}")

        login_user(user, remember=remember)
        return redirect(url_for('admin.dashboard'))

    return render_template("auth/login.html")

@auth_bp.route("/deconnexion")
@login_required
def logout():
    try:
        # Ne pas supprimer les données utilisateur
        if hasattr(current_user, 'jeton_identification'):
            # On garde le token pour la prochaine connexion
            pass
        db.session.commit()
    except:
        db.session.rollback()
        pass
    
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
            envoyer_email(email, "Réinitialisation de mot de passe", 'email_reset.html', recover_url=recover_url)
            
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
    """Route pour déboguer et voir le jeton actuel"""
    return {
        'user_id': current_user.id,
        'email': current_user.email,
        'jeton_identification': getattr(current_user, 'jeton_identification', 'Champ non existant'),
        'jeton_github': current_user.jeton_github,
        'session_token': session.get('jeton_identification'),
        'photo_profil': current_user.photo_profil,
        'photo_couverture': current_user.photo_couverture
    }

# --- AUTHENTIFICATION SOCIALE (OAUTH) ---

@auth_bp.route('/login/<name>')
def social_login(name):
    """Route pour l'authentification sociale (Google, GitHub)"""
    
    if name == 'github':
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            flash("Erreur de configuration GitHub. Contactez l'administrateur.", "danger")
            return redirect(url_for('auth.login'))
        
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        redirect_uri = url_for('auth.auth_callback', name='github', _external=True)
        
        params = {
            'client_id': GITHUB_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': 'user:email repo',  # ✅ AJOUT DU SCOPE 'repo' POUR LES DÉPÔTS PRIVÉS
            'state': state,
            'response_type': 'code',
             'allow_signup': 'true' 
        }
        
        return redirect(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")
    
    elif name == 'google':
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            flash("Erreur de configuration Google. Contactez l'administrateur.", "danger")
            return redirect(url_for('auth.login'))
        
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        
        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash("Impossible de contacter Google. Réessayez plus tard.", "danger")
            return redirect(url_for('auth.login'))
        
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        redirect_uri = url_for('auth.auth_callback', name='google', _external=True)
        
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        return redirect(f"{authorization_endpoint}?{urlencode(params)}")
    
    else:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))

@auth_bp.route('/auth/<name>')
def auth_callback(name):
    """Callback pour l'authentification sociale - AVEC TÉLÉCHARGEMENT LOCAL DES AVATARS"""
    
    if name == 'github':
        state = request.args.get('state')
        code = request.args.get('code')
        error = request.args.get('error')
        
        stored_state = session.get('oauth_state')
        session.pop('oauth_state', None)
        
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
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": url_for('auth.auth_callback', name='github', _external=True)
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
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json"
                },
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
            
            pseudo = user_info.get('login')
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
            
            # Avatar : uniquement pour les nouveaux utilisateurs
            if is_new_user or not user.photo_profil or user.photo_profil == 'default-avatar.jpg':
                if avatar_url:
                    local_avatar = download_and_save_avatar(avatar_url, user.id, 'avatar')
                    if local_avatar:
                        user.photo_profil = local_avatar
                        logger.info(f"Avatar GitHub téléchargé pour {user.email}: {local_avatar}")
                    else:
                        user.photo_profil = 'default-avatar.jpg'
                        logger.warning(f"Échec téléchargement avatar GitHub pour {user.email}, utilisation avatar par défaut")
                else:
                    user.photo_profil = 'default-avatar.jpg'
            else:
                logger.info(f"Avatar existant conservé pour {user.email}: {user.photo_profil}")
            
            try:
                ensure_token_column_exists()
                nouveau_token = secrets.token_urlsafe(32)
                user.jeton_identification = nouveau_token
                session['jeton_identification'] = nouveau_token
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération du jeton: {e}")
            
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=True)
            flash(f"Bienvenue {user.nom_utilisateur} ! Vous êtes connecté avec GitHub.", "success")
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"❌ Erreur inattendue GitHub: {e}")
            flash(f"Erreur inattendue: {str(e)}", "danger")
            return redirect(url_for('auth.login'))
    
    elif name == 'google':
        state = request.args.get('state')
        code = request.args.get('code')
        error = request.args.get('error')
        
        stored_state = session.get('oauth_state')
        session.pop('oauth_state', None)
        
        if error:
            flash(f"Erreur Google: {error}", "danger")
            return redirect(url_for('auth.login'))
        
        if not state or state != stored_state:
            flash("Erreur de sécurité OAuth (state invalide).", "danger")
            return redirect(url_for('auth.login'))
        
        if not code:
            flash("Code d'autorisation manquant.", "danger")
            return redirect(url_for('auth.login'))
        
        # Éviter les doublons de code
        if session.get('oauth_code_used') == code:
            print("⚠️ Code déjà utilisé, redirection vers login")
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
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": url_for('auth.auth_callback', name='google', _external=True)
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
            
            user_info = user_response.json()
            
            email = user_info.get('email')
            pseudo = user_info.get('name', email.split('@')[0])
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
            
            # Avatar : uniquement pour les nouveaux utilisateurs
            if is_new_user or not user.photo_profil or user.photo_profil == 'default-avatar.jpg':
                if avatar_url:
                    local_avatar = download_and_save_avatar(avatar_url, user.id, 'avatar')
                    if local_avatar:
                        user.photo_profil = local_avatar
                        logger.info(f"Avatar Google téléchargé pour {user.email}: {local_avatar}")
                    else:
                        user.photo_profil = 'default-avatar.jpg'
                        logger.warning(f"Échec téléchargement avatar Google pour {user.email}, utilisation avatar par défaut")
                else:
                    user.photo_profil = 'default-avatar.jpg'
            else:
                logger.info(f"Avatar existant conservé pour {user.email}: {user.photo_profil}")
            
            try:
                ensure_token_column_exists()
                nouveau_token = secrets.token_urlsafe(32)
                user.jeton_identification = nouveau_token
                session['jeton_identification'] = nouveau_token
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération du jeton: {e}")
            
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            
            session.pop('oauth_code_used', None)
            
            login_user(user, remember=True)
            flash(f"Bienvenue {user.nom_utilisateur} ! Vous êtes connecté avec Google.", "success")
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"❌ Erreur inattendue Google: {e}")
            session.pop('oauth_code_used', None)
            flash(f"Erreur inattendue: {str(e)}", "danger")
            return redirect(url_for('auth.login'))
    
    else:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))

# ============================================
# BLUEPRINT MAIN (Routes principales)
# ============================================

@main_bp.route("/")
def index():
    return render_template('index.html')

# ============================================
# BLUEPRINT ADMIN (Dashboard et administration)
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

    repos_dict = {}
    error_message = None
    
    repos, error_message = fetch_github_repos(current_user.jeton_github)
    
    if error_message:
        flash(error_message, "danger")
        return render_template('admin/import_repos.html', repos=[])
    
    for r in repos:
        if r['owner']['login'].lower() != current_user.nom_utilisateur.lower():
            r['user_role'] = f"Invité par {r['owner']['login']}"
        else:
            r['user_role'] = "Propriétaire"
        repos_dict[r['id']] = r
    
    repos_list = list(repos_dict.values())
    repos_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
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
    repo_url = request.form.get('repo_url')

    existant = Projet.query.filter_by(repo_id_github=str(github_id), utilisateur_id=current_user.id).first()
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
            print("\n" + "="*50)
            print("DÉBUT MODIFICATION PROJET")
            print("="*50)
            print(f"Projet ID: {id}")
            print(f"Projet nom actuel: {projet.nom}")
            print(f"Image couverture actuelle: {projet.image_couverture}")
            print(f"Logo actuel: {projet.logo_projet}")
            print(f"Utilisateur ID: {current_user.id}")
            
            # Récupération des données du formulaire
            projet.nom = request.form.get('nom', projet.nom)
            projet.description = request.form.get('description', projet.description)
            projet.demo_url = request.form.get('demo_url', projet.demo_url)
            projet.structure_nom = request.form.get('structure_nom', projet.structure_nom)
            
            est_collab = request.form.get('est_collaboration')
            projet.est_collaboration = est_collab == '1' if est_collab else False
            print(f"Type de projet: {'Collaboration' if projet.est_collaboration else 'Personnel'}")

            # Gestion des technologies
            technologies_str = request.form.get('technologies_annexes', '')
            if technologies_str.strip():
                technologie_liste = [tech.strip() for tech in technologies_str.split(',') if tech.strip()]
                projet.technologies_annexes = technologie_liste
                print(f"Technologies mises à jour: {technologie_liste}")
            else:
                projet.technologies_annexes = []
                print("Technologies vidées")

            # GESTION DE L'IMAGE DE COUVERTURE
            print("\n--- TRAITEMENT IMAGE DE COUVERTURE ---")
            
            delete_image = request.form.get('delete_image')
            print(f"Suppression demandée: {delete_image}")
            
            if delete_image == '1':
                if projet.image_couverture:
                    print(f"🗑️ Suppression de l'image: {projet.image_couverture}")
                    delete_media_file(projet.image_couverture, 'proj')
                    projet.image_couverture = None
                    print("✅ Image de couverture supprimée")
                    flash('Image de couverture supprimée', 'info')
                else:
                    print("⚠️ Aucune image à supprimer")
            
            image_file = request.files.get('image_file')
            
            if image_file and image_file.filename and image_file.filename.strip():
                print(f"📤 Upload de nouvelle image: {image_file.filename}")
                
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(image_file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                
                if ext in allowed_extensions:
                    new_filename = save_media_file(image_file, 'proj', projet.id)
                    
                    if new_filename:
                        if projet.image_couverture and projet.image_couverture != new_filename:
                            print(f"  - Suppression de l'ancienne image: {projet.image_couverture}")
                            delete_media_file(projet.image_couverture, 'proj')
                        
                        projet.image_couverture = new_filename
                        print(f"✅ Image assignée à projet.image_couverture: {projet.image_couverture}")
                        flash('Image de couverture mise à jour avec succès', 'success')
                    else:
                        print("❌ ERREUR: save_media_file a retourné None")
                        flash('Erreur lors de la sauvegarde de l\'image de couverture', 'danger')
                else:
                    print(f"❌ Extension non autorisée: {ext}")
                    flash(f'Format non supporté pour la couverture. Utilisez: {", ".join(allowed_extensions)}', 'warning')
            
            # GESTION DU LOGO
            print("\n--- TRAITEMENT LOGO ---")
            
            delete_logo = request.form.get('delete_logo')
            print(f"Suppression logo demandée: {delete_logo}")
            
            if delete_logo == '1':
                if projet.logo_projet:
                    print(f"🗑️ Suppression du logo: {projet.logo_projet}")
                    delete_media_file(projet.logo_projet, 'proj')
                    projet.logo_projet = None
                    print("✅ Logo supprimé")
                    flash('Logo supprimé', 'info')
                else:
                    print("⚠️ Aucun logo à supprimer")
            
            logo_file = request.files.get('logo_file')
            
            if logo_file and logo_file.filename and logo_file.filename.strip():
                print(f"📤 Upload de nouveau logo: {logo_file.filename}")
                
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(logo_file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                
                if ext in allowed_extensions:
                    new_logo = save_media_file(logo_file, 'proj', projet.id)
                    
                    if new_logo:
                        if projet.logo_projet and projet.logo_projet != new_logo:
                            print(f"  - Suppression de l'ancien logo: {projet.logo_projet}")
                            delete_media_file(projet.logo_projet, 'proj')
                        
                        projet.logo_projet = new_logo
                        print(f"✅ Logo assigné à projet.logo_projet: {projet.logo_projet}")
                        flash('Logo mis à jour avec succès', 'success')
                    else:
                        print("❌ ERREUR: save_media_file a retourné None")
                        flash('Erreur lors de la sauvegarde du logo', 'danger')
                else:
                    print(f"❌ Extension non autorisée: {ext}")
                    flash(f'Format non supporté pour le logo. Utilisez: {", ".join(allowed_extensions)}', 'warning')
            
            projet.date_mise_a_jour = datetime.utcnow()
            
            print("\n💾 Tentative de commit dans la base de données...")
            db.session.commit()
            print("✅ COMMIT RÉUSSI!")
            
            flash("Informations mises à jour avec succès !", "success")
            return redirect(url_for('admin.list_repos'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR: {e}")
            import traceback
            traceback.print_exc()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")
            return redirect(url_for('admin.edit_project', id=id))
    
    # GET request - Affichage du formulaire
    technologies_texte = ""
    if projet.technologies_annexes:
        if isinstance(projet.technologies_annexes, list):
            technologies_texte = ", ".join(projet.technologies_annexes)
        else:
            technologies_texte = projet.technologies_annexes
    
    projet_phare = None
    
    return render_template('admin/edit_project.html', 
                         projet=projet, 
                         technologies_texte=technologies_texte,
                         projet_phare=projet_phare)

@admin_bp.route('/delete-project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()
    
    if projet.image_couverture:
        delete_media_file(projet.image_couverture, 'proj')

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

# --- ROUTES DE PROFIL ET MEDIA ---

@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            current_user.nom_utilisateur = request.form.get('nom_utilisateur', current_user.nom_utilisateur)
            current_user.email = request.form.get('email', current_user.email)
            current_user.poste = request.form.get('poste', current_user.poste)
            current_user.localisation = request.form.get('localisation', current_user.localisation)
            current_user.site_web = request.form.get('site_web', current_user.site_web)
            current_user.biographie = request.form.get('biographie', current_user.biographie)
            
            current_user.telephone_principal = request.form.get('telephone_principal', current_user.telephone_principal)
            current_user.telephone_mobile = request.form.get('telephone_mobile', current_user.telephone_mobile)
            
            current_user.github = request.form.get('github', current_user.github)
            current_user.linkedin = request.form.get('linkedin', current_user.linkedin)
            current_user.twitter = request.form.get('twitter', current_user.twitter)
            
            new_token = request.form.get('jeton_github', '').strip()
            if new_token:
                current_user.jeton_github = new_token
                flash('Token GitHub mis à jour', 'info')
            
            current_user.theme_prefere = request.form.get('theme_prefere', current_user.theme_prefere)
            
            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(avatar_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_avatar = save_media_file(avatar_file, 'avatar', current_user.id)
                    if new_avatar:
                        if (current_user.photo_profil and 
                            current_user.photo_profil != 'default-avatar.jpg' and
                            not current_user.photo_profil.startswith(('http://', 'https://'))):
                            delete_media_file(current_user.photo_profil, 'avatar')
                        current_user.photo_profil = new_avatar
                        flash('Avatar mis à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour l\'avatar. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            cover_file = request.files.get('cover')
            if cover_file and cover_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(cover_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_cover = save_media_file(cover_file, 'cover', current_user.id)
                    if new_cover:
                        if (current_user.photo_couverture and 
                            current_user.photo_couverture != 'default-cover.jpg' and
                            not current_user.photo_couverture.startswith(('http://', 'https://'))):
                            delete_media_file(current_user.photo_couverture, 'cover')
                        current_user.photo_couverture = new_cover
                        flash('Photo de couverture mise à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour la couverture. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            cv_file = request.files.get('cv')
            if cv_file and cv_file.filename:
                allowed_extensions = {'pdf', 'doc', 'docx'}
                filename = secure_filename(cv_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    cv_file.seek(0, os.SEEK_END)
                    file_size = cv_file.tell()
                    cv_file.seek(0)
                    
                    if file_size > 5 * 1024 * 1024:
                        flash('Le fichier CV est trop volumineux. Taille maximale : 5 Mo.', 'warning')
                    else:
                        new_cv = save_media_file(cv_file, 'cv', current_user.id)
                        if new_cv:
                            if current_user.cv:
                                delete_media_file(current_user.cv, 'cv')
                            current_user.cv = new_cv
                            flash('CV mis à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour le CV. Utilisez PDF, DOC ou DOCX.', 'warning')
            
            current_user.derniere_connexion = datetime.utcnow()
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil : {str(e)}', 'danger')
        
        return redirect(url_for('admin.edit_profile'))
    
    return render_template('admin/edit_profile.html')

# --- ROUTES PORTFOLIO (Administration) ---

@admin_bp.route('/portfolio/edit', methods=['GET', 'POST'])
@login_required
def edit_portfolio_content():
    config = PortfolioConfig.query.filter_by(utilisateur_id=current_user.id).first()
    if not config:
        config = PortfolioConfig(utilisateur_id=current_user.id)
        db.session.add(config)
        db.session.flush()
        
        # Initialiser les JSON par défaut
        config.about_skills_json = []
        config.tech_stack_json = []
        db.session.commit()

    if request.method == 'POST':
        try:
            print("\n" + "="*50)
            print("📝 ENREGISTREMENT PORTFOLIO")
            print("="*50)
            
            # Section Hero
            config.hero_titre = request.form.get('hero_titre', config.hero_titre)
            
            # Vérifier si hero_description existe
            if hasattr(config, 'hero_description'):
                config.hero_description = request.form.get('hero_description', '')
            
            # Section About
            config.about_titre = request.form.get('about_titre', config.about_titre)
            config.about_soustitre = request.form.get('about_soustitre', config.about_soustitre)
            config.about_description = request.form.get('about_description', config.about_description)
            config.about_lien_texte = request.form.get('about_lien_texte', config.about_lien_texte)
            
            # Section Projets et CTA
            config.projects_titre = request.form.get('projects_titre', config.projects_titre)
            config.cta_titre = request.form.get('cta_titre', config.cta_titre)

            # Traitement des spécialités (skills)
            s_noms = request.form.getlist('skill_item_nom[]')
            s_icons = request.form.getlist('skill_item_icon[]')
            
            skills_list = []
            for n, i in zip(s_noms, s_icons):
                if n and n.strip():
                    skills_list.append({
                        "nom": n.strip(), 
                        "icon": i if i else "fas fa-star"
                    })
            config.about_skills_json = skills_list if skills_list else []
            print(f"✅ {len(skills_list)} spécialités enregistrées: {skills_list}")

            # Traitement de la stack technique
            t_noms = request.form.getlist('tech_nom[]')
            t_percents = request.form.getlist('tech_pourcent[]')
            t_icons = request.form.getlist('tech_icon[]')
            t_cats = request.form.getlist('tech_cat[]')

            tech_list = []
            for n, p, i, c in zip(t_noms, t_percents, t_icons, t_cats):
                if n and n.strip():
                    tech_list.append({
                        "nom": n.strip(), 
                        "pourcent": p if p else "0", 
                        "icon": i if i else "fas fa-code", 
                        "cat": c if c else ""
                    })
            
            config.tech_stack_json = tech_list if tech_list else []
            print(f"✅ {len(tech_list)} technologies enregistrées")
            
            db.session.commit()
            print("✅ COMMIT RÉUSSI!")
            flash("Portfolio mis à jour avec succès !", "success")
            return redirect(url_for('admin.edit_portfolio_content'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERREUR: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "danger")
            return redirect(url_for('admin.edit_portfolio_content'))

    # GET request - S'assurer que les JSON ne sont pas None
    if config.about_skills_json is None:
        config.about_skills_json = []
    if config.tech_stack_json is None:
        config.tech_stack_json = []
    
    return render_template('admin/edit_portfolio.html', config=config)
# --- ROUTES ABOUT (Administration) ---

@admin_bp.route('/about/edit', methods=['GET', 'POST'])
@login_required
def about_edit():
    config = AboutPage.query.filter_by(utilisateur_id=current_user.id).first()
    
    if request.method == 'POST':
        if not config:
            config = AboutPage(utilisateur_id=current_user.id)
            db.session.add(config)
        
        try:
            # Traitement des fichiers
            if 'hero_image' in request.files:
                file = request.files['hero_image']
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        if config.hero_image:
                            delete_media_file(config.hero_image, 'about')
                        config.hero_image = new_filename
            if request.form.get('hero_image_delete'):
                if config.hero_image:
                    delete_media_file(config.hero_image, 'about')
                    config.hero_image = None
            
            if 'philosophie_image' in request.files:
                file = request.files['philosophie_image']
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        if config.philosophie_image:
                            delete_media_file(config.philosophie_image, 'about')
                        config.philosophie_image = new_filename
            if request.form.get('philosophie_image_delete'):
                if config.philosophie_image:
                    delete_media_file(config.philosophie_image, 'about')
                    config.philosophie_image = None
            
            if 'parcours_image' in request.files:
                file = request.files['parcours_image']
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        if config.parcours_image:
                            delete_media_file(config.parcours_image, 'about')
                        config.parcours_image = new_filename
            if request.form.get('parcours_image_delete'):
                if config.parcours_image:
                    delete_media_file(config.parcours_image, 'about')
                    config.parcours_image = None
            
            if 'competences_image' in request.files:
                file = request.files['competences_image']
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        if config.competences_image:
                            delete_media_file(config.competences_image, 'about')
                        config.competences_image = new_filename
            if request.form.get('competences_image_delete'):
                if config.competences_image:
                    delete_media_file(config.competences_image, 'about')
                    config.competences_image = None
            
            if 'certifications_image' in request.files:
                file = request.files['certifications_image']
                if file and file.filename:
                    new_filename = save_media_file(file, 'about', current_user.id)
                    if new_filename:
                        if config.certifications_image:
                            delete_media_file(config.certifications_image, 'about')
                        config.certifications_image = new_filename
            if request.form.get('certifications_image_delete'):
                if config.certifications_image:
                    delete_media_file(config.certifications_image, 'about')
                    config.certifications_image = None
            
            # Texte
            config.hero_titre = request.form.get('hero_titre', config.hero_titre)
            config.hero_texte = request.form.get('hero_texte', config.hero_texte)
            config.hero_bouton_1_texte = request.form.get('hero_bouton_1_texte', config.hero_bouton_1_texte)
            config.hero_bouton_1_lien = request.form.get('hero_bouton_1_lien', config.hero_bouton_1_lien)
            config.hero_bouton_2_texte = request.form.get('hero_bouton_2_texte', config.hero_bouton_2_texte)
            config.hero_bouton_2_lien = request.form.get('hero_bouton_2_lien', config.hero_bouton_2_lien)
            
            config.philosophie_titre = request.form.get('philosophie_titre', config.philosophie_titre)
            config.philosophie_sous_titre = request.form.get('philosophie_sous_titre', config.philosophie_sous_titre)
            config.philosophie_description_1 = request.form.get('philosophie_description_1', config.philosophie_description_1)
            config.philosophie_description_2 = request.form.get('philosophie_description_2', config.philosophie_description_2)
            
            config.competences_titre = request.form.get('competences_titre', config.competences_titre)
            config.competences_sous_titre = request.form.get('competences_sous_titre', config.competences_sous_titre)
            
            config.certifications_titre = request.form.get('certifications_titre', config.certifications_titre)
            config.certifications_sous_titre = request.form.get('certifications_sous_titre', config.certifications_sous_titre)
            
            # GESTION DES JSON
            v_icons = request.form.getlist('valeur_icone[]')
            v_titres = request.form.getlist('valeur_titre[]')
            v_descriptions = request.form.getlist('valeur_description[]')
            
            valeurs_list = []
            for icon, titre, desc in zip(v_icons, v_titres, v_descriptions):
                if titre and titre.strip():
                    valeurs_list.append({
                        "icon": icon,
                        "titre": titre.strip(),
                        "description": desc
                    })
            config.values_json = valeurs_list if valeurs_list else []
            
            p_periodes = request.form.getlist('parcours_periode[]')
            p_titres = request.form.getlist('parcours_titre[]')
            p_descriptions = request.form.getlist('parcours_description[]')
            
            parcours_list = []
            for periode, titre, desc in zip(p_periodes, p_titres, p_descriptions):
                if titre and titre.strip():
                    parcours_list.append({
                        "periode": periode,
                        "titre": titre.strip(),
                        "description": desc
                    })
            config.parcours_json = parcours_list if parcours_list else []
            
            c_icons = request.form.getlist('competence_icone[]')
            c_titres = request.form.getlist('competence_titre[]')
            c_descriptions = request.form.getlist('competence_description[]')
            
            competences_list = []
            for icon, titre, desc in zip(c_icons, c_titres, c_descriptions):
                if titre and titre.strip():
                    competences_list.append({
                        "icon": icon,
                        "titre": titre.strip(),
                        "description": desc
                    })
            config.competences_json = competences_list if competences_list else []
            
            cert_titres = request.form.getlist('certification_titre[]')
            cert_organismes = request.form.getlist('certification_organisme[]')
            cert_descriptions = request.form.getlist('certification_description[]')
            
            certifications_list = []
            for titre, organisme, desc in zip(cert_titres, cert_organismes, cert_descriptions):
                if titre and titre.strip():
                    certifications_list.append({
                        "titre": titre.strip(),
                        "organisme": organisme,
                        "description": desc
                    })
            config.certifications_json = certifications_list if certifications_list else []
            
            config.date_mise_a_jour = datetime.utcnow()
            
            db.session.commit()
            flash('Page À propos mise à jour avec succès!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
        
        return redirect(url_for('admin.about_edit'))
    
    return render_template('admin/about_edit.html', config=config)

# --- ROUTES DE SERVICE DE FICHIERS POUR L'ADMIN ---

@admin_bp.route('/media/<type>/<filename>')
@login_required
def serve_media(type, filename):
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs',
        'proj': 'projects',
        'about': 'about'
    }
    
    subdir = subdirs.get(type)
    if not subdir:
        abort(404)
    
    media_dir = get_media_path(subdir)
    
    if type == 'avatar' and not filename.startswith(f'avatar_{current_user.id}_'):
        abort(403)
    elif type == 'cover' and not filename.startswith(f'cover_{current_user.id}_'):
        abort(403)
    elif type == 'cv' and not filename.startswith(f'cv_{current_user.id}_'):
        abort(403)
    elif type == 'proj':
        try:
            projet_id = filename.split('_')[1] if '_' in filename else None
            if projet_id and projet_id.isdigit():
                projet = Projet.query.filter_by(id=int(projet_id), utilisateur_id=current_user.id).first()
                if not projet:
                    abort(403)
        except (IndexError, ValueError):
            abort(403)
    
    try:
        return send_from_directory(media_dir, filename)
    except FileNotFoundError:
        abort(404)

# --- ROUTE DE MIGRATION DES AVATARS ---

@admin_bp.route('/migrate-avatars')
@login_required
def migrate_avatars():
    """Migre les avatars des URLs externes vers des fichiers locaux"""
    if current_user.role != 'admin':
        flash("Accès réservé aux administrateurs.", "danger")
        abort(403)
    
    users = Utilisateur.query.all()
    migrated_avatars = 0
    migrated_covers = 0
    errors = 0
    
    for user in users:
        # Migrer l'avatar
        if user.photo_profil and user.photo_profil.startswith(('http://', 'https://')):
            try:
                logger.info(f"Migration avatar pour {user.email}: {user.photo_profil}")
                local_avatar = download_and_save_avatar(user.photo_profil, user.id, 'avatar')
                if local_avatar:
                    user.photo_profil = local_avatar
                    migrated_avatars += 1
                    logger.info(f"Avatar migré avec succès: {local_avatar}")
                else:
                    errors += 1
                    logger.error(f"Échec migration avatar pour {user.email}")
            except Exception as e:
                errors += 1
                logger.error(f"Erreur migration avatar {user.id}: {e}")
        
        # Migrer la couverture si c'est une URL externe
        if user.photo_couverture and user.photo_couverture.startswith(('http://', 'https://')):
            try:
                logger.info(f"Migration cover pour {user.email}: {user.photo_couverture}")
                local_cover = download_and_save_avatar(user.photo_couverture, user.id, 'cover')
                if local_cover:
                    user.photo_couverture = local_cover
                    migrated_covers += 1
                    logger.info(f"Cover migrée avec succès: {local_cover}")
            except Exception as e:
                logger.error(f"Erreur migration cover {user.id}: {e}")
    
    try:
        db.session.commit()
        flash(f"Migration terminée : {migrated_avatars} avatars migrés, {migrated_covers} couvertures migrées, {errors} erreurs.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la sauvegarde: {str(e)}", "danger")
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/init-media-folders')
def init_media_folders():
    try:
        project_root = current_app.root_path
        media_path = os.path.join(project_root, 'media')
        
        subdirs = ['profiles', 'covers', 'docs', 'projects', 'about', 'uploads']
        
        for subdir in subdirs:
            dir_path = os.path.join(media_path, subdir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"Créé: {dir_path}")
        
        return f'''
        <h1>Structure media créée avec succès!</h1>
        <p>Racine du projet: {project_root}</p>
        <p>Dossier media: {media_path}</p>
        <ul>
            <li>{os.path.join(media_path, 'profiles')}</li>
            <li>{os.path.join(media_path, 'covers')}</li>
            <li>{os.path.join(media_path, 'docs')}</li>
            <li>{os.path.join(media_path, 'projects')}</li>
            <li>{os.path.join(media_path, 'about')}</li>
            <li>{os.path.join(media_path, 'uploads')}</li>
        </ul>
        <p><a href="{url_for('admin.migrate_avatars')}" class="btn btn-primary">Lancer la migration des avatars</a></p>
        <p><a href="{url_for('admin.edit_profile')}">Retour à l'édition du profil</a></p>
        '''
    
    except Exception as e:
        return f"Erreur lors de la création de la structure media: {str(e)}"

# --- ROUTES DE DÉBOGAGE GITHUB ---

@admin_bp.route('/debug-github-token')
@login_required
def debug_github_token():
    """Vérifie les permissions du token GitHub"""
    if not current_user.jeton_github:
        return {"error": "Pas de token GitHub"}
    
    headers = {
        'Authorization': f'token {current_user.jeton_github}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Vérifier les scopes du token
    response = requests.get('https://api.github.com/user', headers=headers)
    scopes = response.headers.get('X-OAuth-Scopes', 'Non spécifié')
    
    # Vérifier les invitations en attente
    invites_response = requests.get('https://api.github.com/user/repository_invitations', headers=headers)
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
    """Accepte toutes les invitations GitHub en attente"""
    if not current_user.jeton_github:
        flash("Token GitHub non configuré", "danger")
        return redirect(url_for('admin.edit_profile'))
    
    headers = {
        'Authorization': f'token {current_user.jeton_github}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Récupérer les invitations
    response = requests.get('https://api.github.com/user/repository_invitations', headers=headers)
    
    if response.status_code != 200:
        flash("Impossible de récupérer les invitations", "danger")
        return redirect(url_for('admin.import_view'))
    
    invitations = response.json()
    accepted = 0
    
    for invite in invitations:
        invite_id = invite['id']
        repo_name = invite['repository']['full_name']
        
        # Accepter l'invitation
        accept_response = requests.patch(
            f'https://api.github.com/user/repository_invitations/{invite_id}',
            headers=headers
        )
        
        if accept_response.status_code == 204:
            accepted += 1
            flash(f"✅ Invitation acceptée pour {repo_name}", "success")
        else:
            flash(f"❌ Erreur pour {repo_name}", "danger")
    
    if accepted > 0:
        flash(f"{accepted} invitation(s) acceptée(s)! Rafraîchissez la liste des dépôts.", "success")
    
    return redirect(url_for('admin.import_view'))

# ============================================
# BLUEPRINT GITHUB (Routes GitHub OAuth)
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
        session.pop('github_token', None)
        session.pop('github_user', None)
        session.pop('oauth_state', None)
        session.pop('next_url', None)
    
    flash('🔐 Accès GitHub révoqué', 'success')
    return redirect(url_for('admin.dashboard'))

@github_bp.route('/check')
@login_required
def check():
    token = current_user.jeton_github
    
    if token:
        return {
            'connected': True,
            'authenticated': True
        }
    return {'connected': False, 'authenticated': True}

@github_bp.route('/debug')
def debug_github():
    info = {
        'GITHUB_CLIENT_ID': GITHUB_CLIENT_ID[:5] + '...' if GITHUB_CLIENT_ID else 'NON DÉFINI',
        'GITHUB_CLIENT_SECRET': 'Défini' if GITHUB_CLIENT_SECRET else 'NON DÉFINI',
        'GITHUB_AUTHORIZE_URL': GITHUB_AUTHORIZE_URL,
        'GITHUB_TOKEN_URL': GITHUB_TOKEN_URL,
        'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID[:10] + '...' if GOOGLE_CLIENT_ID else 'NON DÉFINI',
        'GOOGLE_CLIENT_SECRET': 'Défini' if GOOGLE_CLIENT_SECRET else 'NON DÉFINI',
        'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'jeton_github': 'Présent' if hasattr(current_user, 'jeton_github') and current_user.jeton_github else 'Absent'
    }
    return info

# ============================================
# BLUEPRINT PORTFOLIO (Routes publiques)
# ============================================

@portfolio_bp.route('/portfolio')
def home():
    context = get_common_context()
    user = context.get('user')
    
    projets = []
    config = None
    if user:
        projets = Projet.query.filter_by(utilisateur_id=user.id).limit(3).all()
        config = PortfolioConfig.query.filter_by(utilisateur_id=user.id).first()

    return render_template(
        'portfolio/portfolio.html', 
        projets=projets, 
        config=config, 
        **context
    )

@portfolio_bp.route('/me_connaitre')
def me_connaitre():
    context = get_common_context()
    if not context['user']:
        abort(404)
    
    about_config = AboutPage.query.filter_by(utilisateur_id=context['user'].id).first()
    
    return render_template('portfolio/me_connaitre.html', about_config=about_config, **context)

@portfolio_bp.route('/projets')
def projets_liste():
    context = get_common_context()
    if not context['user']:
        abort(404)
    
    tous_les_projets = Projet.query.filter_by(utilisateur_id=context['user'].id)\
                                   .order_by(Projet.id.desc()).all()
    
    return render_template('portfolio/projet.html', 
                           projets=tous_les_projets, 
                           **context)

@portfolio_bp.route('/contact')
def contact():
    context = get_common_context()
    if not context['user']:
        abort(404)
        
    return render_template('portfolio/contact.html', **context)

# ============================================
# ROUTE UNIQUE POUR LES MÉDIAS PUBLICS DU PORTFOLIO
# ============================================

@portfolio_bp.route('/media/<folder>/<path:filename>')
def serve_public_media(folder, filename):
    subdirs = ['about', 'profiles', 'projects', 'covers', 'docs', 'uploads']
    
    if folder not in subdirs:
        abort(404)
    
    media_dir = get_media_path(folder)
    
    if not os.path.exists(media_dir):
        print(f"ERREUR: Dossier introuvable - {media_dir}")
        default_dir = get_media_path('about')
        try:
            return send_from_directory(default_dir, 'default-about.jpg')
        except:
            abort(404)
    
    try:
        return send_from_directory(media_dir, filename)
    except FileNotFoundError:
        print(f"ERREUR: Fichier introuvable - {os.path.join(media_dir, filename)}")
        default_files = {
            'about': 'default-about.jpg',
            'profiles': 'default-profile.jpg',
            'projects': 'default-project.jpg',
            'covers': 'default-cover.jpg',
            'docs': 'default-doc.pdf',
            'uploads': 'default-file.txt'
        }
        default_file = default_files.get(folder, 'default-about.jpg')
        
        try:
            return send_from_directory(media_dir, default_file)
        except:
            abort(404)
    print(f"Cherche: {os.path.join(media_dir, filename)}")
    print(f"Existe: {os.path.exists(os.path.join(media_dir, filename))}")
    
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
        flash("Erreur de configuration GitHub. Contactez l'administrateur.", "danger")
        return redirect(url_for('admin.authorize_page'))
    
    return redirect(url_for('auth.social_login', name='github'))

@admin_bp.route('/skipp-authorize')
@login_required
def skipp_authorize():
    flash("Vous pourrez connecter GitHub plus tard depuis la page de profil.", "info")
    return redirect(url_for('admin.dashboard'))