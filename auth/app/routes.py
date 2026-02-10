import os
from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app
from . import mail, oauth 
from models import db, Utilisateur
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

main_bp = Blueprint('main', __name__)

# URL du micro-service Admin récupérée depuis le .env
admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')

# --- FONCTIONS UTILITAIRES ---

def generer_jeton(email, salt):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt=salt)

def verifier_jeton(token, salt, expiration=3600):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serialiseur.loads(token, salt=salt, max_age=expiration)
    except:
        return None

def envoyer_email(destinataire, sujet, template, **kwargs):
    msg = Message(
        sujet,
        recipients=[destinataire],
        sender=current_app.config.get('MAIL_DEFAULT_SENDER')
    )
    msg.html = render_template(template, **kwargs)
    mail.send(msg)

# --- ROUTES DE NAVIGATION ---

@main_bp.route("/")
def index():
    return render_template('index.html')

# --- INSCRIPTION ET CONFIRMATION ---

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if Utilisateur.query.filter_by(email=email).first():
            flash("Cette adresse email est déjà enregistrée.", "danger")
            return redirect(url_for('main.login'))

        nouvel_utilisateur = Utilisateur(
            email=email,
            nom_utilisateur=email.split('@')[0],
            mot_de_passe_hache=generate_password_hash(password),
            est_confirme=False
        )

        db.session.add(nouvel_utilisateur)
        db.session.commit()

        token = generer_jeton(email, 'email-confirm-salt')
        lien = url_for('main.confirmer_email', token=token, _external=True)
        envoyer_email(email, "Confirmez votre compte GitFetch", 'email_confirmation.html', confirm_url=lien)

        flash("Compte créé ! Vérifiez votre boîte mail pour confirmer.", "success")
        return redirect(url_for('main.login'))

    return render_template("register.html")

@main_bp.route("/confirm/<token>")
def confirmer_email(token):
    email = verifier_jeton(token, 'email-confirm-salt')
    if not email:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('main.register'))

    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()
    if not utilisateur.est_confirme:
        utilisateur.est_confirme = True
        db.session.commit()
        flash("Email validé ! Vous pouvez vous connecter.", "success")
    
    return redirect(url_for('main.login'))

# --- CONNEXION CLASSIQUE ---

@main_bp.route("/connexion", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Utilisateur.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.mot_de_passe_hache, password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return redirect(url_for('main.login'))

        if not user.est_confirme:
            flash('Veuillez confirmer votre email avant de vous connecter.', 'warning')
            return redirect(url_for('main.login'))

        login_user(user, remember=remember)
        return redirect(f"{admin_url}/dashboard")

    return render_template("login.html")

@main_bp.route("/deconnexion")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('main.index'))

# --- MOT DE PASSE OUBLIÉ ---

@main_bp.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user:
            token = generer_jeton(email, 'recover-password-salt')
            recover_url = url_for('main.reset_password', token=token, _external=True)
            envoyer_email(email, "Réinitialisation de mot de passe", 'email_reset.html', recover_url=recover_url)
            
        flash("Si cet email existe, un lien a été envoyé.", "info")
        return redirect(url_for('main.login'))
        
    return render_template("forgot_password.html")

@main_bp.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    email = verifier_jeton(token, 'recover-password-salt', expiration=1800)
    if not email:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('newPassword')
        user = Utilisateur.query.filter_by(email=email).first_or_404()
        user.mot_de_passe_hache = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Mot de passe mis à jour !", "success")
        return redirect(url_for('main.login'))
        
    return render_template("reset_password.html", token=token)

# --- AUTHENTICATION SOCIALE (OAUTH) ---

@main_bp.route('/login/<name>')
def social_login(name):
    client = oauth.create_client(name)
    redirect_uri = url_for('main.auth_callback', name=name, _external=True)
    return client.authorize_redirect(redirect_uri)

@main_bp.route('/auth/<name>')
def auth_callback(name):
    client = oauth.create_client(name)
    token = client.authorize_access_token()
    access_token = token.get('access_token')
    
    # 1. Récupération des infos selon le provider
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
            email = next(e['email'] for e in emails if e['primary'])
        pseudo = user_info.get('login')
        avatar = user_info.get('avatar_url')

    # 2. Gestion de l'utilisateur en DB
    user = Utilisateur.query.filter_by(email=email).first()
    if not user:
        user = Utilisateur(email=email, nom_utilisateur=pseudo, est_confirme=True, mot_de_passe_hache=None)
        db.session.add(user)

    # 3. MISE À JOUR AUTOMATIQUE DU JETON ET AVATAR
    if name == 'github':
        user.jeton_github = access_token
    user.logo_profil = avatar
    
    db.session.commit()
    
    # 4. Connexion et Redirection vers ADMIN
    login_user(user)
    flash(f"Bienvenue {user.nom_utilisateur} !", "success")
    return redirect(f"{admin_url}/dashboard")