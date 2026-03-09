# /var/www/votre_username_pythonanywhere_com_wsgi.py
# (chemin exact à adapter selon votre configuration PythonAnywhere)

import sys
import os

# Ajouter le chemin de votre projet
path = '/home/votre_username/gitfetch'  # Remplacez par votre vrai chemin
if path not in sys.path:
    sys.path.append(path)

# Désactiver la sortie buffering (optionnel)
os.environ['PYTHONUNBUFFERED'] = '1'

# Importer votre application Flask
from application import application as app

# Point d'entrée pour PythonAnywhere
application = app