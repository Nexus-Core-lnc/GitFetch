import os
import requests
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app, send_from_directory, abort, session
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from dotenv import load_dotenv
from models import db, Utilisateur, Projet, PortfolioConfig, AboutPage

# Charger le fichier .env
load_dotenv()

# --- CONFIGURATIONS ---
# URL du micro-service Admin (pour redirections, mais en monolithe on peut utiliser url_for)
admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')

# Configuration GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

# --- CRÉATION DES BLUEPRINTS ---
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')  # Routes d'authentification
main_bp = Blueprint('main', __name__)  # Routes principales (accueil, etc.)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')  # Routes d'administration
portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')  # Routes publiques du portfolio avec préfixe /portfolio
github_bp = Blueprint('github_bp', __name__, url_prefix='/github')  # Routes GitHub OAuth

# --- FONCTIONS UTILITAIRES COMMUNES ---

def generer_jeton(email, salt):
    """Génère un jeton sécurisé pour les emails"""
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt=salt)

def verifier_jeton(token, salt, expiration=3600):
    """Vérifie un jeton email"""
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serialiseur.loads(token, salt=salt, max_age=expiration)
        return email
    except:
        return None

def envoyer_email(destinataire, sujet, template, **kwargs):
    """Envoie un email"""
    try:
        msg = Message(
            sujet,
            recipients=[destinataire],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        msg.html = render_template(f'auth/{template}', **kwargs)
        # Récupérer l'instance mail depuis l'application
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            print(f"Email envoyé à {destinataire}")
        else:
            print("ERREUR: Mail non configuré")
    except Exception as e:
        print(f"Erreur lors de l'envoi d'email: {e}")

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
    """
    Fonction utilitaire pour récupérer les données communes à toutes les pages du portfolio.
    """
    user = Utilisateur.query.first()  # On récupère le propriétaire du portfolio
    
    return {
        'user': user
    }

# ============================================
# BLUEPRINT AUTH (Authentification)
# ============================================

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Vérifier si l'email existe déjà
        if Utilisateur.query.filter_by(email=email).first():
            flash("Cette adresse email est déjà enregistrée.", "danger")
            return redirect(url_for('auth.login'))

        # Créer le nouvel utilisateur
        nouvel_utilisateur = Utilisateur(
            email=email,
            nom_utilisateur=email.split('@')[0],
            mot_de_passe_hache=generate_password_hash(password),
            est_confirme=False,
            photo_profil='default-avatar.jpg',
            photo_couverture='default-cover.jpg'
        )

        db.session.add(nouvel_utilisateur)
        db.session.commit()

        # Envoyer l'email de confirmation
        token = generer_jeton(email, 'email-confirm-salt')
        lien = url_for('auth.confirmer_email', token=token, _external=True)
        
        # Garder HTTP pour le développement local
        # Ne pas forcer HTTPS en local
        
        envoyer_email(email, "Confirmez votre compte GitFetch", 'email_confirmation.html', confirm_url=lien)

        flash("Compte créé ! Vérifiez votre boîte mail pour confirmer votre inscription.", "success")
        return redirect(url_for('auth.login'))

    return render_template("auth/register.html")

@auth_bp.route("/confirm/<token>")
def confirmer_email(token):
    """Confirmation d'email via le lien reçu"""
    email = verifier_jeton(token, 'email-confirm-salt')
    if not email:
        flash("Le lien de confirmation est invalide ou a expiré.", "danger")
        return redirect(url_for('auth.register'))

    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()
    
    if not utilisateur.est_confirme:
        utilisateur.est_confirme = True
        utilisateur.date_confirmation = datetime.utcnow()
        db.session.commit()
        flash("Email validé avec succès ! Vous pouvez maintenant vous connecter.", "success")
    else:
        flash("Cet email a déjà été confirmé.", "info")
    
    return redirect(url_for('auth.login'))

@auth_bp.route("/connexion", methods=['GET', 'POST'])
def login():
    """Connexion classique par email/mot de passe"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Utilisateur.query.filter_by(email=email).first()

        # 1. Vérification identifiants
        if not user or not user.mot_de_passe_hache or not check_password_hash(user.mot_de_passe_hache, password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return redirect(url_for('auth.login'))

        # 2. Vérification confirmation email
        if not user.est_confirme:
            flash('Veuillez confirmer votre email avant de vous connecter. Vérifiez votre boîte de réception.', 'warning')
            return redirect(url_for('auth.login'))

        # Mise à jour de la date de connexion
        try:
            user.derniere_connexion = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de la mise à jour de la date : {e}")

        # 3. Connexion de l'utilisateur
        login_user(user, remember=remember)
        
        flash(f"Bon retour parmi nous, {user.nom_utilisateur} !", "success")
        
        # Redirection vers le dashboard admin
        return redirect(url_for('admin.dashboard'))

    return render_template("auth/login.html")

@auth_bp.route("/deconnexion")
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    flash("Vous avez été déconnecté avec succès.", "info")
    return redirect(url_for('main.index'))

@auth_bp.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    """Demande de réinitialisation de mot de passe"""
    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user:
            token = generer_jeton(email, 'recover-password-salt')
            recover_url = url_for('auth.reset_password', token=token, _external=True)
            
            # Garder HTTP pour le développement local
            # Ne pas forcer HTTPS en local
                
            envoyer_email(email, "Réinitialisation de votre mot de passe", 'email_reset.html', recover_url=recover_url)
            
        # Toujours afficher le même message pour des raisons de sécurité
        flash("Si cette adresse email existe dans notre base, un lien de réinitialisation a été envoyé.", "info")
        return redirect(url_for('auth.login'))
        
    return render_template("auth/forgot_password.html")

@auth_bp.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    """Réinitialisation du mot de passe"""
    email = verifier_jeton(token, 'recover-password-salt', expiration=1800)  # 30 minutes
    if not email:
        flash("Le lien de réinitialisation est invalide ou a expiré.", "danger")
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template("auth/reset_password.html", token=token)
        
        if len(new_password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
            return render_template("auth/reset_password.html", token=token)
        
        user = Utilisateur.query.filter_by(email=email).first_or_404()
        user.mot_de_passe_hache = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Votre mot de passe a été mis à jour avec succès ! Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for('auth.login'))
        
    return render_template("auth/reset_password.html", token=token)

# --- AUTHENTIFICATION SOCIALE (OAUTH) ---

@auth_bp.route('/login/<name>')
def social_login(name):
    """Route pour l'authentification sociale (Google, GitHub)"""
    # Récupérer l'instance OAuth depuis l'application
    oauth = current_app.extensions.get('oauth')
    if not oauth:
        flash("Configuration OAuth manquante.", "danger")
        return redirect(url_for('auth.login'))
    
    client = oauth.create_client(name)
    if not client:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('auth.auth_callback', name=name, _external=True)
    
    # IMPORTANT: Pour le développement local, on garde HTTP
    # La ligne qui forçait le HTTPS a été supprimée
    
    print(f"DEBUG: Redirect URI: {redirect_uri}")
    
    # Paramètres supplémentaires selon le provider
    if name == 'github':
        return client.authorize_redirect(redirect_uri)
    elif name == 'google':
        return client.authorize_redirect(redirect_uri)
    else:
        return client.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/<name>')
def auth_callback(name):
    """Callback pour l'authentification sociale"""
    # Récupérer l'instance OAuth depuis l'application
    oauth = current_app.extensions.get('oauth')
    if not oauth:
        flash("Configuration OAuth manquante.", "danger")
        return redirect(url_for('auth.login'))
    
    client = oauth.create_client(name)
    if not client:
        flash(f"Provider OAuth '{name}' non supporté.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        token = client.authorize_access_token()
        access_token = token.get('access_token')
    except Exception as e:
        print(f"Erreur OAuth: {e}")
        flash("Erreur lors de l'authentification. Veuillez réessayer.", "danger")
        return redirect(url_for('auth.login'))
    
    # 1. Récupération des infos selon le provider
    try:
        if name == 'google':
            user_info = client.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
            email = user_info.get('email')
            pseudo = user_info.get('name', email.split('@')[0])
            avatar = user_info.get('picture')
        elif name == 'github':
            user_info = client.get('user').json()
            email = user_info.get('email')
            if not email:
                emails = client.get('user/emails').json()
                # Chercher l'email principal
                for e in emails:
                    if e.get('primary'):
                        email = e.get('email')
                        break
                if not email:
                    email = emails[0].get('email') if emails else None
            pseudo = user_info.get('login')
            avatar = user_info.get('avatar_url')
        else:
            flash(f"Provider '{name}' non implémenté.", "danger")
            return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"Erreur récupération infos utilisateur: {e}")
        flash("Erreur lors de la récupération de vos informations.", "danger")
        return redirect(url_for('auth.login'))
    
    if not email:
        flash("Impossible de récupérer votre adresse email.", "danger")
        return redirect(url_for('auth.login'))
    
    # 2. Gestion de l'utilisateur en DB
    user = Utilisateur.query.filter_by(email=email).first()
    if not user:
        # Nouvel utilisateur
        user = Utilisateur(
            email=email, 
            nom_utilisateur=pseudo, 
            est_confirme=True, 
            mot_de_passe_hache=None,
            photo_profil='default-avatar.jpg',
            photo_couverture='default-cover.jpg'
        )
        db.session.add(user)
        flash("Votre compte a été créé avec succès !", "success")
    else:
        flash(f"Bon retour parmi nous, {user.nom_utilisateur} !", "success")
    
    # 3. MISE À JOUR AUTOMATIQUE DU JETON ET AVATAR
    if name == 'github' and access_token:
        user.jeton_github = access_token
    
    # Sauvegarder l'avatar si c'est une URL (pas un fichier local)
    if avatar and avatar.startswith('http'):
        user.photo_profil = avatar  # C'est une URL, pas un fichier
    
    db.session.commit()
    
    # 4. Connexion et Redirection vers ADMIN
    login_user(user)
    return redirect(url_for('admin.dashboard'))

# ============================================
# BLUEPRINT MAIN (Routes principales)
# ============================================

@main_bp.route("/")
def index():
    """Page d'accueil du site"""
    return render_template('index.html')

# ============================================
# BLUEPRINT ADMIN (Dashboard et administration)
# ============================================

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Affiche le Dashboard divisé en sections :
    1. Résumé
    2. Projets Importés (Base de données)
    3. Dépôts GitHub (API)
    4. Paramètres
    """
    repos = []
    if current_user.jeton_github:
        headers = {
            'Authorization': f'token {current_user.jeton_github}',
            'Accept': 'application/vnd.github.v3+json'
        }
        github_url = 'https://api.github.com/user/repos?sort=updated&per_page=50&affiliation=owner'
        
        try:
            response = requests.get(github_url, headers=headers, timeout=10)
            if response.status_code == 200:
                repos = response.json()
            else:
                flash(f"Impossible de récupérer les dépôts GitHub (Code: {response.status_code})", "warning")
        except Exception as e:
            flash(f"Erreur de connexion à GitHub : {str(e)}", "danger")
    else:
        flash("Token GitHub non configuré. Connectez votre compte GitHub pour importer des dépôts.", "info")

    return render_template('admin/dashboard.html', repos=repos)





"""=============================================="""
#AFFICHAGE DES REPOS
import requests
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user

@admin_bp.route('/import-view')
@login_required
def import_view():
    """Affiche la page des dépôts GitHub disponibles pour l'importation"""
    repos = []
    if current_user.jeton_github:
        headers = {
            'Authorization': f'token {current_user.jeton_github}',
            'Accept': 'application/vnd.github.v3+json'
        }
        github_url = 'https://api.github.com/user/repos?sort=updated&per_page=50&affiliation=owner'
        
        try:
            response = requests.get(github_url, headers=headers, timeout=10)
            if response.status_code == 200:
                repos = response.json()
            else:
                flash(f"Impossible de récupérer les dépôts GitHub (Code: {response.status_code})", "warning")
        except Exception as e:
            flash(f"Erreur de connexion à GitHub: {str(e)}", "danger")
    else:
        flash("Veuillez configurer votre token GitHub dans les paramètres de profil", "warning")

    return render_template('admin/import_repos.html', repos=repos)

@admin_bp.route('/list-repos')
@login_required
def list_repos():
    """Affiche uniquement les projets déjà présents dans PostgreSQL"""
    projets = Projet.query.filter_by(utilisateur_id=current_user.id).order_by(Projet.id.desc()).all()
    return render_template('list_repos.html', projets=projets)

@admin_bp.route('/import-repo/<int:github_id>', methods=['POST'])
@login_required
def import_repo(github_id):
    """Importe un dépôt GitHub vers la base de données PostgreSQL"""
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

"""=============================================="""
@admin_bp.route('/edit-project/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    """Modifie les informations d'un projet dans la base de données"""
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()

    if request.method == 'POST':
        try:
            # Informations de base
            projet.nom = request.form.get('nom')
            projet.description = request.form.get('description')
            projet.demo_url = request.form.get('demo_url')
            projet.structure_nom = request.form.get('structure_nom')
            
            # Gestion de la collaboration
            est_collab = request.form.get('est_collaboration')
            projet.est_collaboration = est_collab == '1' if est_collab else False

            # === GESTION DES TECHNOLOGIES ANNEXES (LISTE) ===
            technologies_str = request.form.get('technologies_annexes', '')
            if technologies_str.strip():
                technologie_liste = [tech.strip() for tech in technologies_str.split(',') if tech.strip()]
                projet.technologies_annexes = technologie_liste
            else:
                projet.technologies_annexes = []

            # Gestion de l'image de couverture
            file = request.files.get('image_file')
            if file and file.filename:
                new_filename = save_media_file(file, 'proj', projet.id)
                if new_filename:
                    # Supprimer l'ancien fichier s'il existe
                    if projet.image_couverture:
                        delete_media_file(projet.image_couverture, 'proj')
                    projet.image_couverture = new_filename
                else:
                    flash("Format de fichier non supporté. Utilisez PNG, JPG ou GIF.", "warning")

            db.session.commit()
            flash("Informations mises à jour avec succès !", "success")
            return redirect(url_for('admin.list_repos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")

    # Pour l'affichage GET : convertir la liste en chaîne pour le formulaire
    technologies_texte = ""
    if projet.technologies_annexes:
        if isinstance(projet.technologies_annexes, list):
            technologies_texte = ", ".join(projet.technologies_annexes)
        else:
            technologies_texte = projet.technologies_annexes

    return render_template('admin/edit_project.html', 
                         projet=projet, 
                         technologies_texte=technologies_texte)

@admin_bp.route('/delete-project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    """Supprime un projet de la base de données"""
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
    """Redirige vers le dashboard pour forcer un appel API GitHub"""
    return redirect(url_for('admin.dashboard'))

# --- ROUTES DE PROFIL ET MEDIA ---

@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Gère l'édition du profil utilisateur
    """
    if request.method == 'POST':
        try:
            # === 1. INFORMATIONS PERSONNELLES ===
            current_user.nom_utilisateur = request.form.get('nom_utilisateur', current_user.nom_utilisateur)
            current_user.email = request.form.get('email', current_user.email)
            current_user.poste = request.form.get('poste', current_user.poste)
            current_user.localisation = request.form.get('localisation', current_user.localisation)
            current_user.site_web = request.form.get('site_web', current_user.site_web)
            current_user.biographie = request.form.get('biographie', current_user.biographie)
            
            # === 2. NUMÉROS DE TÉLÉPHONE ===
            current_user.telephone_principal = request.form.get('telephone_principal', current_user.telephone_principal)
            current_user.telephone_mobile = request.form.get('telephone_mobile', current_user.telephone_mobile)
            
            # === 3. RÉSEAUX SOCIAUX ===
            current_user.github = request.form.get('github', current_user.github)
            current_user.linkedin = request.form.get('linkedin', current_user.linkedin)
            current_user.twitter = request.form.get('twitter', current_user.twitter)
            
            # === 4. TOKEN GITHUB (privé) ===
            new_token = request.form.get('jeton_github', '').strip()
            if new_token:
                current_user.jeton_github = new_token
                flash('Token GitHub mis à jour', 'info')
            
            # === 5. THÈME ===
            current_user.theme_prefere = request.form.get('theme_prefere', current_user.theme_prefere)
            
            # === 6. GESTION DE L'AVATAR ===
            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(avatar_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_avatar = save_media_file(avatar_file, 'avatar', current_user.id)
                    if new_avatar:
                        if (current_user.photo_profil and 
                            current_user.photo_profil != 'default-avatar.jpg'):
                            delete_media_file(current_user.photo_profil, 'avatar')
                        
                        current_user.photo_profil = new_avatar
                        flash('Avatar mis à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour l\'avatar. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            # === 7. GESTION DE LA PHOTO DE COUVERTURE ===
            cover_file = request.files.get('cover')
            if cover_file and cover_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(cover_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_cover = save_media_file(cover_file, 'cover', current_user.id)
                    if new_cover:
                        if (current_user.photo_couverture and 
                            current_user.photo_couverture != 'default-cover.jpg'):
                            delete_media_file(current_user.photo_couverture, 'cover')
                        
                        current_user.photo_couverture = new_cover
                        flash('Photo de couverture mise à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour la couverture. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            # === 8. GESTION DU CV (PDF) ===
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
            
            # === 9. SAUVEGARDE EN BASE DE DONNÉES ===
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
    """Édition du contenu du portfolio"""
    # Récupérer ou créer la config pour l'utilisateur
    config = PortfolioConfig.query.filter_by(utilisateur_id=current_user.id).first()
    if not config:
        config = PortfolioConfig(utilisateur_id=current_user.id)
        db.session.add(config)

    if request.method == 'POST':
        # --- TEXTES SIMPLES ---
        config.hero_titre = request.form.get('hero_titre')
        config.hero_description = request.form.get('hero_description')
        config.about_titre = request.form.get('about_titre')
        config.about_soustitre = request.form.get('about_soustitre')
        config.about_description = request.form.get('about_description')
        config.about_lien_texte = request.form.get('about_lien_texte')
        config.projects_titre = request.form.get('projects_titre')
        config.cta_titre = request.form.get('cta_titre')

        # --- GESTION DES SPÉCIALITÉS ---
        s_noms = request.form.getlist('skill_item_nom[]')
        s_icons = request.form.getlist('skill_item_icon[]')
        
        skills_list = []
        for n, i in zip(s_noms, s_icons):
            if n.strip():
                skills_list.append({"nom": n, "icon": i})
        config.about_skills_json = skills_list

        # --- GESTION DE LA STACK TECHNIQUE ---
        t_noms = request.form.getlist('tech_nom[]')
        t_percents = request.form.getlist('tech_pourcent[]')
        t_icons = request.form.getlist('tech_icon[]')
        t_cats = request.form.getlist('tech_cat[]')

        tech_list = []
        for n, p, i, c in zip(t_noms, t_percents, t_icons, t_cats):
            if n.strip():
                tech_list.append({
                    "nom": n, 
                    "pourcent": p, 
                    "icon": i, 
                    "cat": c
                })
        
        config.tech_stack_json = tech_list

        try:
            db.session.commit()
            flash("Portfolio mis à jour avec succès !", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'enregistrement : {str(e)}", "danger")

        return redirect(url_for('admin.edit_portfolio_content'))

    return render_template('admin/edit_portfolio.html', config=config)

# --- ROUTES ABOUT (Administration) ---

@admin_bp.route('/about/edit', methods=['GET', 'POST'])
@login_required
def about_edit():
    """Édition de la page À propos"""
    config = AboutPage.query.filter_by(utilisateur_id=current_user.id).first()
    
    if request.method == 'POST':
        if not config:
            config = AboutPage(utilisateur_id=current_user.id)
        
        # Traitement des fichiers
        # Hero image
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
        
        # Philosophie image
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
        
        # Parcours image
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
        
        # Competences image
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
        
        # Certifications image
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
        config.hero_titre = request.form.get('hero_titre')
        config.hero_sous_titre = request.form.get('hero_sous_titre')
        config.philosophie_titre = request.form.get('philosophie_titre')
        config.philosophie_contenu = request.form.get('philosophie_contenu')
        config.parcours_titre = request.form.get('parcours_titre')
        config.parcours_contenu = request.form.get('parcours_contenu')
        config.competences_titre = request.form.get('competences_titre')
        config.competences_contenu = request.form.get('competences_contenu')
        config.certifications_titre = request.form.get('certifications_titre')
        
        db.session.add(config)
        db.session.commit()
        
        flash('Page À propos mise à jour avec succès!', 'success')
        return redirect(url_for('admin.about_edit'))
    
    return render_template('admin/about_edit.html', config=config)

# --- ROUTES DE SERVICE DE FICHIERS POUR L'ADMIN ---

import os
from flask import current_app, send_from_directory, abort

# Route publique pour le portfolio (à mettre dans la partie publique de routes.py)
@admin_bp.route('/media/<folder>/<filename>')
def serve_portfolio_media(folder, filename):
    """Sert les médias pour les visiteurs du portfolio"""
    # Liste blanche des dossiers autorisés pour éviter les failles de sécurité
    allowed_folders = ['profiles', 'covers', 'docs', 'projects', 'about', 'uploads']
    
    if folder not in allowed_folders:
        abort(404)

    # On pointe vers le dossier media à la racine
    # current_app.root_path est le dossier GITFETCH-MONOLITHIQUE
    media_dir = os.path.join(current_app.root_path, 'media', folder)
    
    return send_from_directory(media_dir, filename)

@admin_bp.route('/admin/media/<type>/<filename>')
@login_required
def serve_admin_media(type, filename):
    """Sert les fichiers depuis le dossier media avec vérification de propriété"""
    
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
    
    # Chemin vers le dossier media racine
    media_dir = os.path.join(current_app.root_path, 'media', subdir)
    
    # --- LOGIQUE DE SÉCURITÉ ---
    # Vérifier que le fichier appartient bien à l'utilisateur connecté
    prefix_map = {
        'avatar': f'avatar_{current_user.id}_',
        'cover': f'cover_{current_user.id}_',
        'cv': f'cv_{current_user.id}_'
    }

    if type in prefix_map:
        if not filename.startswith(prefix_map[type]):
            abort(403)
            
    elif type == 'proj':
        # Extraction de l'ID projet (format attendu : proj_ID_nom.jpg)
        try:
            parts = filename.split('_')
            if len(parts) > 1 and parts[1].isdigit():
                projet_id = int(parts[1])
                projet = Projet.query.filter_by(id=projet_id, utilisateur_id=current_user.id).first()
                if not projet:
                    abort(403)
            else:
                abort(403)
        except Exception:
            abort(403)
            
    return send_from_directory(media_dir, filename)

@admin_bp.route('/admin/init-media-folders')
@login_required
def init_media_folders():
    """Crée la structure media/ à la racine du projet"""
    try:
        # Dans un monolithe, root_path est la racine du projet
        media_path = os.path.join(current_app.root_path, 'media')
        
        subdirs = ['profiles', 'covers', 'docs', 'projects', 'about', 'uploads']
        created = []
        
        for subdir in subdirs:
            dir_path = os.path.join(media_path, subdir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                created.append(subdir)
        
        return f"Structure media prête. Dossiers créés : {', '.join(created) if created else 'Aucun (déjà existants)'}"
    except Exception as e:
        return f"Erreur : {str(e)}"


# ============================================
# BLUEPRINT GITHUB (Routes OAuth GitHub)
# ============================================

@github_bp.route('/authorize')
@login_required
def authorize():
    """Redirige vers GitHub pour l'autorisation OAuth"""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        flash('Configuration GitHub manquante. Contactez l\'administrateur.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Générer un état aléatoire pour la sécurité
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    
    # URL de callback
    redirect_uri = url_for('github_bp.callback', _external=True)
    
    # IMPORTANT: Pour le développement local, on garde HTTP
    # Ne pas forcer HTTPS en local
    
    # Paramètres de la requête OAuth
    params = {
        'client_id': GITHUB_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'repo read:user user:email',
        'state': state
    }
    
    # Stocker l'URL de redirection après autorisation
    next_url = request.args.get('next', url_for('admin.dashboard'))
    session['next_url'] = next_url
    print(f"Callback URL: {redirect_uri}")
    
    return redirect(f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}")

@github_bp.route('/callback')
@login_required
def callback():
    """Callback après autorisation GitHub"""
    # Vérifier l'état (sécurité CSRF)
    state = request.args.get('state')
    code = request.args.get('code')

    if not state or state != session.get('oauth_state'):
        flash("Erreur de sécurité OAuth (state invalide).", "error")
        return redirect(url_for('admin.dashboard'))

    if not code:
        flash("Code d'autorisation manquant.", "error")
        return redirect(url_for('admin.dashboard'))

    # Échanger le code contre un access_token
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
    )

    token_json = token_response.json()

    if "access_token" not in token_json:
        flash("Impossible de récupérer le token GitHub.", "error")
        return redirect(url_for('admin.dashboard'))

    access_token = token_json["access_token"]

    # Sauvegarder le token en base
    current_user.jeton_github = access_token
    db.session.commit()

    # Nettoyage session
    session.pop('oauth_state', None)

    flash("Compte GitHub connecté avec succès !", "success")
    return redirect(url_for('admin.dashboard'))

@github_bp.route('/revoke')
@login_required
def revoke():
    """Révoque l'accès GitHub"""
    try:
        # Supprimer le token de la base de données
        current_user.jeton_github = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la révocation : {str(e)}', 'error')
    finally:
        # Nettoyer la session
        session.pop('github_token', None)
        session.pop('github_user', None)
        session.pop('oauth_state', None)
        session.pop('next_url', None)
    
    flash('🔐 Accès GitHub révoqué', 'success')
    return redirect(url_for('admin.dashboard'))

@github_bp.route('/check')
@login_required
def check():
    """Vérifie si l'utilisateur est connecté à GitHub"""
    token = current_user.jeton_github
    
    if token:
        return {
            'connected': True,
            'authenticated': True
        }
    return {'connected': False, 'authenticated': True}

@github_bp.route('/debug')
def debug_github():
    """Route de debug pour vérifier la configuration GitHub"""
    info = {
        'GITHUB_CLIENT_ID': GITHUB_CLIENT_ID[:5] + '...' if GITHUB_CLIENT_ID else 'NON DÉFINI',
        'GITHUB_CLIENT_SECRET': 'Défini' if GITHUB_CLIENT_SECRET else 'NON DÉFINI',
        'GITHUB_AUTHORIZE_URL': GITHUB_AUTHORIZE_URL,
        'GITHUB_TOKEN_URL': GITHUB_TOKEN_URL,
        'authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'jeton_github': 'Présent' if hasattr(current_user, 'jeton_github') and current_user.jeton_github else 'Absent'
    }
    return info

# ============================================
# BLUEPRINT PORTFOLIO (Routes publiques)
# ============================================

@portfolio_bp.route('/portfolio')
def home():
    """Page d'accueil du portfolio"""
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
    """Page de présentation détaillée (À propos)"""
    context = get_common_context()
    if not context['user']:
        abort(404)
    
    about_config = AboutPage.query.filter_by(utilisateur_id=context['user'].id).first()
    
    return render_template('portfolio/me_connaitre.html', about_config=about_config, **context)

@portfolio_bp.route('/projets')
def projets_liste():
    """Page affichant l'intégralité des projets réalisés"""
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
    """Page de contact"""
    context = get_common_context()
    if not context['user']:
        abort(404)
        
    return render_template('portfolio/contact.html', **context)

# ============================================
# ROUTE UNIQUE POUR LES MÉDIAS PUBLICS DU PORTFOLIO
# ============================================

@portfolio_bp.route('/media/<folder>/<path:filename>')
def serve_public_media(folder, filename):
    """
    Route UNIQUE pour servir tous les médias publics depuis le dossier media.
    Supporte les dossiers : about, profiles, projects, covers, etc.
    """
    # Chemins possibles
    subdirs = ['about', 'profiles', 'projects', 'covers', 'docs', 'uploads']
    
    if folder not in subdirs:
        abort(404)
    
    # Chemin absolu vers le dossier media
    media_dir = get_media_path(folder)
    
    # Vérifier si le dossier existe
    if not os.path.exists(media_dir):
        print(f"ERREUR: Dossier introuvable - {media_dir}")
        # Fallback vers le dossier about par défaut
        default_dir = get_media_path('about')
        return send_from_directory(default_dir, 'default-about.jpg')
    
    try:
        return send_from_directory(media_dir, filename)
    except FileNotFoundError:
        print(f"ERREUR: Fichier introuvable - {os.path.join(media_dir, filename)}")
        # Fallback vers image par défaut selon le dossier
        default_files = {
            'about': 'default-about.jpg',
            'profiles': 'default-profile.jpg',
            'projects': 'default-project.jpg',
            'covers': 'default-cover.jpg',
            'docs': 'default-doc.pdf',
            'uploads': 'default-file.txt'
        }
        default_file = default_files.get(folder, 'default-about.jpg')
        
        # Vérifier si le fichier par défaut existe
        default_path = os.path.join(media_dir, default_file)
        if not os.path.exists(default_path):
            # Créer un fichier par défaut minimal
            with open(default_path, 'w') as f:
                f.write(f"Default {folder} file placeholder")
        
        return send_from_directory(media_dir, default_file)