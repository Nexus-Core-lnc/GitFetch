import os
import requests
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# Importation des modèles (le chemin sys.path est géré dans __init__.py)
from models import db, Projet, Utilisateur

admin_bp = Blueprint('admin', __name__)

# --- CONFIGURATION DES UPLOADS ---
def get_upload_path():
    """Retourne le chemin absolu vers le dossier uploads et le crée s'il n'existe pas"""
    # Chemin absolu vers static/uploads
    upload_path = os.path.join(current_app.root_path, '..', 'static', 'uploads')
    
    # Créer le dossier s'il n'existe pas
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    
    return upload_path

def get_static_path():
    """Retourne le chemin absolu vers le dossier static"""
    return os.path.join(current_app.root_path, '..', 'static')

def save_uploaded_file(file, prefix, user_id, allowed_extensions=None):
    """
    Sauvegarde un fichier uploadé avec nom sécurisé
    Retourne le nom du fichier ou None en cas d'erreur
    """
    if not file or not file.filename:
        return None
    
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Vérifier l'extension
    filename = secure_filename(file.filename)
    if '.' not in filename:
        return None
    
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return None
    
    # Créer un nom unique avec timestamp
    timestamp = int(datetime.utcnow().timestamp())
    unique_filename = f"{prefix}_{user_id}_{timestamp}.{extension}"
    
    # Obtenir le chemin de sauvegarde
    upload_dir = get_upload_path()
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        file.save(file_path)
        return unique_filename
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier: {e}")
        return None

# --- ROUTES ---

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
    # 1. Récupération des projets déjà en Base de Données
    # Ils sont accessibles via current_user.projets grâce à la relation backref
    
    # 2. Récupération des dépôts distants sur GitHub
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


@admin_bp.route('/import-repo/<int:github_id>', methods=['POST'])
@login_required
def import_repo(github_id):
    """Importe un dépôt GitHub vers la base de données PostgreSQL"""
    repo_name = request.form.get('repo_name')
    repo_desc = request.form.get('repo_desc')
    repo_url = request.form.get('repo_url')

    # Vérification si le projet existe déjà pour cet utilisateur
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
            # Mise à jour des textes
            projet.nom = request.form.get('nom')
            projet.description = request.form.get('description')
            projet.demo_url = request.form.get('demo_url')
            projet.structure_nom = request.form.get('structure_nom')
            
            # Checkbox : True si coché, False sinon
            est_collab = request.form.get('est_collaboration')
            projet.est_collaboration = est_collab == '1' if est_collab else False

            # Gestion de l'image de couverture (File Upload)
            file = request.files.get('image_file')
            if file and file.filename:
                new_filename = save_uploaded_file(file, 'proj', projet.id)
                if new_filename:
                    # Supprimer l'ancienne image si elle existe
                    if projet.image_couverture:
                        old_file = os.path.join(get_upload_path(), projet.image_couverture)
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass  # Ignorer les erreurs de suppression
                    
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
    
    # Supprimer le fichier image du serveur s'il existe
    if projet.image_couverture:
        old_file = os.path.join(get_upload_path(), projet.image_couverture)
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
    # current_user.projets contient déjà la liste grâce à la relation SQLAlchemy
    return render_template('list_repos.html')


@admin_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Modifie le profil de l'utilisateur"""
    if request.method == 'POST':
        try:
            # ... autres mises à jour ...
            
            # Avatar
            avatar_file = request.files.get('avatar')
            if avatar_file and avatar_file.filename:
                new_avatar = save_uploaded_file(avatar_file, 'avatar', current_user.id)
                if new_avatar:
                    # Supprimer l'ancien avatar seulement s'il n'est pas l'image par défaut
                    if (current_user.photo_profil and 
                        current_user.photo_profil != 'default-avatar.jpg' and
                        not current_user.photo_profil.startswith('avatar_')):
                        old_file = os.path.join(get_upload_path(), current_user.photo_profil)
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass
                    
                    current_user.photo_profil = new_avatar
                else:
                    flash("Format de fichier non supporté pour l'avatar. Utilisez PNG, JPG ou GIF.", "warning")
            
            # Photo de couverture
            cover_file = request.files.get('cover')
            if cover_file and cover_file.filename:
                new_cover = save_uploaded_file(cover_file, 'cover', current_user.id)
                if new_cover:
                    # Supprimer l'ancienne couverture seulement si elle n'est pas l'image par défaut
                    if (current_user.photo_couverture and 
                        current_user.photo_couverture != 'default-cover.jpg' and
                        not current_user.photo_couverture.startswith('cover_')):
                        old_file = os.path.join(get_upload_path(), current_user.photo_couverture)
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass
                    
                    current_user.photo_couverture = new_cover
                else:
                    flash("Format de fichier non supporté pour la couverture. Utilisez PNG, JPG ou GIF.", "warning")
            
            db.session.commit()
            flash('Profil mis à jour avec succès!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour du profil: {str(e)}', 'danger')
        
        return redirect(url_for('admin.edit_profile'))
    
    # GET request - afficher le formulaire
    return render_template('edit_profile.html')

@admin_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Route pour servir les fichiers uploadés"""
    return send_from_directory(get_upload_path(), filename)


# Route pour créer les dossiers manquants (utile pour le développement)
@admin_bp.route('/init-folders')
def init_folders():
    """Crée les dossiers nécessaires s'ils n'existent pas"""
    try:
        # Créer le dossier uploads
        upload_path = get_upload_path()
        
        # Créer le dossier static s'il n'existe pas
        static_path = get_static_path()
        if not os.path.exists(static_path):
            os.makedirs(static_path, exist_ok=True)
        
        # Créer des images par défaut si elles n'existent pas
        default_avatar = os.path.join(get_static_path(), 'default-avatar.jpg')
        default_cover = os.path.join(get_static_path(), 'default-cover.jpg')
        
        if not os.path.exists(default_avatar):
            # Créer un fichier texte temporaire (à remplacer par de vraies images)
            with open(default_avatar, 'w') as f:
                f.write("Default avatar image placeholder")
        
        if not os.path.exists(default_cover):
            with open(default_cover, 'w') as f:
                f.write("Default cover image placeholder")
        
        return f"Dossiers initialisés avec succès!<br>Uploads: {upload_path}<br>Static: {static_path}"
    
    except Exception as e:
        return f"Erreur lors de l'initialisation: {str(e)}"