import os
from flask import Blueprint, render_template, abort, send_from_directory
from models import db, Projet, Utilisateur, PortfolioConfig, AboutPage

# On définit le blueprint pour le portfolio
portfolio_bp = Blueprint('portfolio', __name__)

# --- UTILS ---

def get_common_context():
    """
    Fonction utilitaire pour récupérer les données communes à toutes les pages.
    Évite de répéter ce code dans chaque route.
    """
    user = Utilisateur.query.first()  # On récupère le propriérateur du portfolio
    
    # URLs des micro-services (Admin et Auth)
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return {
        'user': user,
        'auth_url': auth_url,
        'admin_url': admin_url
    }

# --- ROUTE MÉDIA UNIQUE ET GÉNÉRIQUE ---

@portfolio_bp.route('/media/<folder>/<path:filename>')
def serve_admin_media(folder, filename):
    """
    Route UNIQUE pour servir tous les médias depuis le service admin.
    Supporte les dossiers : about, profiles, projects, covers, etc.
    """
    # Chemin absolu vers le dossier media de l'admin
    base_dir = os.path.abspath(os.path.join(os.getcwd(), 'admin', 'app', 'media', folder))
    
    # Vérifier si le dossier existe
    if not os.path.exists(base_dir):
        print(f"ERREUR: Dossier introuvable - {base_dir}")
        # Fallback vers le dossier about par défaut
        default_dir = os.path.abspath(os.path.join(os.getcwd(), 'admin', 'app', 'media', 'about'))
        return send_from_directory(default_dir, 'default-about.jpg')
    
    try:
        return send_from_directory(base_dir, filename)
    except FileNotFoundError:
        print(f"ERREUR: Fichier introuvable - {os.path.join(base_dir, filename)}")
        # Fallback vers image par défaut selon le dossier
        if folder == 'about':
            default_file = 'default-about.jpg'
        elif folder == 'profiles':
            default_file = 'default-profile.jpg'
        elif folder == 'projects':
            default_file = 'default-project.jpg'
        elif folder == 'covers':
            default_file = 'default-cover.jpg'
        else:
            default_file = 'default-about.jpg'
        
        return send_from_directory(base_dir, default_file)

# --- ROUTES PRINCIPALES ---

@portfolio_bp.route('/')
def home():
    context = get_common_context()
    user = context.get('user')
    
    projets = []
    config = None
    if user:
        projets = Projet.query.filter_by(utilisateur_id=user.id).limit(3).all()
        config = PortfolioConfig.query.filter_by(utilisateur_id=user.id).first()

    return render_template(
        'portfolio.html', 
        projets=projets, 
        config=config, 
        **context
    )

@portfolio_bp.route('/me_connaitre')
def me_connaitre():
    """Page de présentation détaillée (À propos)"""
    context = get_common_context()
    if not context['user']:
        abort(404)
    
    about_config = AboutPage.query.filter_by(utilisateur_id=context['user'].id).first()
    
    return render_template('me_connaitre.html', about_config=about_config, **context)

@portfolio_bp.route('/projets')
def projets_liste():
    """Page affichant l'intégralité des projets réalisés"""
    context = get_common_context()
    if not context['user']:
        abort(404)
    
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