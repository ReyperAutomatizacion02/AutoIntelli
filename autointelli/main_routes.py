# autointelli/main_routes.py

from flask import Blueprint, render_template

# Crear el Blueprint para las rutas principales. Sin prefijo URL.
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Flask-Login inyecta current_user automáticamente en el contexto de la plantilla
    return render_template('index.html')