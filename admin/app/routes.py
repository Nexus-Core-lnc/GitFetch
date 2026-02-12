import os
import requests
import secrets
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort, session
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from models import db, Projet, Utilisateur, PortfolioConfig, AboutPage
from urllib.parse import urlencode

# Blueprint principal admin
admin_bp = Blueprint('admin', __name__)

# Blueprint GitHub
github_bp = Blueprint('github_bp', __name__)

# Configuration GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

# --- FONCTIONS UTILITAIRES ---

def get_upload_path(subdir=''):
    """Retourne le chemin absolu vers le dossier uploads et le crée s'il n'existe pas"""
    upload_path = os.path.join(current_app.root_path, '..', 'static', 'uploads')
    
    if subdir:
        upload_path = os.path.join(upload_path, subdir)
    
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    
    return upload_path

def get_static_path():
    """Retourne le chemin absolu vers le dossier static"""
    return os.path.join(current_app.root_path, '..', 'static')

def save_uploaded_file(file, type_file, user_id):
    """Sauvegarde un fichier uploadé dans le dossier approprié"""
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs',
        'proj': 'projects'
    }
    subdir = subdirs.get(type_file, '')
    
    upload_dir = get_upload_path(subdir)
    
    filename = secure_filename(f"{type_file}_{user_id}_{file.filename}")
    full_path = os.path.join(upload_dir, filename)
    
    file.save(full_path)
    return filename

# --- ROUTES DE SERVICE DE FICHIERS ---

@admin_bp.route('/serve-static/media/profiles/<filename>')
def serve_profile_pic(filename):
    media_path = os.path.join(current_app.root_path, 'media', 'profiles')
    return send_from_directory(media_path, filename)

@admin_bp.route('/serve-static/media/docs/<filename>')
def serve_cv(filename):
    docs_path = os.path.join(current_app.root_path, 'media', 'docs')
    return send_from_directory(docs_path, filename, as_attachment=True)

