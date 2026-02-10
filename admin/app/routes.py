import os
import requests
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from models import db, Projet, Utilisateur

admin_bp = Blueprint('admin', __name__)

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


from flask import send_from_directory, current_app
import os

import os
from flask import send_from_directory, current_app

@admin_bp.route('/serve-static/media/profiles/<filename>')
def serve_profile_pic(filename):
    media_path = os.path.join(current_app.root_path, 'media', 'profiles')
    return send_from_directory(media_path, filename)


@admin_bp.route('/serve-static/media/docs/<filename>')
def serve_cv(filename):
    docs_path = os.path.join(current_app.root_path, 'media', 'docs')
    # as_attachment=True force le navigateur à télécharger le fichier
    return send_from_directory(docs_path, filename, as_attachment=True)
# --- ROUTES PRINCIPALES ---

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
    return render_template('list_repos.html')

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
            projet.nom = request.form.get('nom')
            projet.description = request.form.get('description')
            projet.demo_url = request.form.get('demo_url')
            projet.structure_nom = request.form.get('structure_nom')
            
            est_collab = request.form.get('est_collaboration')
            projet.est_collaboration = est_collab == '1' if est_collab else False

            file = request.files.get('image_file')
            if file and file.filename:
                new_filename = save_uploaded_file(file, 'proj', projet.id)
                if new_filename:
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

    return render_template('edit_project.html', projet=projet)

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

# --- ROUTES DE SERVICE DE FICHIERS ---

