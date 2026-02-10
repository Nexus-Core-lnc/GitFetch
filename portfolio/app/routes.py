import os
from flask import Blueprint, render_template, abort
from models import db, Projet, Utilisateur

# On définit le blueprint pour le portfolio
portfolio_bp = Blueprint('portfolio', __name__)

# --- UTILS ---

def get_common_context():
    """
    Fonction utilitaire pour récupérer les données communes à toutes les pages.
    Évite de répéter ce code dans chaque route.
    """
    user = Utilisateur.query.first()  # On récupère le propriétaire du portfolio
    
    # URLs des micro-services (Admin et Auth)
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return {
        'user': user,
        'auth_url': auth_url,
        'admin_url': admin_url
    }

# --- ROUTES ---

@portfolio_bp.route('/')
@portfolio_bp.route('/portfolio')
def home():
    """Page d'accueil du portfolio"""
    context = get_common_context()
    
    if not context['user']:
        return "Aucun profil configuré dans la base de données.", 404
        
    # On peut récupérer les 3 derniers projets pour la section "Featured" de l'accueil
    projets_recents = Projet.query.filter_by(utilisateur_id=context['user'].id)\
                                  .order_by(Projet.id.desc())\
                                  .limit(3).all()
    
    return render_template('portfolio.html', projets=projets_recents, **context)

@portfolio_bp.route('/me_connaitre')
def me_connaitre():
    """Page de présentation détaillée (À propos)"""
    context = get_common_context()
    if not context['user']:
        abort(404)
        
    return render_template('me_connaitre.html', **context)

@portfolio_bp.route('/projets')
def projets_liste():
    """Page affichant l'intégralité des projets réalisés"""
    context = get_common_context()
    if not context['user']:
        abort(404)
    
    # On récupère TOUS les projets de l'utilisateur
    tous_les_projets = Projet.query.filter_by(utilisateur_id=context['user'].id)\
                                   .order_by(Projet.id.desc()).all()
    
    return render_template('projet.html', 
                           projets=tous_les_projets, 
                           **context)

@portfolio_bp.route('/contact')
def contact():
    """Page de contact"""
    context = get_common_context()
    if not context['user']:
        abort(404)
        
    return render_template('contact.html', **context)