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
    logo_profil = db.Column(db.String(255), nullable=True)
    biographie = db.Column(db.Text, nullable=True)
    
    est_confirme = db.Column(db.Boolean, default=False)
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    projets = db.relationship('Projet', backref='proprietaire', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Utilisateur {self.email}>'

class Projet(db.Model):
    __tablename__ = 'projets'

    id = db.Column(db.Integer, primary_key=True)
    id_depot_github = db.Column(db.BigInteger, unique=True)
    
    titre_personnalise = db.Column(db.String(150))
    description_personnalisee = db.Column(db.Text)
    annee_creation = db.Column(db.Integer)
    url_depot = db.Column(db.String(255))
    
    technologies = db.Column(db.JSON) 
    collaborateurs_et_orgs = db.Column(db.JSON)
    
    est_visible = db.Column(db.Boolean, default=True)
    
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)

    def __repr__(self):
        return f'<Projet {self.titre_personnalise}>'