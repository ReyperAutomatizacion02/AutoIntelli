# autointelli/app.py

# coding: utf-8

# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
# No necesitas importar SQLAlchemy aquí si db viene de models
# from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
# Importar datetime y timedelta específicamente
from datetime import datetime, timedelta
# Importaciones de Modelos y BD desde .models
from .models import db, User, AuditLog # <<< Correcto: Importar db y modelos desde models.py
# Importaciones de módulos locales auxiliares (si aún se usan)
# from . import mH2 as moverHorarios02 # <<< Eliminar si la lógica se movió completamente a ajustes.py
# from .nuevosRegistros import crear_proyecto, crear_partidas # <<< Eliminar si la lógica se llama desde proyectos.py

from flask_migrate import Migrate
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from email_validator import validate_email, EmailNotValidError
import logging

# Configuración básica de logging (puedes expandirla)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Imports para Blueprints ---
from .solicitudes import solicitudes_bp # Blueprint de Solicitudes
from .ajustes import ajustes_bp       # Blueprint de Ajustes
from .proyectos import proyectos_bp   # <<< Importar el nuevo Blueprint de Proyectos
# --- Fin Imports Blueprints ---


# Cargar variables de entorno (¡Una vez al inicio!)
# ¡Importante!: En Render, las variables de entorno se configuran directamente.
# load_dotenv() solo es necesario si ejecutas localmente fuera de un entorno que ya carga .env
# Para Render, puedes comentar o dejarlo, no hará daño si no hay un .env file.
load_dotenv() # Lo mantenemos por si se ejecuta localmente con .env

# --- Define las rutas a las carpetas de plantillas y static (antes de crear la app) ---
# Asegúrate de que esta estructura de directorios coincida con tu despliegue en Render
# Esto asume que autointelli está dentro de un directorio principal que también contiene templates y static
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
# --- Fin Definición de Rutas ---


# =====================
# Creación de app Flask
# =====================
# Función de fábrica para la aplicación (recomendado con Blueprints y extensiones)
# Aunque tu código actual no usa una función de fábrica explícita,
# la estructura con init_app se presta bien a ello.
# Para mantener tu estructura actual, simplemente crea la instancia aquí.
app = Flask(__name__,
            template_folder=template_dir,
            static_folder=static_dir
           )
# --- Fin Creación de app Flask ---


# --- Configuración de la Aplicación (General) ---

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    logger.warning("SECRET_KEY no configurada. La aplicación no es segura.") # Cambiado de print a warning/logger
    # En producción, deberías manejar esto como un error fatal o proveer un valor por defecto MUY seguro

# Configuración de Flask-Mail (General)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com') # Añadir valor por defecto
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465)) if os.environ.get('MAIL_PORT') else 465 # Añadir valor por defecto y convertir a int de forma segura
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true' # Default False
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true' # Default True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME')) # Default MAIL_USERNAME, usar .get por si MAIL_USERNAME tampoco existe

if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
     logger.warning("MAIL_USERNAME o MAIL_PASSWORD no configurados. La funcionalidad de correo no funcionará.")


mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuración de la base de datos (General)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
if not app.config['SQLALCHEMY_DATABASE_URI']:
     logger.error("DATABASE_URL no configurada. La aplicación no funcionará sin base de datos.")
     # Dependiendo de si la DB es vital para el inicio, podrías querer crashear o manejarlo.
     # En Render, esto probablemente causaría un fallo de inicio.

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Inicializar DB CON LA INSTANCIA DE APP ---
# db es importado desde .models y es SQLAlchemy()
db.init_app(app) # Inicializa db pasando la instancia 'app'
migrate = Migrate(app, db)

# Configuración de Flask-Login (General)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# Configura la categoría del mensaje flash para login_required
login_manager.login_message_category = 'info'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'


# --- Modelos de Base de Datos (Importados desde models.py) ---
# Las clases User y AuditLog se definen en models.py

