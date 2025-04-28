# autointelli/app.py

# coding: utf-8

# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
# Importaciones de Modelos y BD desde .models
from .models import db, User, AuditLog
# Importaciones de módulos locales (auxiliares o rutas que quedan aquí)
from . import mH2 as moverHorarios02 # Mantenemos si run_script queda aquí
from .nuevosRegistros import crear_proyecto, crear_partidas # Mantenemos si create_project queda aquí
from flask_migrate import Migrate
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from email_validator import validate_email, EmailNotValidError

# --- Imports para Blueprints ---
from .solicitudes import solicitudes_bp # Blueprint de Solicitudes
from .ajustes import ajustes_bp       # Blueprint de Ajustes
# En el futuro, importarías otros blueprints aquí, ej:
# from .proyectos import proyectos_bp
# --- Fin Imports Blueprints ---


# Cargar variables de entorno (¡Una vez al inicio!)
load_dotenv()

# --- Define las rutas a las carpetas de plantillas y static (antes de crear la app) ---
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
# --- Fin Definición de Rutas ---


# =====================
# Creación de app Flask
# (SOLO ESTE BLOQUE DEBE EXISTIR Y LA DEFINICIÓN DE DIRECTORIOS DEBE ESTAR ANTES)
# =====================
app = Flask(__name__,
            template_folder=template_dir,
            static_folder=static_dir
           )
# --- Fin Creación de app Flask ---


# --- Configuración de la Aplicación (General) ---
# Configuración de CORS (Global si se aplica a toda la app)
# from flask_cors import CORS # Descomentar si usas CORS global
# CORS(app) # Descomentar y configurar si usas CORS global

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Configuración de Flask-Mail (General)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') # Usar variable de entorno
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') # Usar variable de entorno
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME') # Usar variable de entorno

# NOTA: NOTION_TOKEN y DATABASE_ID_* variables ahora están en los Blueprints correspondientes

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuración de la base de datos (General)
# basedir = os.path.abspath(os.path.dirname(__file__)) # Ya no necesitas basedir aquí directamente
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') # Usar variable de entorno
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Inicializar DB CON LA INSTANCIA DE APP ---
# db es importado desde .models y es SQLAlchemy()
db.init_app(app) # Inicializa db pasando la instancia 'app'
migrate = Migrate(app, db)

# Configuración de Flask-Login (General)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Modelos de Base de Datos (Importados desde models.py) ---
# Las clases User y AuditLog se definen en models.py

# Función para cargar usuario (requerida por Flask-Login)
# Usa el modelo User importado desde models.py y db importado desde .models
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) # Usa sintaxis moderna

# --- Registrar Blueprints ---
app.register_blueprint(solicitudes_bp) # Registra el Blueprint de Solicitudes
app.register_blueprint(ajustes_bp)     # Registra el Blueprint de Ajustes
# En el futuro, registra otros blueprints aquí, ej:
# app.register_blueprint(proyectos_bp)
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
     if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Usa el modelo User importado desde .models
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login exitoso.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger')

     return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
     if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        if not username or not password or not confirm_password or not email:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')

        try:
            emailinfo = validate_email(email, check_deliverability=False)
            email = emailinfo.normalized
        except EmailNotValidError as e:
            flash(str(e), 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está registrado. Por favor, elige otro.', 'danger')
            return render_template('register.html')

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('El correo electrónico ya está registrado. Por favor, utiliza otro.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        # Usa el modelo User importado desde .models
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user) # Usa db importado de .models
        db.session.commit() # Usa db importado de .models

        flash('Registro exitoso. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login'))

     return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout exitoso.', 'info')
    return redirect(url_for('index'))

