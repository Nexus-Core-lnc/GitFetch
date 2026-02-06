from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app
from . import db, mail
from .models import Utilisateur
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

# Je definis mon blueprint unique ici
main_bp = Blueprint('main', __name__)

# --- MES FONCTIONS UTILITAIRES ---

def generer_jeton_confirmation(email):
    # Je genere un jeton securise pour confirmer l'email
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt='email-confirm-salt')

def envoyer_mail_confirmation(destinataire, lien_confirmation):
    # Je prepare et j'envoie le mail de bienvenue
    msg = Message(
        "Confirmez votre compte GitFetch",
        recipients=[destinataire],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    msg.html = render_template('email_confirmation.html', confirm_url=lien_confirmation)
    mail.send(msg)

# --- MES ROUTES ---

@main_bp.route("/")
def index():
    # J'affiche ma page d'accueil
    return render_template('index.html')

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Je verifie si l'utilisateur existe deja
        utilisateur_existant = Utilisateur.query.filter_by(email=email).first()
        if utilisateur_existant:
            flash("Cette adresse email est deja enregistree.", "danger")
            return redirect(url_for('main.login'))

        # Je cree le nouvel utilisateur avec un mot de passe hache
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

            # Je lance la procedure d'envoi de mail
            jeton = generer_jeton_confirmation(email)
            lien = url_for('main.confirmer_email', token=jeton, _external=True)
            envoyer_mail_confirmation(email, lien)

            flash("Compte cree ! Verifiez votre boite mail pour confirmer.", "success")
            return redirect(url_for('main.login'))

        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de l'inscription. Reessayez plus tard.", "danger")
            print(f"Erreur inscription : {e}")

    return render_template("register.html")

@main_bp.route("/confirm/<token>")
def confirmer_email(token):
    # Je valide l'email de l'utilisateur via le jeton
    try:
        serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serialiseur.loads(token, salt='email-confirm-salt', max_age=3600)
    except:
        flash("Le lien est invalide ou a expire.", "danger")
        return redirect(url_for('main.register'))

    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()

    if utilisateur.est_confirme:
        flash("Compte deja confirme.", "info")
    else:
        utilisateur.est_confirme = True
        db.session.commit()
        flash("Email valide ! Vous pouvez vous connecter.", "success")

    return redirect(url_for('main.login'))

@main_bp.route("/connexion", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = Utilisateur.query.filter_by(email=email).first()

        # Je verifie l'identite et le mot de passe
        if not user or not check_password_hash(user.mot_de_passe_hache, password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return redirect(url_for('main.login'))

        # Je bloque la connexion si l'email n'est pas valide
        if not user.est_confirme:
            flash('Veuillez confirmer votre email avant.', 'warning')
            return redirect(url_for('main.login'))

        # Je connecte l'utilisateur et je cree la session
        login_user(user, remember=remember)
        return redirect(url_for('main.dashboard'))

    return render_template("login.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    # J'affiche le tableau de bord prive
    return render_template("dashboard.html", user=current_user)

@main_bp.route("/deconnexion")
@login_required
def logout():
    # Je ferme la session et je redirige
    logout_user()
    return redirect(url_for('main.index'))

@main_bp.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user:
            # Je genere un jeton specifique pour le reset
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt='recover-password-salt')
            
            # Je prepare le lien
            recover_url = url_for('main.reset_password', token=token, _external=True)
            
            # J'envoie le mail
            msg = Message(
                "Reinitialisation de votre mot de passe",
                recipients=[email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            msg.body = f"Cliquez sur ce lien pour changer votre mot de passe : {recover_url}"
            mail.send(msg)
            
        # Par securite, je ne dis pas si l'email existe ou non
        flash("Si cet email existe, un lien de reinitialisation a ete envoye.", "info")
        return redirect(url_for('main.login'))
        
    return render_template("forgot_password.html")

@main_bp.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='recover-password-salt', max_age=1800)
    except:
        flash("Le lien est invalide ou a expire.", "danger")
        return redirect(url_for('main.forgot_password'))
        
    if request.method == 'POST':
        # ATTENTION ICI : Je change 'password' par 'newPassword' pour coller a ton HTML
        new_password = request.form.get('newPassword')
        
        # Je verifie aussi le code si tu veux vraiment l'utiliser, 
        # mais pour l'instant je me concentre sur le mot de passe
        if not new_password:
            flash("Erreur : le nouveau mot de passe est manquant.", "danger")
            return render_template("reset_password.html", token=token)

        user = Utilisateur.query.filter_by(email=email).first_or_404()
        
        # Je hache et je sauvegarde
        user.mot_de_passe_hache = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Ton mot de passe a ete mis a jour avec succes !", "success")
        return redirect(url_for('main.login'))
        
    return render_template("reset_password.html", token=token)