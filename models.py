from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Utilisateur(db.Model, UserMixin):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom_utilisateur = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    mot_de_passe_hache = db.Column(db.String(255), nullable=True)
    
    role = db.Column(db.String(20), default='user')
    jeton_github = db.Column(db.String(255), nullable=True)
    
    # ✅ AJOUTER CETTE LIGNE ICI
    jeton_identification = db.Column(db.String(255), nullable=True)  # Jeton unique pour l'identification
    
    # Photos de profil et couverture
    photo_profil = db.Column(db.String(255), nullable=True, default='default-avatar.jpg')
    photo_couverture = db.Column(db.String(255), nullable=True, default='default-cover.jpg')
    
    # CV
    cv = db.Column(db.String(255)) 
    
    # Informations personnelles
    biographie = db.Column(db.Text, nullable=True)
    poste = db.Column(db.String(100), nullable=True)
    localisation = db.Column(db.String(100), nullable=True)
    site_web = db.Column(db.String(255), nullable=True)
    
    # Réseaux sociaux
    twitter = db.Column(db.String(100), nullable=True)
    linkedin = db.Column(db.String(100), nullable=True)
    github = db.Column(db.String(100), nullable=True)
    github_access_token = db.Column(db.String(255), nullable=True)
    
    # Numéros de téléphone
    telephone_principal = db.Column(db.String(20), nullable=True)
    telephone_mobile = db.Column(db.String(20), nullable=True)
    
    # Préférences
    theme_prefere = db.Column(db.String(20), default='light') 
    
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
    demo_url = db.Column(db.String(255))
    image_couverture = db.Column(db.String(255))
    logo_projet = db.Column(db.String(255))
    repo_id_github = db.Column(db.String(100), unique=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    est_collaboration = db.Column(db.Boolean, default=False)
    structure_nom = db.Column(db.String(100))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    technologies_annexes = db.Column(db.JSON, default=list)
    
    def __repr__(self):
        return f'<Projet {self.nom}>'
    
    
class PortfolioConfig(db.Model):
    __tablename__ = 'portfolio_config'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    
    # SECTION HERO
    hero_titre = db.Column(db.String(200), default="CONSTRUIRE LE FUTUR DU CODE")
    
    # SECTION ABOUT 
    about_titre = db.Column(db.String(200), default="Spécialiste IT multi-domaines")
    about_soustitre = db.Column(db.String(200), default="Précision. Performance. Innovation.")
    about_description = db.Column(db.Text)
    about_lien_texte = db.Column(db.String(100), default="EN SAVOIR PLUS SUR MON PARCOURS")
    
    # SKILLS ITEMS
    about_skills_json = db.Column(db.JSON, default=list)
    
    # STACK TECHNIQUE (React, Python...)
    tech_stack_json = db.Column(db.JSON, default=list)
    
    # TITRES DE SECTIONS
    projects_titre = db.Column(db.String(200), default="PROJETS RÉCENTS")
    cta_titre = db.Column(db.String(200), default="PRÊT À LANCER VOTRE PROCHAIN PROJET")
    
    # À ajouter dans admin/app/models.py

class AboutPage(db.Model):
    __tablename__ = 'about_pages'
    
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, nullable=False, index=True)
    
    # HERO SECTION
    hero_titre = db.Column(db.String(255), default="PLUS QU'UN DÉVELOPPEUR")
    hero_texte = db.Column(db.Text, default="Une passion pour l'innovation...")
    hero_image = db.Column(db.String(500), nullable=True)
    hero_bouton_1_texte = db.Column(db.String(100), default="Mon parcours")
    hero_bouton_1_lien = db.Column(db.String(255), default="#formation")
    hero_bouton_2_texte = db.Column(db.String(100), default="Échanger ensemble")
    hero_bouton_2_lien = db.Column(db.String(255), default="#contact")
    
    # PHILOSOPHY SECTION
    philosophie_titre = db.Column(db.String(255), default="MA PHILOSOPHIE")
    philosophie_sous_titre = db.Column(db.String(255), default="L'humain au centre de la technologie")
    philosophie_description_1 = db.Column(db.Text, default="...")
    philosophie_description_2 = db.Column(db.Text, default="...")
    philosophie_image = db.Column(db.String(500), nullable=True)
    
    # PARCOURS SECTION
    parcours_image = db.Column(db.String(500), nullable=True)
    
    # COMPETENCES SECTION
    competences_titre = db.Column(db.String(255), default="COMPÉTENCES CLÉS")
    competences_sous_titre = db.Column(db.String(255), default="...")
    competences_image = db.Column(db.String(500), nullable=True)
    
    # CERTIFICATIONS SECTION
    certifications_titre = db.Column(db.String(255), default="CERTIFICATIONS RECONNUES")
    certifications_sous_titre = db.Column(db.String(255), default="...")
    certifications_image = db.Column(db.String(500), nullable=True)
    
    # JSON FIELDS
    values_json = db.Column(db.JSON, default=list)
    parcours_json = db.Column(db.JSON, default=list)
    competences_json = db.Column(db.JSON, default=list)
    certifications_json = db.Column(db.JSON, default=list)
    
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)