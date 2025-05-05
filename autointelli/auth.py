# autointelli/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import logging

# Importar db y modelos desde el paquete
from .models import db, User, AuditLog # Asegúrate de importar User
# Importar la clase Message de flask_mail (si la usas en recover_password)
from flask_mail import Message

# Crear el Blueprint. Prefijo /auth para todas las rutas.
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

logger = logging.getLogger(__name__)

# Helper para acceder al serializador y mail desde current_app (si usas flask_mail y su serializer)
def get_mail_and_serializer():
    # Acceder a mail y s a través de la instancia de la aplicación
    mail = current_app.mail if hasattr(current_app, 'mail') else None # Verifica si mail está inicializado
    s = current_app.url_serializer # O como lo hayas guardado en la fábrica
    return mail, s


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Ingresa usuario y contraseña.', 'danger')
            return render_template('auth/login.html'), 400

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Bienvenido, {user.username}!', 'success') # Flash personalizado con username
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger')
            return render_template('auth/login.html'), 401

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # --- OBTENER LOS NUEVOS CAMPOS DEL FORMULARIO ---
        first_name = request.form.get('first_name', '').strip() # Usar .strip() para limpiar espacios
        last_name = request.form.get('last_name', '').strip()
        # --- FIN OBTENER ---

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        email = request.form.get('email', '').strip()

        # --- VALIDAR CAMPOS OBLIGATORIOS (INCLUIR NUEVOS) ---
        # Lista de campos que no deben estar vacíos
        fields_to_check = {
             'Nombre': first_name,
             'Apellido': last_name,
             'Nombre de Usuario': username,
             'Correo Electrónico': email,
             'Contraseña': password,
             'Confirmar Contraseña': confirm_password # Validamos que no esté vacío, la coincidencia se valida después
        }

        missing_fields = [name for name, value in fields_to_check.items() if not value]

        if missing_fields:
            flash(f"Faltan campos obligatorios: {', '.join(missing_fields)}.", 'danger')
            return render_template('auth/register.html',
                                   # Opcional: Pasar de vuelta los valores ingresados (excepto contraseñas)
                                   first_name=first_name,
                                   last_name=last_name,
                                   username=username,
                                   email=email), 400

        # --- FIN VALIDAR CAMPOS OBLIGATORIOS ---


        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   username=username,
                                   email=email), 400

        try:
            emailinfo = validate_email(email, check_deliverability=False)
            email_normalized = emailinfo.normalized # Usar el email normalizado
        except EmailNotValidError as e:
            flash(str(e), 'danger')
            return render_template('auth/register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   username=username,
                                   email=email), 400


        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está registrado. Por favor, elige otro.', 'danger')
            return render_template('auth/register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   # No pasar username de vuelta aquí si ya está tomado
                                   email=email), 409

        existing_email = User.query.filter_by(email=email_normalized).first()
        if existing_email:
            flash('El correo electrónico ya está registrado. Por favor, utiliza otro.', 'danger')
            return render_template('auth/register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   username=username), 409

        hashed_password = generate_password_hash(password)
        # --- CREAR NUEVO USUARIO CON CAMPOS DE NOMBRE Y APELLIDO ---
        new_user = User(username=username,
                        first_name=first_name,
                        last_name=last_name,
                        password=hashed_password,
                        email=email_normalized)
        # --- FIN CREAR NUEVO USUARIO ---

        db.session.add(new_user)
        try:
            db.session.commit()
            # Registrar registro de auditoría (opcional, requiere importar AuditLog y db)
            # Si quieres registrar cada registro, asegúrate de que la tabla AuditLog existe
            # try:
            #     audit_log = AuditLog(
            #         user_id=new_user.id, # Usar el ID del nuevo usuario
            #         action='Registro de nuevo usuario',
            #         details=f"Nuevo usuario registrado: {username} ({first_name} {last_name})"
            #     )
            #     db.session.add(audit_log)
            #     db.session.commit() # Hacer commit nuevamente para el log, o hacer un solo commit grande
            # except Exception as audit_e:
            #      logger.warning(f"WARNING: Could not create audit log entry for new user registration: {audit_e}", exc_info=True)
            #      db.session.rollback() # Rollback del log pero no del usuario si el primer commit fue successful? Depende de tu estrategia.

            logger.info(f"Nuevo usuario registrado: {username} ({first_name} {last_name})")
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error durante el registro del usuario '{username}': {e}", exc_info=True)
            flash(f'Error al registrar usuario: {e}', 'danger')
            return render_template('auth/register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   username=username,
                                   email=email), 500

    # GET request
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    user_username = current_user.username # Guardar antes de logout_user si necesitas el nombre en el mensaje
    logout_user()
    flash('Logout exitoso.', 'info')
    # Opcional: log de auditoría de logout
    # try:
    #     audit_log = AuditLog(
    #         user_id=current_user.id if current_user.is_authenticated else None, # user might not be authenticated after logout
    #         action='Logout',
    #         details=f"Usuario {user_username} cerró sesión."
    #     )
    #     db.session.add(audit_log)
    #     db.session.commit()
    # except Exception as e:
    #      logger.warning(f"WARNING: Could not create audit log for logout: {e}", exc_info=True)


    return redirect(url_for('main.index'))


@auth_bp.route('/recover_password', methods=['GET', 'POST'])
# El código de recover_password se mantiene igual, no necesita first/last name para recuperar
def recover_password():
    if current_user.is_authenticated:
         return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
             flash('Ingresa usuario y correo electrónico.', 'danger')
             return render_template('auth/recover_password.html'), 400

        user = User.query.filter_by(username=username, email=email).first()

        if user:
            mail, s = get_mail_and_serializer()
            if not mail or not s:
                logger.error("Mail or Serializer not configured properly.")
                flash('Error interno: Funcionalidad de correo no disponible.', 'danger')
                return render_template('auth/recover_password.html'), 500


            # Generar un token con tiempo de expiración (1 hora)
            token = s.dumps(user.email, salt='recover-key')
            link = url_for('auth.reset_password', token=token, _external=True)
            logger.info(f"Generado enlace de restablecimiento para {user.username}")

            # Registrar solicitud de auditoría
            audit_log = AuditLog(
                user_id=user.id,
                action='Solicitud de restablecimiento de contraseña',
                details=f'Enlace de restablecimiento generado para {user.username}' # Incluir username
            )
            db.session.add(audit_log)
            try:
                db.session.commit()
                logger.info(f"Registro de auditoría creado para solicitud de restablecimiento de {user.username}.")
            except Exception as audit_e:
                db.session.rollback()
                logger.warning(f"WARNING: Could not commit audit log entry for password recovery request: {audit_e}", exc_info=True)

            try:
                if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
                     raise Exception("Configuración de correo incompleta en app.config.")

                msg = Message('Restablecer Contraseña', sender=current_app.config.get('MAIL_DEFAULT_SENDER') or 'noreply@autointelli.com', recipients=[user.email]) # Usar sender por defecto
                # Personalizar mensaje con nombre de usuario
                msg.body = f"""Hola {user.username},

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{link}

Este enlace expirará en 1 hora.

Si no solicitaste restablecer tu contraseña, puedes ignorar este correo.

Saludos,
El equipo de AutoIntelli
"""
                mail.send(msg)
                flash('Se ha enviado un correo electrónico con un enlace para restablecer la contraseña.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as mail_e:
                flash('Error al enviar el correo de restablecimiento de contraseña. Por favor, verifica la configuración del correo.', 'danger')
                logger.error(f"ERROR al enviar correo de restablecimiento para {user.username}: {mail_e}", exc_info=True)
                return render_template('auth/recover_password.html'), 500

        else:
            logger.warning(f"Intento fallido de recuperación de contraseña para username '{username}' y email '{email}'. Usuario no encontrado con esa combinación.")
            flash('Usuario o correo electrónico incorrectos.', 'danger')
            return render_template('auth/recover_password.html'), 400

    return render_template('auth/recover_password.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
# El código de reset_password se mantiene igual
def reset_password(token):
    user = None
    mail, s = get_mail_and_serializer() # Obtener s de la aplicación
    if not s:
         logger.error("Serializer not configured properly.")
         flash('Error interno.', 'danger')
         return redirect(url_for('auth.login'))

    try:
        email = s.loads(token, salt='recover-key', max_age=3600)
        user = User.query.filter_by(email=email).first()
        if not user:
             logger.warning(f"Intento de restablecimiento de contraseña con token válido pero usuario no encontrado para email: {email}")
             raise Exception("Usuario no encontrado.")

    except Exception as e:
        logger.warning(f"Intento de restablecimiento de contraseña con token inválido/expirado/usuario no encontrado. Token: {token}. Error: {e}")
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
             flash('Debes ingresar y confirmar la nueva contraseña.', 'danger')
             return render_template('auth/reset_password.html', token=token), 400

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/reset_password.html', token=token), 400

        hashed_password = generate_password_hash(password)
        user.password = hashed_password

        try:
            db.session.commit()
            logger.info(f"Contraseña restablecida para usuario {user.username}.")
            flash('La contraseña se ha restablecido correctamente.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
             db.session.rollback()
             logger.error(f"Error al guardar la nueva contraseña para {user.username}: {e}", exc_info=True)
             flash(f'Error al guardar la nueva contraseña: {e}', 'danger')
             return render_template('auth/reset_password.html', token=token), 500

    return render_template('auth/reset_password.html', token=token)