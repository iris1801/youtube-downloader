import base64
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inizializza Flask
app = Flask(__name__)

# Configurazioni di base
app.config['SECRET_KEY'] = 'supersegreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Database
db = SQLAlchemy(app)

# Gestione Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    from app.models import User  # Importiamo qui per evitare loop
    return User.query.get(int(user_id))

from app.celery_worker import celery

# Definizione del filtro per Base64 encoding
def b64encode(value):
    """Codifica una stringa in Base64 per evitare caratteri non validi negli ID HTML."""
    return base64.b64encode(value.encode()).decode()

# Registra il filtro in Jinja2
app.jinja_env.filters['b64encode'] = b64encode

# Importiamo le rotte dopo l'inizializzazione dell'app
from app import routes, auth