@admin_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Route pour servir les fichiers uploadés"""
    return send_from_directory(get_upload_path(), filename)

@admin_bp.route('/serve-static/<path:filename>')
def serve_root_static(filename):
    """Envoie les fichiers depuis le dossier static racine"""
    root_static = get_static_path()
    return send_from_directory(root_static, filename)

# --- ROUTE D'INITIALISATION (développement) ---

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

@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Gère l'édition du profil utilisateur avec une structure media/ à la racine du projet.
    Dossiers : media/profiles/, media/covers/, media/docs/
    """
    
    def get_media_path(subdir=''):
        """Retourne le chemin absolu vers le dossier media et le crée s'il n'existe pas"""
        # Chemin absolu vers media/ à la racine du projet Flask
        project_root = current_app.root_path
        media_path = os.path.join(project_root, 'media')
        
        if subdir:
            media_path = os.path.join(media_path, subdir)
        
        # Créer le dossier s'il n'existe pas
        if not os.path.exists(media_path):
            os.makedirs(media_path, exist_ok=True)
        
        return media_path
    
    def get_media_url(filename, type_file):
        """Retourne l'URL pour servir les fichiers depuis le dossier media"""
        # Pour servir depuis media/ via une route spéciale
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
        
        # Obtenir le chemin du dossier
        media_dir = get_media_path(subdir)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_ext = os.path.splitext(file.filename)[1] if '.' in file.filename else ''
        filename = f"{type_file}_{user_id}_{timestamp}{original_ext}"
        
        # Sécuriser le nom de fichier
        filename = secure_filename(filename)
        
        # Sauvegarder le fichier
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
            
            # === 2. RÉSEAUX SOCIAUX ===
            current_user.github = request.form.get('github', current_user.github)
            current_user.linkedin = request.form.get('linkedin', current_user.linkedin)
            current_user.twitter = request.form.get('twitter', current_user.twitter)
            
            # === 3. TOKEN GITHUB (privé) ===
            new_token = request.form.get('jeton_github', '').strip()
            if new_token:
                current_user.jeton_github = new_token
                flash('Token GitHub mis à jour', 'info')
            
            # === 4. THÈME ===
            current_user.theme_prefere = request.form.get('theme_prefere', current_user.theme_prefere)
            
            # === 5. GESTION DE L'AVATAR ===
            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename:
                # Validation du type de fichier
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(avatar_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_avatar = save_media_file(avatar_file, 'avatar', current_user.id)
                    if new_avatar:
                        # Suppression de l'ancien fichier si différent du défaut
                        if (current_user.photo_profil and 
                            current_user.photo_profil != 'default-avatar.jpg'):
                            delete_media_file(current_user.photo_profil, 'avatar')
                        
                        current_user.photo_profil = new_avatar
                        flash('Avatar mis à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour l\'avatar. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            # === 6. GESTION DE LA PHOTO DE COUVERTURE ===
            cover_file = request.files.get('cover')
            if cover_file and cover_file.filename:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(cover_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    new_cover = save_media_file(cover_file, 'cover', current_user.id)
                    if new_cover:
                        # Suppression de l'ancien fichier si différent du défaut
                        if (current_user.photo_couverture and 
                            current_user.photo_couverture != 'default-cover.jpg'):
                            delete_media_file(current_user.photo_couverture, 'cover')
                        
                        current_user.photo_couverture = new_cover
                        flash('Photo de couverture mise à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour la couverture. Utilisez PNG, JPG, JPEG, GIF ou WEBP.', 'warning')
            
            # === 7. GESTION DU CV (PDF) ===
            cv_file = request.files.get('cv')
            if cv_file and cv_file.filename:
                allowed_extensions = {'pdf', 'doc', 'docx'}
                filename = secure_filename(cv_file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Vérification de la taille (5 Mo max)
                    cv_file.seek(0, os.SEEK_END)
                    file_size = cv_file.tell()
                    cv_file.seek(0)
                    
                    if file_size > 5 * 1024 * 1024:
                        flash('Le fichier CV est trop volumineux. Taille maximale : 5 Mo.', 'warning')
                    else:
                        new_cv = save_media_file(cv_file, 'cv', current_user.id)
                        if new_cv:
                            # Suppression de l'ancien fichier s'il existe
                            if current_user.cv:
                                delete_media_file(current_user.cv, 'cv')
                            
                            current_user.cv = new_cv
                            flash('CV mis à jour avec succès', 'success')
                else:
                    flash('Format de fichier non supporté pour le CV. Utilisez PDF, DOC ou DOCX.', 'warning')
            
            # === 8. SAUVEGARDE EN BASE DE DONNÉES ===
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil : {str(e)}', 'danger')
        
        return redirect(url_for('admin.edit_profile'))
    
    # Pour le template, on peut passer les URLs des médias
    # Ces fonctions seront utilisées dans le template pour afficher les images
    return render_template('edit_profile.html')


# Route pour servir les fichiers depuis le dossier media
@admin_bp.route('/media/<type>/<filename>')
@login_required
def serve_media(type, filename):
    """Sert les fichiers depuis le dossier media"""
    
    # Mapping des types vers les sous-dossiers
    subdirs = {
        'avatar': 'profiles',
        'cover': 'covers',
        'cv': 'docs'
    }
    
    subdir = subdirs.get(type)
    if not subdir:
        abort(404)
    
    # Chemin vers le dossier media
    project_root = current_app.root_path
    media_dir = os.path.join(project_root, 'media', subdir)
    
    # Vérifier que le fichier existe et appartient à l'utilisateur
    # (sécurité : vérifier que le fichier commence par le bon pattern)
    if type == 'avatar' and not filename.startswith(f'avatar_{current_user.id}_'):
        abort(403)
    elif type == 'cover' and not filename.startswith(f'cover_{current_user.id}_'):
        abort(403)
    elif type == 'cv' and not filename.startswith(f'cv_{current_user.id}_'):
        abort(403)
    
    return send_from_directory(media_dir, filename)


# Route utilitaire pour initialiser la structure media
@admin_bp.route('/init-media-folders')
def init_media_folders():
    """Crée la structure media/ à la racine du projet"""
    try:
        project_root = current_app.root_path
        media_path = os.path.join(project_root, 'media')
        
        # Créer les sous-dossiers
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
        <p><a href="{{ url_for('admin.edit_profile') }}">Retour à l'édition du profil</a></p>
        '''
    
    except Exception as e:
        return f"Erreur lors de la création de la structure media: {str(e)}"