# Función para cargar usuario (requerida por Flask-Login)
# Usa el modelo User importado desde .models y db importado desde .models
@login_manager.user_loader
def load_user(user_id):
    # Dentro de un contexto de aplicación, puedes acceder a db
    # Si esta función está en app.py y db.init_app(app) ya corrió,
    # db está disponible globalmente en el contexto de app.
    try:
        return db.session.get(User, int(user_id)) # Usa sintaxis moderna y segura
    except (ValueError, TypeError):
         return None # user_id inválido

# --- Registrar Blueprints ---
app.register_blueprint(solicitudes_bp) # Registra el Blueprint de Solicitudes
app.register_blueprint(ajustes_bp)     # Registra el Blueprint de Ajustes
app.register_blueprint(proyectos_bp)   # <<< Registrar el nuevo Blueprint de Proyectos
# --- Fin Registro Blueprints ---


# ===========================================
# Definición de las rutas principales:
# (Rutas que no pertenecen claramente a un solo Blueprint, como login/logout, index)
# ===========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
     # Redirigir si ya está autenticado
     if current_user.is_authenticated:
         return redirect(url_for('index'))

     if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
             flash('Ingresa usuario y contraseña.', 'danger')
             return render_template('login.html'), 400

        # Usa el modelo User importado desde .models
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login exitoso.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger')
            return render_template('login.html'), 401 # Unauthorized

     return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
     # Redirigir si ya está autenticado
     if current_user.is_authenticated:
         return redirect(url_for('index'))

     if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')

        if not username or not password or not confirm_password or not email:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('register.html'), 400

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html'), 400

        try:
            emailinfo = validate_email(email, check_deliverability=False)
            email = emailinfo.normalized
        except EmailNotValidError as e:
            flash(str(e), 'danger')
            return render_template('register.html'), 400

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está registrado. Por favor, elige otro.', 'danger')
            return render_template('register.html'), 409 # Conflict

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('El correo electrónico ya está registrado. Por favor, utiliza otro.', 'danger')
            return render_template('register.html'), 409 # Conflict

        hashed_password = generate_password_hash(password)
        # Usa el modelo User importado desde .models
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user) # Usa db importado de .models
        try:
             db.session.commit() # Usa db importado de .models
             flash('Registro exitoso. Por favor, inicia sesión.', 'success')
             return redirect(url_for('login'))
        except Exception as e:
             db.session.rollback()
             logger.error(f"Error durante el registro del usuario '{username}': {e}", exc_info=True)
             flash(f'Error al registrar usuario: {e}', 'danger')
             return render_template('register.html'), 500 # Internal Server Error

     return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout exitoso.', 'info')
    return redirect(url_for('index'))

