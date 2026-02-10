import os
import requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# Importation des modèles (le chemin sys.path est géré dans __init__.py)
from models import db, Projet, Utilisateur

admin_bp = Blueprint('admin', __name__)

# --- CONFIGURATION DES UPLOADS ---
# Les images sont stockées dans GitFetch/static/uploads
# On définit le chemin par rapport à la racine du projet
def get_upload_path():
    return os.path.join(current_app.root_path, '..', 'static', 'uploads')

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
        flash("Erreur lors de l'importation.", "danger")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/edit-project/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    """Modifie les informations d'un projet dans la base de données"""
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()

    if request.method == 'POST':
        # Mise à jour des textes
        projet.nom = request.form.get('nom')
        projet.description = request.form.get('description')
        projet.demo_url = request.form.get('demo_url')
        projet.structure_nom = request.form.get('structure_nom')
        # Checkbox : True si coché, False sinon
        projet.est_collaboration = True if request.form.get('est_collaboration') else False

        # Gestion de l'image de couverture (File Upload)
        file = request.files.get('image_file')
        if file and file.filename != '':
            # Sécurisation du nom de fichier
            filename = secure_filename(f"proj_{projet.id}_{file.filename}")
            
            # Création du dossier si inexistant
            upload_dir = get_upload_path()
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Sauvegarde physique
            file.save(os.path.join(upload_dir, filename))
            
            # Mise à jour du nom de fichier en base de données
            projet.image_couverture = filename

        try:
            db.session.commit()
            flash("Informations mises à jour avec succès !", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de l'enregistrement.", "danger")

    return render_template('edit_project.html', projet=projet)


@admin_bp.route('/delete-project/<int:id>', methods=['POST'])
@login_required
def delete_project(id):
    """Supprime un projet de la base de données (le retire du front-end)"""
    projet = Projet.query.filter_by(id=id, utilisateur_id=current_user.id).first_or_404()
    
    # Optionnel : Supprimer le fichier image du serveur s'il existe
    if projet.image_couverture:
        old_file = os.path.join(get_upload_path(), projet.image_couverture)
        if os.path.exists(old_file):
            os.remove(old_file)

    try:
        db.session.delete(projet)
        db.session.commit()
        flash("Projet supprimé de la base de données.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de la suppression.", "danger")

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/refresh-github', methods=['POST'])
@login_required
def refresh_repos():
    """Redirige simplement vers le dashboard pour forcer un appel API GitHub"""
    return redirect(url_for('admin.dashboard'))

# --- ROUTE POUR VOIR LES REPOS À IMPORTER (GitHub API) ---
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
        except Exception as e:
            flash(f"Erreur de connexion à GitHub", "danger")

    return render_template('import_repos.html', repos=repos)


# --- ROUTE POUR VOIR LES REPOS DÉJÀ IMPORTÉS (Base de données) ---
@admin_bp.route('/list-repos')
@login_required
def list_repos():
    """Affiche uniquement les projets déjà présents dans PostgreSQL"""
    # current_user.projets contient déjà la liste grâce à la relation SQLAlchemy
    return render_template('list_repos.html')