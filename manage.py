import os
from flask import Flask
from flask_migrate import Migrate
from models import db  # Importe le db de ton models.py racine
from dotenv import load_dotenv

# Charger l'environnement
load_dotenv()

def create_manager_app():
    app = Flask(__name__)
    
    # Configuration minimale pour que Migrate fonctionne
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

app = create_manager_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run()