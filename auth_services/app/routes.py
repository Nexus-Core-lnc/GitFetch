from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app
from . import db, mail
from .models import Utilisateur
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

main_bp = Blueprint('main', __name__)

# --- FONCTIONS UTILITAIRES ---

def generer_jeton_confirmation(email):
    """Génère un jeton sécurisé pour la confirmation par mail."""
    serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serialiseur.dumps(email, salt='email-confirm-salt')

def envoyer_mail_confirmation(destinataire, lien_confirmation):
    """Envoie le mail de bienvenue avec le lien de validation."""
    msg = Message(
        "Confirmez votre compte GitFetch",
        recipients=[destinataire],
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    msg.html = render_template('auth/email_confirmation.html', confirm_url=lien_confirmation)
    mail.send(msg)

# --- ROUTES ---

@main_bp.route("/")
def index():
    return render_template('index.html')

@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Vérification si l'utilisateur existe déjà
        utilisateur_existant = Utilisateur.query.filter_by(email=email).first()
        if utilisateur_existant:
            flash("Cette adresse email est déjà enregistrée.", "danger")
            return redirect(url_for('main.register'))

        # 2. Création de l'utilisateur
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

            # 3. Envoi du mail de confirmation
            jeton = generer_jeton_confirmation(email)
            lien = url_for('main.confirmer_email', token=jeton, _external=True)
            envoyer_mail_confirmation(email, lien)

            flash("Compte créé ! Veuillez vérifier votre boîte mail pour confirmer votre inscription.", "success")
            return redirect(url_for('main.login'))

        except Exception as e:
            db.session.rollback()
            flash("Une erreur est survenue lors de l'inscription. Réessayez plus tard.", "danger")
            print(f"Erreur inscription : {e}")

    return render_template("auth/register.html")

@main_bp.route("/confirm/<token>")
def confirmer_email(token):
    """Route appelée lorsque l'utilisateur clique sur le lien dans son mail."""
    try:
        serialiseur = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serialiseur.loads(token, salt='email-confirm-salt', max_age=3600)
    except:
        flash("Le lien de confirmation est invalide ou a expiré.", "danger")
        return redirect(url_for('main.register'))

    utilisateur = Utilisateur.query.filter_by(email=email).first_or_404()

    if utilisateur.est_confirme:
        flash("Votre compte est déjà confirmé. Vous pouvez vous connecter.", "info")
    else:
        utilisateur.est_confirme = True
        db.session.commit()
        flash("Merci ! Votre adresse email a été validée. Vous pouvez maintenant vous connecter.", "success")

    return redirect(url_for('main.login'))

@main_bp.route("/connexion")
def login():
    return render_template("auth/login.html")