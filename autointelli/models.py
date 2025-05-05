# autointelli/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    # --- AÑADIR CAMPOS DE NOMBRE Y APELLIDO ---
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    # --- FIN AÑADIR CAMPOS ---
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(50), default='visitante', nullable=False) # Rol por defecto. Ajusta si es necesario.
    # Roles posibles: 'admin', 'logistica', 'diseno', 'almacen', 'compras', 'visitante'

    # Opcional: Añadir una propiedad para obtener el nombre completo fácilmente
    @property
    def full_name(self):
        # Combina nombre y apellido. Puedes ajustar el formato si necesitas (ej. Apellido, Nombre)
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self):
        return f'<User {self.username} ({self.full_name}, Role: {self.role})>'


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)

    user = db.relationship('User', backref='audit_logs', lazy=True)

    def __repr__(self):
        username_str = "Usuario Desconocido"
        user_info = f"ID:{self.user_id}"
        try:
            if self.user:
                 username_str = self.user.username
                 user_info = f"{username_str} ({self.user.full_name})" # Usar nombre completo si está disponible
            else:
                 user_info = f"ID:{self.user_id} (No cargado/Eliminado)"
        except Exception:
             user_info = f"ID:{self.user_id} (Error de carga)"


        action_repr = self.action[:50] + '...' if len(self.action) > 50 else self.action

        return f'<AuditLog {self.id} User:{user_info} Action:"{action_repr}" @{self.timestamp.strftime("%Y-%m-%d %H:%M")}>'