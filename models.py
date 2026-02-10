from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Correction : nullable=True pour permettre la connexion OAuth
    mot_de_passe_hache = db.Column(db.String(255), nullable=True)
    
    role = db.Column(db.String(20), default='user')
    jeton_github = db.Column(db.String(255), nullable=True)
    
    # Photos de profil et couverture
    photo_profil = db.Column(db.String(255), nullable=True, default='default-avatar.jpg')
    photo_couverture = db.Column(db.String(255), nullable=True, default='default-cover.jpg')
    
    # CV
    cv = db.Column(db.String(255)) 
    
    # Informations personnelles
    biographie = db.Column(db.Text, nullable=True)
    poste = db.Column(db.String(100), nullable=True)  # Ex: "Développeur Full Stack"
    localisation = db.Column(db.String(100), nullable=True)
    site_web = db.Column(db.String(255), nullable=True)
    
    # Réseaux sociaux
    twitter = db.Column(db.String(100), nullable=True)
    linkedin = db.Column(db.String(100), nullable=True)
    github = db.Column(db.String(100), nullable=True)
    
    # Numéros de téléphone
    telephone_principal = db.Column(db.String(20), nullable=True)
    telephone_mobile = db.Column(db.String(20), nullable=True)
    
    # Préférences
    theme_prefere = db.Column(db.String(20), default='light')  # 'light' ou 'dark'
    
    # Statut
    est_confirme = db.Column(db.Boolean, default=False)
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projets = db.relationship('Projet', backref='proprietaire', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Utilisateur {self.email}>'

class Projet(db.Model):
    __tablename__ = 'projets'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    github_url = db.Column(db.String(255))
    demo_url = db.Column(db.String(255)) # URL en ligne
    image_couverture = db.Column(db.String(255)) # URL de l'image
    logo_projet = db.Column(db.String(255)) # Petit logo
    repo_id_github = db.Column(db.String(100), unique=True) # Pour éviter les doublons
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    est_collaboration = db.Column(db.Boolean, default=False) # Collaboration ou compte propre
    structure_nom = db.Column(db.String(100)) # Nom de la structure
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Projet {self.nom}>'