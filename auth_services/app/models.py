from . import db
from datetime import datetime
from flask_login import UserMixin

class Utilisateur(db.Model,UserMixin):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mot_de_passe_hache = db.Column(db.String(255), nullable=False)
    
    # Rôles et Profil (Champs que tu avais dans Django, convertis pour Flask)
    role = db.Column(db.String(20), default='user')
    jeton_github = db.Column(db.String(255), nullable=True)
    logo_profil = db.Column(db.String(255), nullable=True)
    biographie = db.Column(db.Text, nullable=True)
    
    # Statut du compte
    est_confirme = db.Column(db.Boolean, default=False)
    date_confirmation = db.Column(db.DateTime, nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation : Un utilisateur peut avoir plusieurs projets
    projets = db.relationship('Projet', backref='proprietaire', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Utilisateur {self.email}>'

class Projet(db.Model):
    __tablename__ = 'projets'

    id = db.Column(db.Integer, primary_key=True)
    id_depot_github = db.Column(db.BigInteger, unique=True)
    
    # Infos éditables
    titre_personnalise = db.Column(db.String(150))
    description_personnalisee = db.Column(db.Text)
    annee_creation = db.Column(db.Integer)
    url_depot = db.Column(db.String(255))
    
    # Stockage JSON pour les technos et collaborateurs
    technologies = db.Column(db.JSON) 
    collaborateurs_et_orgs = db.Column(db.JSON)
    
    est_visible = db.Column(db.Boolean, default=True)
    
    # Clé étrangère vers l'utilisateur
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)

    def __repr__(self):
        return f'<Projet {self.titre_personnalise}>'