@app.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']

        # Usa el modelo User importado desde .models
        user = User.query.filter_by(username=username, email=email).first()

        if user:
            token = s.dumps(user.email, salt='recover-key')
            link = url_for('reset_password', token=token, _external=True)
            print(f"Reset password link: {link}")

            # Asegúrate de que AuditLog está importado desde .models
            audit_log = AuditLog(
                user_id=user.id,
                action='Solicitud de restablecimiento de contraseña',
                details=f'Token de restablecimiento de contraseña: {token}'
            )
            db.session.add(audit_log)
            db.session.commit()

            msg = Message('Restablecer Contraseña', sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[user.email])
            msg.body = f"Para restablecer tu contraseña, haz clic en el siguiente enlace: {link}"
            mail.send(msg)

            flash('Se ha enviado un correo electrónico con un enlace para restablecer la contraseña.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Usuario o correo electrónico incorrectos.', 'danger')
            return render_template('recover_password.html')

    return render_template('recover_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='recover-key', max_age=3600)
    except:
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('login'))

    # Asegúrate de que AuditLog está importado desde .models y db.session
    audit_log = AuditLog.query.filter_by(details=f'Token de restablecimiento de contraseña: {token}').first()
    if not audit_log:
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html', token=token)

        # Asegúrate de que User está importado desde .models
        user = User.query.filter_by(email=email).first()

        if user:
            hashed_password = generate_password_hash(password)
            user.password = hashed_password

            db.session.delete(audit_log)
            db.session.commit()

            flash('La contraseña se ha restablecido correctamente.', 'success')
            return redirect(url_for('login'))
        else:
            flash('El enlace para restablecer la contraseña es inválido.', 'danger')
            return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# --- Las rutas de 'create_project' y 'adjust_dates' que estaban aquí se MUEVEN a sus Blueprints ---
# La ruta /adjust_dates ahora está en ajustes.py (@ajustes_bp.route('/'))
# La ruta /run_script ahora está en ajustes.py (@ajustes_bp.route('/run'))
# La ruta /create_project aún está aquí por ahora


@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        # Llama a las funciones importadas desde .nuevosRegistros
        nombre_proyecto = request.form['nombre_proyecto']
        num_partidas = int(request.form['num_partidas'])

        # Asegúrate de que crear_proyecto y crear_partidas estén importadas arriba
        proyecto_page_id = crear_proyecto(nombre_proyecto)
        if proyecto_page_id:
            partidas_ids = crear_partidas(num_partidas, proyecto_page_id)
            if partidas_ids:
                return jsonify({'message': f'Proyecto "{nombre_proyecto}" creado con éxito con {len(partidas_ids)} partidas.'})
            else:
                return jsonify({'error': 'Error al crear las partidas.'}), 500
        else:
            return jsonify({'error': 'Error al crear el proyecto.'}), 500
    return render_template('create_project.html')


# ================================
# Ejecución de la aplicación Flask
# ================================

if __name__ == '__main__':
    # Asegúrate de que db y modelos se inicializan con init_app(app) y se importan desde .models
    with app.app_context():
        # Crea la base de datos y tablas si no existen
        db.create_all()
        print("Base de datos y tablas creadas (si no existían).")

        # *** CREACIÓN DE USUARIOS DE EJEMPLO (SOLO LA PRIMERA VEZ) ***
        if User.query.count() == 0:
            print("No se encontraron usuarios en la base de datos. Creando usuarios de ejemplo...")
            # Usar User importado desde .models
            hashed_password_admin = generate_password_hash('password123')
            hashed_password_usuario = generate_password_hash('password456')
            user_admin = User(username='admin', password=hashed_password_admin, email='admin@example.com')
            user_usuario = User(username='usuario', password=hashed_password_usuario, email='usuario@example.com')
            db.session.add(user_admin)
            db.session.add(user_usuario)
            db.session.commit()
            print("Usuarios de ejemplo 'admin' y 'usuario' creados en la base de datos.")
        else:
            print("Ya existen usuarios en la base de datos. Omitiendo creación de usuarios de ejemplo.")

        # *** Corrección de emails antiguos (opcional, si es necesario) ***
        # Usar User importado desde .models
        users = User.query.all()
        changes_made = False
        for user in users:
            if not user.email or user.email.strip() == '':
                user.email = f'{user.username}@example.com'
                changes_made = True
        if changes_made:
            db.session.commit()
            print("Emails por defecto asignados a usuarios sin email.")
        else:
            print("Todos los usuarios ya tenían email o no hay usuarios sin email.")
        # *** Fin corrección emails ***


    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)