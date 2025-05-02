# autointelli/decorators.py

from functools import wraps
from flask import flash, redirect, url_for, abort, current_app # Importar current_app si es necesario en los decoradores (ej: para logger)
from flask_login import current_user # Importar current_user
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Decorador para requerir uno o más roles
def role_required(allowed_roles):
    if not isinstance(allowed_roles, (list, tuple)):
        allowed_roles = [allowed_roles] # Asegurarse de que siempre es una lista/tupla

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f"Checking role access for user {current_user.username} to endpoint {f.__name__}. Allowed roles: {allowed_roles}")

            # Verificar si el usuario está autenticado
            # @login_required debería manejar la redirección si no está autenticado
            # pero la verificación explícita aquí es para la lógica de roles *después* de la autenticación.
            if not current_user.is_authenticated:
                logger.warning(f"Acceso denegado: Usuario no autenticado intentando acceder a {f.__name__}")
                # La redirección al login ya la maneja Flask-Login con login_required
                # return redirect(url_for('auth.login')) # No es necesario re-redirigir

                # Si llegas aquí, algo podría estar mal con la combinación de decoradores,
                # pero en teoría @login_required se ejecuta primero y redirige.
                # Si insiste en este error, podrías querer lanzar un 401 o redirigir explícitamente.
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                # Redirigir al login del Blueprint de auth
                # Asegúrate de que el endpoint 'auth.login' existe y está registrado.
                return redirect(url_for(current_app.config.get('LOGIN_VIEW', 'auth.login'))) # Usar la vista de login configurada


            # Verificar si el usuario tiene alguno de los roles permitidos
            # Asumimos que el modelo User tiene un atributo 'role' (string)
            if hasattr(current_user, 'role') and current_user.role in allowed_roles:
                logger.debug(f"Access granted: User {current_user.username} has role {current_user.role}.")
                return f(*args, **kwargs) # El usuario tiene un rol permitido, permitir acceso

            else:
                # El usuario está autenticado pero no tiene un rol permitido
                logger.warning(f"Acceso denegado: Usuario {current_user.username} (Role: {current_user.role}) intentando acceder a {f.__name__} (Requiere: {', '.join(allowed_roles)})")
                flash('No tienes los permisos necesarios para acceder a esta página.', 'warning')
                # Devolver un error 403 Forbidden es una buena práctica para permisos denegados
                abort(403) # Devolver 403 Forbidden

        return decorated_function
    return decorator

# Opcional: Decorador específico para admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Reutiliza el decorador role_required para el rol 'admin'
        # Llama directamente a la función decorada retornada por role_required
        return role_required('admin')(f)(*args, **kwargs)
    return decorated_function

# Opcional: Decorador para permitir varios roles (sintaxis alternativa a role_required)
# @any_role_required('logistica', 'admin')
def any_role_required(*roles):
     def decorator(f):
          @wraps(f)
          def decorated_function(*args, **kwargs):
               # Llama directamente a la función decorada retornada por role_required
               return role_required(roles)(f)(*args, **kwargs)
          return decorated_function
     return decorator