@admin_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Route pour servir les fichiers uploadés"""
    return send_from_directory(get_upload_path(), filename)

@admin_bp.route('/serve-static/<path:filename>')
def serve_root_static(filename):
    """Envoie les fichiers depuis le dossier static racine"""
    root_static = get_static_path()
    return send_from_directory(root_static, filename)

# --- ROUTES GITHUB OAUTH ---

@github_bp.route('/authorize')
def authorize():
    """Redirige vers GitHub pour l'autorisation OAuth"""
    if not current_user.is_authenticated:
        flash('Veuillez vous connecter d\'abord', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        flash('Configuration GitHub manquante. Contactez l\'administrateur.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Générer un état aléatoire pour la sécurité
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    
    # URL de callback
    redirect_uri = url_for('github_bp.callback', _external=True)

    
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
def revoke():
    """Révoque l'accès GitHub"""
    if not current_user.is_authenticated:
        flash('Veuillez vous connecter d\'abord', 'warning')
        return redirect(url_for('admin.dashboard'))
    
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
    return redirect(url_for('admin.authorize_page'))

@github_bp.route('/check')
def check():
    """Vérifie si l'utilisateur est connecté à GitHub"""
    if not current_user.is_authenticated:
        return {'connected': False, 'authenticated': False}
    
    token = session.get('github_token') or current_user.jeton_github
    user = session.get('github_user')
    
    if token and user:
        return {
            'connected': True,
            'user': user.get('login'),
            'avatar': user.get('avatar_url'),
            'authenticated': True
        }
    return {'connected': False, 'authenticated': True}

# --- ROUTES ADMIN PAGES D'AUTORISATION ---

@admin_bp.route('/authorize')
def authorize_page():
    """Page d'autorisation GitHub"""
    return render_template('authorize.html')

@admin_bp.route('/skip-authorize')
def skipp_authorize():
    """Passer l'autorisation pour le moment"""
    if not current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    session['skip_github'] = True
    session['skip_github_time'] = datetime.utcnow().isoformat()
    flash('Vous pourrez connecter GitHub plus tard depuis le menu', 'info')
    return redirect(url_for('admin.dashboard'))

# --- ROUTES PRINCIPALES ADMIN ---

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

    return render_template('dashboard.html', repos=repos)

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

    return render_template('import_repos.html', repos=repos)

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
                new_filename = save_uploaded_file(file, 'proj', projet.id)
                if new_filename:
                    # Supprimer l'ancien fichier s'il existe
                    if projet.image_couverture:
                        old_file = os.path.join(get_upload_path('projects'), projet.image_couverture)
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass
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

    return render_template('edit_project.html', 
                         projet=projet, 
                         technologies_texte=technologies_texte)

@admin_bp.route('/delete-project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    """Supprime un projet de la base de données (le retire du front-end)"""
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()
    
    if projet.image_couverture:
        old_file = os.path.join(get_upload_path('projects'), projet.image_couverture)
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier: {e}")

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
    """Redirige simplement vers le dashboard pour forcer un appel API GitHub"""
    return redirect(url_for('admin.dashboard'))

# --- ROUTES DE PROFIL ET MEDIA ---

@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Gère l'édition du profil utilisateur avec une structure media/ à la racine du projet.
    Dossiers : media/profiles/, media/covers/, media/docs/
    """
    
    def get_media_path(subdir=''):
        """Retourne le chemin absolu vers le dossier media et le crée s'il n'existe pas"""
        project_root = current_app.root_path
        media_path = os.path.join(project_root, 'media')
        
        if subdir:
            media_path = os.path.join(media_path, subdir)
        
        if not os.path.exists(media_path):
            os.makedirs(media_path, exist_ok=True)
        
        return media_path
    
    def get_media_url(filename, type_file):
        """Retourne l'URL pour servir les fichiers depuis le dossier media"""
        return url_for('admin.serve_media', type=type_file, filename=filename)
    
    def save_media_file(file, type_file, user_id):
        """Sauvegarde un fichier dans le dossier media approprié"""
        subdirs = {
            'avatar': 'profiles',
            'cover': 'covers',
            'cv': 'docs'
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
            'cv': 'docs'
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
    
    return render_template('edit_profile.html')

@admin_bp.route('/media/<type>/<filename>')
@login_required
def serve_media(type, filename):
    """Sert les fichiers depuis le dossier media"""
    
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs'
    }
    
    subdir = subdirs.get(type)
    if not subdir:
        abort(404)
    
    project_root = current_app.root_path
    media_dir = os.path.join(project_root, 'media', subdir)
    
    # Sécurité : vérifier que le fichier appartient à l'utilisateur
    if type == 'avatar' and not filename.startswith(f'avatar_{current_user.id}_'):
        abort(403)
    elif type == 'cover' and not filename.startswith(f'cover_{current_user.id}_'):
        abort(403)
    elif type == 'cv' and not filename.startswith(f'cv_{current_user.id}_'):
        abort(403)
    
    return send_from_directory(media_dir, filename)

# --- ROUTES D'INITIALISATION ---

@admin_bp.route('/init-folders')
def init_folders():
    """Crée les dossiers nécessaires s'ils n'existent pas"""
    try:
        upload_path = get_upload_path()
        static_path = get_static_path()
        
        if not os.path.exists(static_path):
            os.makedirs(static_path, exist_ok=True)
        
        default_avatar = os.path.join(get_static_path(), 'default-avatar.jpg')
        default_cover = os.path.join(get_static_path(), 'default-cover.jpg')
        
        if not os.path.exists(default_avatar):
            with open(default_avatar, 'w') as f:
                f.write("Default avatar image placeholder")
        
        if not os.path.exists(default_cover):
            with open(default_cover, 'w') as f:
                f.write("Default cover image placeholder")
        
        return f"Dossiers initialisés avec succès!<br>Uploads: {upload_path}<br>Static: {static_path}"
    
    except Exception as e:
        return f"Erreur lors de l'initialisation: {str(e)}"

@admin_bp.route('/init-media-folders')
def init_media_folders():
    """Crée la structure media/ à la racine du projet"""
    try:
        project_root = current_app.root_path
        media_path = os.path.join(project_root, 'media')
        
        subdirs = ['profiles', 'covers', 'docs']
        
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
        </ul>
        <p><a href="{url_for('admin.edit_profile')}">Retour à l'édition du profil</a></p>
        '''
    
    except Exception as e:
        return f"Erreur lors de la création de la structure media: {str(e)}"

# --- ROUTES PORTFOLIO ---

@admin_bp.route('/portfolio/edit', methods=['GET', 'POST'])
@login_required
def edit_portfolio_content():
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

    return render_template('edit_portfolio.html', config=config)

# --- ROUTES ABOUT ---

@admin_bp.route('/about/edit', methods=['GET', 'POST'])
@login_required
def about_edit():
    config = AboutPage.query.filter_by(utilisateur_id=current_user.id).first()
    
    if request.method == 'POST':
        if not config:
            config = AboutPage(utilisateur_id=current_user.id)
        
        # Traitement des fichiers
        upload_folder = os.path.join(current_app.root_path, 'media', 'about')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Hero image
        if 'hero_image' in request.files:
            file = request.files['hero_image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f"hero_{secrets.token_hex(8)}.{ext}"
                file.save(os.path.join(upload_folder, filename))
                config.hero_image = filename
        if request.form.get('hero_image_delete'):
            config.hero_image = None
        
        # Philosophie image
        if 'philosophie_image' in request.files:
            file = request.files['philosophie_image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f"philosophie_{secrets.token_hex(8)}.{ext}"
                file.save(os.path.join(upload_folder, filename))
                config.philosophie_image = filename
        if request.form.get('philosophie_image_delete'):
            config.philosophie_image = None
        
        # Parcours image
        if 'parcours_image' in request.files:
            file = request.files['parcours_image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f"parcours_{secrets.token_hex(8)}.{ext}"
                file.save(os.path.join(upload_folder, filename))
                config.parcours_image = filename
        if request.form.get('parcours_image_delete'):
            config.parcours_image = None
        
        # Competences image
        if 'competences_image' in request.files:
            file = request.files['competences_image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f"competences_{secrets.token_hex(8)}.{ext}"
                file.save(os.path.join(upload_folder, filename))
                config.competences_image = filename
        if request.form.get('competences_image_delete'):
            config.competences_image = None
        
        # Certifications image
        if 'certifications_image' in request.files:
            file = request.files['certifications_image']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                filename = f"certifications_{secrets.token_hex(8)}.{ext}"
                file.save(os.path.join(upload_folder, filename))
                config.certifications_image = filename
        if request.form.get('certifications_image_delete'):
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
    
    return render_template('about_edit.html', config=config)

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