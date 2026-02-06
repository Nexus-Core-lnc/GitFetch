from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail # Ajouter cet import
from dotenv import load_dotenv
import os

db = SQLAlchemy()
mail = Mail() # Initialiser l'objet mail

def create_app():
    load_dotenv()
    app = Flask(__name__)

    # Configuration DB
    DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    # Configuration Mail
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

    db.init_app(app)
    mail.init_app(app)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app