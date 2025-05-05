# autointelli/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # --- CAMBIAR ROL POR DEFECTO Y NOTA ---
    role = db.Column(db.String(50), default='visitante', nullable=False) # Rol por defecto. Ajusta si es necesario.
    # Roles posibles: 'admin', 'logistica', 'diseno', 'almacen', 'compras', 'visitante'
    # ------------------------------------

    def __repr__(self):
        return f'<User {self.username} (Role: {self.role})>'


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)

    user = db.relationship('User', backref='audit_logs', lazy=True)

    def __repr__(self):
        username_str = "Usuario Desconocido"
        try:
             username_str = self.user.username if self.user else f"ID:{self.user_id} (No cargado/Eliminado)"
        except Exception:
             username_str = f"ID:{self.user_id} (Error de carga)"

        action_repr = self.action[:50] + '...' if len(self.action) > 50 else self.action

        return f'<AuditLog {self.id} User:{username_str} Action:"{action_repr}" @{self.timestamp.strftime("%Y-%m-%d %H:%M")}>'