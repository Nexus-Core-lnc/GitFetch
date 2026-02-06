from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

from django.contrib.auth.models import AbstractUser
from django.db import models

class Utilisateur(AbstractUser):
    # Roles possibles
    CHOIX_ROLES = [
        ('admin', 'Administrateur'),
        ('user', 'Utilisateur'),
    ]
    
    # Ajout des champs personnalises
    role = models.CharField(max_length=20, choices=CHOIX_ROLES, default='user')
    jeton_github = models.CharField(max_length=255, blank=True, null=True)
    logo_profil = models.CharField(max_length=255, blank=True, null=True)
    biographie = models.TextField(blank=True, null=True)
    est_confirme = models.BooleanField(default=False)
    date_confirmation = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.username
    
    
class Projet(db.Model):
    __tablename__ = 'projets'

    id = db.Column(db.Integer, primary_key=True)
    id_depot_github = db.Column(db.BigInteger, unique=True) # ID unique de l'API GitHub
    
    # Infos éditables dans le dashboard
    titre_personnalise = db.Column(db.String(150))
    description_personnalisee = db.Column(db.Text)
    annee_creation = db.Column(db.Integer)
    url_depot = db.Column(db.String(255))
    
    # Exemple : ["Python", "Flask"]
    technologies = db.Column(db.JSON) 
    
    collaborateurs_et_orgs = db.Column(db.JSON)
    
    est_visible = db.Column(db.Boolean, default=True)
    
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)

    def __repr__(self):
        return f'<Projet {self.titre_personnalise}>'