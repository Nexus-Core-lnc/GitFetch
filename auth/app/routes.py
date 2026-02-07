from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app
# On ajoute 'oauth' dans l'import depuis le dossier parent
from . import db, mail, oauth 
from .models import Utilisateur
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

# Définition du blueprint
main_bp = Blueprint('main', __name__)

# --- FONCTIONS UTILITAIRES ---

def generer_jeton_confirmation(email):
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt='email-confirm-salt')

def envoyer_mail_confirmation(destinataire, lien_confirmation):
    msg = Message(
        "Confirmez votre compte GitFetch",
        recipients=[destinataire],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    msg.html = render_template('email_confirmation.html', confirm_url=lien_confirmation)
    mail.send(msg)

# --- ROUTES CLASSIQUES ---

@main_bp.route("/")
def index():
    return render_template('index.html')

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        utilisateur_existant = Utilisateur.query.filter_by(email=email).first()
        if utilisateur_existant:
            flash("Cette adresse email est déjà enregistrée.", "danger")
            return redirect(url_for('main.login'))

        pseudo_defaut = email.split('@')[0]
        nouvel_utilisateur = Utilisateur(
            email=email,
            nom_utilisateur=pseudo_defaut,
            mot_de_passe_hache=generate_password_hash(password),
            est_confirme=False
        )

        try:
            db.session.add(nouvel_utilisateur)
            db.session.commit()

            jeton = generer_jeton_confirmation(email)
            lien = url_for('main.confirmer_email', token=jeton, _external=True)
            envoyer_mail_confirmation(email, lien)

            flash("Compte créé ! Vérifiez votre boîte mail pour confirmer.", "success")
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de l'inscription. Réessayez plus tard.", "danger")
            print(f"Erreur inscription : {e}")

    return render_template("register.html")

@main_bp.route("/confirm/<token>")
def confirmer_email(token):
    try:
        serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serialiseur.loads(token, salt='email-confirm-salt', max_age=3600)
    except:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('main.register'))

    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()
    if not utilisateur.est_confirme:
        utilisateur.est_confirme = True
        db.session.commit()
        flash("Email validé ! Vous pouvez vous connecter.", "success")
    else:
        flash("Compte déjà confirmé.", "info")

    return redirect(url_for('main.login'))

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
        return redirect(url_for('main.dashboard'))

    return render_template("login.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)

@main_bp.route("/deconnexion")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# --- RÉINITIALISATION MOT DE PASSE ---

@main_bp.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt='recover-password-salt')
            recover_url = url_for('main.reset_password', token=token, _external=True)
            
            msg = Message(
                "Réinitialisation de votre mot de passe",
                recipients=[email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            msg.body = f"Cliquez sur ce lien pour changer votre mot de passe : {recover_url}"
            mail.send(msg)
            
        flash("Si cet email existe, un lien de réinitialisation a été envoyé.", "info")
        return redirect(url_for('main.login'))
        
    return render_template("forgot_password.html")

@main_bp.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='recover-password-salt', max_age=1800)
    except:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('newPassword')
        if not new_password:
            flash("Erreur : le nouveau mot de passe est manquant.", "danger")
            return render_template("reset_password.html", token=token)

        user = Utilisateur.query.filter_by(email=email).first_or_404()
        user.mot_de_passe_hache = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Ton mot de passe a été mis à jour avec succès !", "success")
        return redirect(url_for('main.login'))
        
    return render_template("reset_password.html", token=token)

# --- AUTHENTICATION SOCIALE (OAUTH) ---

@main_bp.route('/login/<name>')
def social_login(name):
    client = oauth.create_client(name)
    # _external=True est vital pour générer l'URL complète
    redirect_uri = url_for('main.auth_callback', name=name, _external=True)
    
    # DEBUG : Ajoute ce print pour voir ce que Flask envoie à Google
    print(f"DEBUG REDIRECT URI: {redirect_uri}")
    
    return client.authorize_redirect(redirect_uri)

@main_bp.route('/auth/<name>')
def auth_callback(name):
    client = oauth.create_client(name)
    token = client.authorize_access_token()
    
    # Gestion différenciée selon le fournisseur
    if name == 'google':
        user_info = client.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
        email = user_info.get('email')
        pseudo = user_info.get('name', email.split('@')[0])
    elif name == 'github':
        user_info = client.get('user').json()
        # GitHub cache souvent l'email, on fait une requête spécifique si besoin
        email = user_info.get('email')
        if not email:
            emails = client.get('user/emails').json()
            email = next(e['email'] for e in emails if e['primary'])
        pseudo = user_info.get('login')

    user = Utilisateur.query.filter_by(email=email).first()
    
    if not user:
        user = Utilisateur(
            email=email, 
            nom_utilisateur=pseudo, 
            est_confirme=True,
            # On laisse le mot de passe vide ou à None pour OAuth
            mot_de_passe_hache=None 
        )
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    flash(f"Connexion réussie avec {name.capitalize()} !", "success")
    return redirect(url_for('main.dashboard'))