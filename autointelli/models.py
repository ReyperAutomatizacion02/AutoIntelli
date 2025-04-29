# autointelli/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
# No importar 'app' o 'current_app' aquí directamente

db = SQLAlchemy() # Inicializa SQLAlchemy SIN pasar la instancia 'app' aquí

# Clase de Usuario (Modelo de Base de Datos)
class User(UserMixin, db.Model):
    # Por defecto, SQLAlchemy usa el nombre de clase en minúsculas como nombre de tabla ('user')
    # __tablename__ = 'users' # Puedes descomentar esto si quieres un nombre de tabla diferente

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # backref='audit_logs' en AuditLog ya crea una propiedad 'audit_logs' en User

    def __repr__(self):
        return f'<User {self.username}>'


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)

    # Define la relación con User. lazy='joined' o 'select' puede ser más eficiente que 'dynamic'
    # lazy=True (el default) es generalmente 'select' o similar, que es bueno.
    user = db.relationship('User', backref='audit_logs', lazy=True)

    def __repr__(self):
        # Acceder a self.user puede requerir contexto de aplicación o estar dentro de una sesión activa
        # Si el objeto User relacionado no ha sido cargado (ej. lazy='select' por defecto)
        # y accedes a self.user, SQLAlchemy intenta cargarlo.
        username_str = "Usuario Desconocido"
        try:
             # Solo intenta acceder si la relación ya fue cargada o puede serlo
             username_str = self.user.username if self.user else f"ID:{self.user_id} (No cargado/Eliminado)"
        except Exception:
             # Esto puede ocurrir si no hay contexto de aplicación o sesión
             username_str = f"ID:{self.user_id} (Error de carga)"

        # Acortar la acción para una representación concisa
        action_repr = self.action[:50] + '...' if len(self.action) > 50 else self.action

        return f'<AuditLog {self.id} User:{username_str} Action:"{action_repr}" @{self.timestamp.strftime("%Y-%m-%d %H:%M")}>'