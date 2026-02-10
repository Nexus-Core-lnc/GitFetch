import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory
from flask_migrate import Migrate
from dotenv import load_dotenv

# 1. Définition des chemins racine
# Path(__file__).resolve().parent correspond à GitFetch/
root_path = Path(__file__).resolve().parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# Importation de la DB et des modèles (nécessaire pour Migrate)
from models import db, Utilisateur, Projet

# 2. Charger les variables d'environnement
load_dotenv(dotenv_path=root_path / ".env")

def create_manager_app():
    app = Flask(__name__)
    
    # Configuration de la Base de Données
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')
    
    # 3. Configuration du dossier static partagé à la racine
    # On définit le dossier d'upload à la racine du projet
    app.config['UPLOAD_FOLDER'] = root_path / 'static' / 'uploads'
    
    # Création automatique du dossier s'il n'existe pas
    if not app.config['UPLOAD_FOLDER'].exists():
        app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

    # Initialisation de la DB avec l'app
    db.init_app(app)
    
    # 4. Route pour servir les fichiers statiques depuis la racine
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return app

# Création de l'instance pour Flask-Migrate
app = create_manager_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        print(f"Base de données connectée : {os.getenv('DB_NAME')}")
        print(f"Dossier d'uploads configuré : {app.config['UPLOAD_FOLDER']}")
    
    # Lancement sur le port 5000 par défaut pour le management
    app.run(port=5000, debug=True)