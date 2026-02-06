from flask import Flask, render_template
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

#Charger les variables d'environnement du fichier .env
load_dotenv()

#Récupérer les variables individuellement
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')

#Construire l'URL SQLAlchemy
DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')
@app.route("/register")
def register()
    return render_template("auth/register.html")

if __name__ == "__main__":
    app.run(debug=True)