@app.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    # Redirigir si ya está autenticado
    if current_user.is_authenticated:
         return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
             flash('Ingresa usuario y correo electrónico.', 'danger')
             return render_template('recover_password.html'), 400

        # Usa el modelo User importado desde .models
        user = User.query.filter_by(username=username, email=email).first()

        if user:
            # Generar un token con tiempo de expiración (1 hora)
            token = s.dumps(user.email, salt='recover-key')
            # Crear el enlace externo
            link = url_for('reset_password', token=token, _external=True)
            logger.info(f"Generado enlace de restablecimiento para {user.username}")

            # Asegúrate de que AuditLog está importado desde .models y db.session
            # No guardar el token completo en el log por seguridad
            audit_log = AuditLog(
                user_id=user.id,
                action='Solicitud de restablecimiento de contraseña',
                details='Enlace de restablecimiento generado'
            )
            db.session.add(audit_log)
            try:
                db.session.commit()
                logger.info(f"Registro de auditoría creado para solicitud de restablecimiento de {user.username}.")
            except Exception as audit_e:
                db.session.rollback()
                logger.warning(f"WARNING: Could not commit audit log entry for password recovery request: {audit_e}", exc_info=True)


            try:
                # Asegurarse de que la configuración de correo es completa
                if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
                    raise Exception("Configuración de correo incompleta.")

                msg = Message('Restablecer Contraseña', sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[user.email])
                msg.body = f"""Hola {user.username},

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{link}

Este enlace expirará en 1 hora.

Si no solicitaste restablecer tu contraseña, puedes ignorar este correo.

Saludos,
El equipo de AutoIntelli
""" # Mejorar el cuerpo del correo
                mail.send(msg)
                flash('Se ha enviado un correo electrónico con un enlace para restablecer la contraseña.', 'success')
                return redirect(url_for('login'))
            except Exception as mail_e:
                flash('Error al enviar el correo de restablecimiento de contraseña. Por favor, verifica la configuración del correo.', 'danger')
                logger.error(f"ERROR al enviar correo de restablecimiento para {user.username}: {mail_e}", exc_info=True)
                # No es un error del usuario, es del servidor.
                return render_template('recover_password.html'), 500 # Internal Server Error

        else:
            # No dar demasiada información al atacante, solo decir que falló
            flash('Usuario o correo electrónico incorrectos.', 'danger')
            # Podrías considerar loguear intentos fallidos aquí
            return render_template('recover_password.html'), 400 # Bad Request

    return render_template('recover_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = None
    user = None
    try:
        # Cargar el email desde el token, verificando la expiración
        email = s.loads(token, salt='recover-key', max_age=3600)
        # Buscar al usuario por el email extraído del token
        user = User.query.filter_by(email=email).first()
        if not user:
             # Usuario no encontrado con ese email (quizás eliminado?)
             raise Exception("Usuario no encontrado.")

    except Exception as e:
        # El token es inválido, expiró, o el usuario no existe para ese email
        logger.warning(f"Intento de restablecimiento de contraseña con token inválido o expirado: {token}. Error: {e}")
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('login'))

    # Opcional: Verificar el registro de auditoría si lo usas para validar el token (menos común, la caducidad es suficiente)
    # audit_log = AuditLog.query.filter_by(details=f'Token de restablecimiento generado').filter(AuditLog.user_id == user.id).filter(AuditLog.timestamp > datetime.utcnow() - timedelta(hours=1)).first()
    # if not audit_log:
    #     flash('El enlace para restablecer la contraseña es inválido o ha expirado (registro no encontrado).', 'danger')
    #     return redirect(url_for('login'))


    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
             flash('Debes ingresar y confirmar la nueva contraseña.', 'danger')
             return render_template('reset_password.html', token=token), 400

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html', token=token), 400

        # user ya está cargado desde el token
        hashed_password = generate_password_hash(password)
        user.password = hashed_password

        # Opcional: Eliminar registro de auditoría o marcarlo como usado (si lo buscas/usas)
        # if audit_log:
        #     db.session.delete(audit_log)

        try:
            db.session.commit()
            logger.info(f"Contraseña restablecida para usuario {user.username}.")
            flash('La contraseña se ha restablecido correctamente.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
             db.session.rollback()
             logger.error(f"Error al guardar la nueva contraseña para {user.username}: {e}", exc_info=True)
             flash(f'Error al guardar la nueva contraseña: {e}', 'danger')
             return render_template('reset_password.html', token=token), 500

    # GET request
    return render_template('reset_password.html', token=token)


# --- Las rutas de 'create_project', 'adjust_dates', 'run_script' se han movido a Blueprints ---
# La ruta /create_project ahora está en proyectos.py (@proyectos_bp.route('/create'))
# La ruta /adjust_dates ahora está en ajustes.py (@ajustes_bp.route('/'))
# La ruta /run_script ahora está en ajustes.py (@ajustes_bp.route('/run'))


# ================================
# Punto de entrada para WSGI (Render)
# ================================
# Esta variable `app` es la que Gunicorn buscará.
# El bloque if __name__ == '__main__': con app.run() ya fue eliminado.
# La inicialización de DB (db.create_all) y la creación inicial de usuarios
# deben manejarse por separado, típicamente con Flask-Migrate (flask db upgrade)
# y scripts de inicialización ejecutados una vez en el entorno de despliegue (Render).