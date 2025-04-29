# autointelli/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app # Importar current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import logging

# Importar db y modelos desde el paquete
from .models import db, User, AuditLog # <<< Importación correcta

# Importar la clase Message de flask_mail
from flask_mail import Message

# Crear el Blueprint. Prefijo /auth para todas las rutas.
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Helper para acceder al serializador y mail desde current_app
# Es más limpio acceder a mail y s a través de current_app después de que init_app()
# se haya ejecutado en la fábrica.
def get_mail_and_serializer():
    # Acceder a mail y s a través de la instancia de la aplicación
    mail = current_app.mail
    s = current_app.url_serializer # O como lo hayas guardado en la fábrica
    return mail, s


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirigir al index (o ruta principal) si ya logueado

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Ingresa usuario y contraseña.', 'danger')
            return render_template('auth/login.html'), 400 # Usar auth/ subdirectorio para plantillas

        user = User.query.filter_by(username=username).first() # Buscar el usuario por username (o email si lo prefieres)
        # O simplemente: user = User.query.filter_by(username=username).first() # Ambos son válidos en contexto de app

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login exitoso.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index')) # Redirigir al index (o ruta principal)
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger')
            return render_template('auth/login.html'), 401 # Unauthorized

    return render_template('auth/login.html') # Usar auth/ subdirectorio para plantillas


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Redirigir al index (o ruta principal) si ya logueado

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')

        if not username or not password or not confirm_password or not email:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('auth/register.html'), 400 # Usar auth/ subdirectorio

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html'), 400 # Usar auth/ subdirectorio

        try:
            emailinfo = validate_email(email, check_deliverability=False)
            email = emailinfo.normalized # Usar el email normalizado
        except EmailNotValidError as e:
            flash(str(e), 'danger')
            return render_template('auth/register.html'), 400 # Usar auth/ subdirectorio

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está registrado. Por favor, elige otro.', 'danger')
            return render_template('auth/register.html'), 409 # Conflict

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('El correo electrónico ya está registrado. Por favor, utiliza otro.', 'danger')
            return render_template('auth/register.html'), 409 # Conflict

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('auth.login')) # Redirigir al login del Blueprint
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error durante el registro del usuario '{username}': {e}", exc_info=True)
            flash(f'Error al registrar usuario: {e}', 'danger')
            return render_template('auth/register.html'), 500 # Internal Server Error

    return render_template('auth/register.html') # Usar auth/ subdirectorio


@auth_bp.route('/logout')
@login_required # Requiere estar logueado para cerrar sesión
def logout():
    logout_user()
    flash('Logout exitoso.', 'info')
    return redirect(url_for('main.index')) # Redirigir al index (o ruta principal)


@auth_bp.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    if current_user.is_authenticated:
         return redirect(url_for('main.index')) # Redirigir si ya está autenticado

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
             flash('Ingresa usuario y correo electrónico.', 'danger')
             return render_template('auth/recover_password.html'), 400 # Usar auth/ subdirectorio

        # Buscar usuario por username Y email
        user = User.query.filter_by(username=username, email=email).first()

        if user:
            # Obtener mail y s de la aplicación
            mail, s = get_mail_and_serializer()
            if not mail or not s:
                logger.error("Mail or Serializer not configured properly.")
                flash('Error interno: Funcionalidad de correo no disponible.', 'danger')
                return render_template('auth/recover_password.html'), 500


            # Generar un token con tiempo de expiración (1 hora)
            # Usar el serializer 's' obtenido de la aplicación
            token = s.dumps(user.email, salt='recover-key')
            # Crear el enlace externo
            link = url_for('auth.reset_password', token=token, _external=True) # Enlace al endpoint del Blueprint
            logger.info(f"Generado enlace de restablecimiento para {user.username}")

            # Registrar solicitud de auditoría
            audit_log = AuditLog(
                user_id=user.id,
                action='Solicitud de restablecimiento de contraseña',
                details='Enlace de restablecimiento generado' # No guardar el token completo en el log
            )
            db.session.add(audit_log)
            try:
                db.session.commit()
                logger.info(f"Registro de auditoría creado para solicitud de restablecimiento de {user.username}.")
            except Exception as audit_e:
                db.session.rollback()
                logger.warning(f"WARNING: Could not commit audit log entry for password recovery request: {audit_e}", exc_info=True)

            try:
                # Asegurarse de que la configuración de correo es completa antes de enviar
                if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
                     raise Exception("Configuración de correo incompleta en app.config.")

                msg = Message('Restablecer Contraseña', sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[user.email])
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
                return redirect(url_for('auth.login')) # Redirigir al login del Blueprint
            except Exception as mail_e:
                flash('Error al enviar el correo de restablecimiento de contraseña. Por favor, verifica la configuración del correo.', 'danger')
                logger.error(f"ERROR al enviar correo de restablecimiento para {user.username}: {mail_e}", exc_info=True)
                return render_template('auth/recover_password.html'), 500

        else: # Usuario no encontrado con esa combinación
            logger.warning(f"Intento fallido de recuperación de contraseña para username '{username}' y email '{email}'. Usuario no encontrado con esa combinación.")
            flash('Usuario o correo electrónico incorrectos.', 'danger')
            return render_template('auth/recover_password.html'), 400

    return render_template('auth/recover_password.html') # Usar auth/ subdirectorio


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = None
    mail, s = get_mail_and_serializer() # Obtener s de la aplicación
    if not s:
         logger.error("Serializer not configured properly.")
         flash('Error interno.', 'danger')
         return redirect(url_for('auth.login'))

    try:
        # Cargar el email desde el token, verificando la expiración
        email = s.loads(token, salt='recover-key', max_age=3600)
        # Buscar al usuario por el email extraído del token
        user = User.query.filter_by(email=email).first()
        if not user:
             logger.warning(f"Intento de restablecimiento de contraseña con token válido pero usuario no encontrado para email: {email}")
             raise Exception("Usuario no encontrado.") # Causa que caiga en el except y flashee error

    except Exception as e:
        logger.warning(f"Intento de restablecimiento de contraseña con token inválido/expirado/usuario no encontrado. Token: {token}. Error: {e}")
        flash('El enlace para restablecer la contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('auth.login')) # Redirigir al login del Blueprint

    # Opcional: Verificar el registro de auditoría si lo usas para validar el token (menos común, la caducidad es suficiente)
    # Este log entry no guarda el token, lo que lo hace menos útil para validar el token en sí,
    # pero sí confirma que hubo una solicitud asociada a este user_id en el tiempo correcto.
    # audit_log = db.session.filter(AuditLog).filter_by(action='Solicitud de restablecimiento de contraseña', user_id=user.id).filter(AuditLog.timestamp > datetime.utcnow() - timedelta(hours=1)).first()
    # if not audit_log:
    #     flash('El enlace para restablecer la contraseña es inválido o ha expirado (registro no encontrado).', 'danger')
    #     return redirect(url_for('auth.login'))


    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
             flash('Debes ingresar y confirmar la nueva contraseña.', 'danger')
             return render_template('auth/reset_password.html', token=token), 400

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/reset_password.html', token=token), 400

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
            return redirect(url_for('auth.login')) # Redirigir al login del Blueprint
        except Exception as e:
             db.session.rollback()
             logger.error(f"Error al guardar la nueva contraseña para {user.username}: {e}", exc_info=True)
             flash(f'Error al guardar la nueva contraseña: {e}', 'danger')
             return render_template('auth/reset_password.html', token=token), 500

    # GET request
    return render_template('auth/reset_password.html', token=token) # Usar auth/ subdirectorio