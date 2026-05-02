# routes.py - Version avec téléchargement local des avatars et correction GitHub OAuth

import os
import requests
import secrets
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, url_for, flash, redirect, current_app, send_from_directory, abort, session
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from dotenv import load_dotenv

# Modification des imports - plus de points (même répertoire)
from models import db, Utilisateur, Projet, PortfolioConfig, AboutPage
from sqlalchemy import inspect, text
import time
import logging

# Charger le fichier .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATIONS ---
# Configuration GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get('ID_CLIENT_GITHUB', '')  # Changé pour correspondre à index.py
GITHUB_CLIENT_SECRET = os.environ.get('SECRET_DU_CLIENT_GITHUB', '')  # Changé pour correspondre
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'

# Configuration Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('ID_CLIENT_GOOGLE', '')  # Changé pour correspondre
GOOGLE_CLIENT_SECRET = os.environ.get('SECRET_DU_CLIENT_GOOGLE', '')  # Changé pour correspondre
GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'

# --- CRÉATION DES BLUEPRINTS ---
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
portfolio_bp = Blueprint('portfolio', __name__)
github_bp = Blueprint('github_bp', __name__, url_prefix='/github')

# [Le reste du fichier routes.py reste identique à partir d'ici]
# (Copiez tout le contenu de votre routes.py à partir de "# --- FONCTIONS UTILITAIRES COMMUNES ---")

# Note : Assurez-vous que toutes les fonctions (download_and_save_avatar, generer_jeton, 
# verifier_jeton, envoyer_email, get_media_path, etc.) sont présentes dans ce fichier.