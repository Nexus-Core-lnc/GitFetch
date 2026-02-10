import requests
import os
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required, login_user
from models import db, Utilisateur, Projet

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # 1. Vérification du jeton en base de données
    if not current_user.jeton_github:
        return render_template('authorize.html')

    # 2. Si le jeton existe, on récupère les dépôts via l'API GitHub
    repos = []
    headers = {
        'Authorization': f'token {current_user.jeton_github}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # URL MODIFIÉE : affiliation=owner,collaborator permet de voir tes repos ET ceux des autres
    github_url = (
        'https://api.github.com/user/repos'
        '?sort=updated'
        '&per_page=50'
        '&affiliation=owner,collaborator,organization_member'
    )
    
    try:
        response = requests.get(github_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            repos = response.json()
        elif response.status_code == 401:
            # Jeton expiré ou révoqué : on nettoie la base
            current_user.jeton_github = None
            db.session.commit()
            return render_template('authorize.html', error="Votre session GitHub a expiré. Veuillez vous reconnecter.")
            
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion à l'API GitHub : {e}")
        flash("Impossible de contacter GitHub pour le moment.", "danger")

    return render_template('dashboard.html', repos=repos)

@admin_bp.route('/login/github/authorize')
def github_authorize():
    # Note : Assure-toi que 'oauth' est bien importé depuis ton extension
    from . import oauth 
    
    try:
        token = oauth.github.authorize_access_token()
        access_token = token.get('access_token')

        # Récupération du profil pour identifier l'utilisateur
        resp = oauth.github.get('user')
        profile = resp.json()
        email = profile.get('email')

        # Si l'email est privé sur GitHub, on fait une requête secondaire
        if not email:
            emails = oauth.github.get('user/emails').json()
            email = next(e['email'] for e in emails if e['primary'])

        # Recherche de l'utilisateur
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur:
            # Mise à jour des infos et du jeton
            utilisateur.jeton_github = access_token
            utilisateur.logo_profil = profile.get('avatar_url')
            db.session.commit()
            
            # Connexion de l'utilisateur
            login_user(utilisateur)
            flash("Profil GitHub synchronisé !", "success")
            return redirect(url_for('admin.dashboard'))
        
        flash("Compte local introuvable. Veuillez vous inscrire d'abord.", "warning")
        return redirect("http://127.0.0.1:5001/connexion")

    except Exception as e:
        print(f"Erreur callback : {e}")
        flash("L'autorisation GitHub a échoué.", "danger")
        return redirect(url_for('admin.dashboard'))