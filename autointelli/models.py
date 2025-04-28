# autointelli/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
# No importes 'app' aquí directamente al inicio

db = SQLAlchemy() # <<< Inicializa SQLAlchemy SIN pasar la instancia 'app' aquí

# Función para cargar usuario (requerida por Flask-Login)
# Esta función necesita acceso a la instancia 'app' o 'db'.
# La convención es tenerla en el archivo donde se inicializa LoginManager (app.py)
# y usar 'app.app_context()' si necesita acceso a 'db'.
# Si la dejas aquí, necesitarás importar 'app' o usar 'current_app'
# Es más limpio dejarla en app.py y usar app.app_context().
# @login_manager.user_loader
# def load_user(user_id):
#     # Esta función necesita estar en el archivo donde se inicializa login_manager
#     # Y usar el contexto de la aplicación para acceder a db
#     # from flask import current_app
#     # with current_app.app_context():
#     #     return User.query.get(int(user_id))
#     # O si db está bien inicializado globalmente:
#     # return db.session.get(User, int(user_id)) # Sintaxis moderna con session
#     # Mejor: Dejarla en app.py y usar db directamente allí si db está globalmente accesible DESPUÉS de su inicialización

# Clase de Usuario (Modelo de Base de Datos)
class User(UserMixin, db.Model): # db.Model es el que usa la instancia 'db'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # __init__ method is not standard with SQLAlchemy models
    # def __init__(self, username, password, email):
    #     self.username = username
    #     self.password = password
    #     self.email = email


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)

    user = db.relationship('User', backref='audit_logs', lazy=True)
    # O simplemente: user = db.relationship('User')

    def __repr__(self):
        username = "Usuario Desconocido"
        # Acceder a la relación User puede requerir contexto de aplicación
        # O asegurar que la sesión esté activa
        try:
             if self.user:
                  username = self.user.username
        except Exception:
             pass # Manejar si self.user no es cargable en este contexto

        return f'<AuditLog {self.id} - User: {username} - Action: {self.action} - Timestamp: {self.timestamp}>'

# NOTA: Las clases User y AuditLog necesitan acceder a la instancia 'db'
# Pero 'db' solo se inicializa completamente DESPUÉS de que se crea la app Flask.
# Esto se maneja correctamente al pasar la instancia 'app' a 'db.init_app(app)' en app.py
# y luego importar 'db' y los modelos en los Blueprints.