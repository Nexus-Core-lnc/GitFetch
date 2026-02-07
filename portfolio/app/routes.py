from flask import Blueprint, render_template
import os

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio', endpoint='portfolio')
def portfolio():
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return render_template('portfolio.html', auth_url=auth_url, admin_url=admin_url)


@portfolio_bp.route('/me_connaitre', endpoint='me_connaitre')
def me_connaitre():
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return render_template('me_connaitre.html', auth_url=auth_url, admin_url=admin_url)

@portfolio_bp.route('/projets', endpoint='projets')
def projet():
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return render_template('projet.html', auth_url=auth_url, admin_url=admin_url)

@portfolio_bp.route('/contact', endpoint='contact')
def contact():
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return render_template('contact.html', auth_url=auth_url, admin_url=admin_url)

@portfolio_bp.route('/', endpoint='home')
def home():
    auth_url = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:5001')
    admin_url = os.getenv('ADMIN_SERVICE_URL', 'http://127.0.0.1:5002')
    
    return render_template('portfolio.html', auth_url=auth_url, admin_url=admin_url)