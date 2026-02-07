from flask import Blueprint, render_template
# On importe l'objet db qui a été défini dans le __init__.py du dossier courant
from . import db 
import os
admin_bp = Blueprint('admin', __name__)




@admin_bp.route('/dashboard')
def dashboard():
    # On récupère l'URL de l'auth depuis l'environnement
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    return render_template('dashboard.html', auth_url=auth_url)