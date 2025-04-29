# autointelli/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv # Para cargar .env en desarrollo local
from notion_client import Client # Inicializar el cliente Notion

# Inicializar extensiones SIN pasar la app (se inicializarán *dentro* de create_app)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

# Serializer para token de recuperación de contraseña (inicializará con SECRET_KEY)
# Lo creamos aquí para que sea accesible después de init_app
s = URLSafeTimedSerializer("default_secret_key") # Valor temporal, se actualizará con la config de la app

def create_app():
    # Cargar variables de entorno si el archivo .env existe (solo para desarrollo local)
    # En Render, las variables de entorno se configuran directamente
    load_dotenv()

    # Define las rutas a las carpetas de plantillas y static (relativo a la carpeta padre)
    # Asegúrate de que la estructura de directorios coincida con tu despliegue
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))


    app = Flask(__name__,
                instance_relative_config=True, # Permite usar config.py en instance/
                template_folder=template_dir,
                static_folder=static_dir
               )

    # --- Configuración de la Aplicación ---
    # Cargar configuración desde variables de entorno
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = 'una_clave_secreta_por_defecto_muy_segura_cambiar_en_produccion' # PROPORCIONAR DEFAULT MUY SEGURO O CRASHEAR

    # Configuración de Base de Datos
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        print("ERROR FATAL: DATABASE_URL no configurada. La aplicación no puede iniciar.")
        # En producción real, podrías querer crashear de forma controlada.
        # raise EnvironmentError("DATABASE_URL not configured.")
        pass # Permite que la app se cree pero fallará al usar la DB


    # Configuración de Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465)) if os.environ.get('MAIL_PORT') else 465
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))

    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
         print("ADVERTENCIA: Configuración de correo incompleta. La funcionalidad de correo no funcionará.") # Usar print aquí antes de configurar logging

    # Configuración de Notion (ahora centralizada)
    app.config['NOTION_API_KEY'] = os.environ.get("NOTION_API_KEY")
    app.config['DATABASE_ID_PROYECTOS'] = os.environ.get("DATABASE_ID_PROYECTOS")
    app.config['DATABASE_ID_PARTIDAS'] = os.environ.get("DATABASE_ID_PARTIDAS")
    app.config['DATABASE_ID_PLANES'] = os.environ.get("DATABASE_ID_PLANES")
    app.config['DATABASE_ID_MATERIALES_DB1'] = os.environ.get("DATABASE_ID") # ID DB 1 Materiales
    app.config['DATABASE_ID_MATERIALES_DB2'] = os.environ.get("DATABASE_ID_2") # ID DB 2 Materiales

    # Inicializar Cliente Notion aquí si NOTION_API_KEY está configurada
    # Guardamos la instancia en app.extensions o app.config para accederla después
    app.notion_client = None # Añadimos el cliente directamente a la instancia de app
    if app.config.get('NOTION_API_KEY'):
         try:
              app.notion_client = Client(auth=app.config['NOTION_API_KEY'])
              print("Cliente de Notion inicializado en la fábrica.")
         except Exception as e:
              print(f"ERROR al inicializar Notion Client: {e}")
              app.notion_client = None # Asegurarse de que sea None en caso de fallo
    else:
         print("ADVERTENCIA: NOTION_API_KEY no configurada. La integración con Notion no funcionará.")


    # --- Inicializar Extensiones con la App ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    # Actualizar el serializer con la SECRET_KEY de la app configurada
    global s # Acceder a la variable global s
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    app.url_serializer = s # También podrías guardarlo en la app si lo accedes desde Blueprints


    # Configuración de Flask-Login
    login_manager.login_view = 'auth.login' # Especifica el endpoint del Blueprint de auth
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'

    # Configurar la función user_loader
    @login_manager.user_loader
    def load_user(user_id):
        # Importar User DENTRO de la función user_loader para evitar problemas de importación circular
        # Alternativamente, puedes importar User arriba si db ya está inicializado con init_app
        # Es más limpio importar aquí para user_loader
        from .models import User
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
             return None


    # --- Registrar Blueprints ---
    from .auth import auth_bp
    from .solicitudes import solicitudes_bp
    from .ajustes import ajustes_bp
    from .proyectos import proyectos_bp
    from .main_routes import main_bp

    app.register_blueprint(main_bp)       # Rutas principales (/)
    app.register_blueprint(auth_bp, url_prefix='/auth') # Rutas de autenticación (/auth/*)
    app.register_blueprint(solicitudes_bp, url_prefix='/solicitudes') # Rutas de solicitudes (/solicitudes/*)
    app.register_blueprint(ajustes_bp, url_prefix='/ajustes')         # Rutas de ajuste (/ajustes/*)
    app.register_blueprint(proyectos_bp, url_prefix='/proyectos')     # Rutas de proyectos (/proyectos/*)

    # Puedes añadir rutas de error personalizadas aquí (opcional)
    # @app.errorhandler(404)
    # def page_not_found(e):
    #     return render_template('404.html'), 404

    # Añadir el cliente Notion y el Serializer al contexto de la aplicación
    # para que los Blueprints puedan acceder a ellos sin importaciones circulares
    # o usando current_app.config
    # Ya lo guardamos directamente en app.notion_client arriba.
    # La config está en app.config.
    # El serializer s es global, pero accederlo desde Blueprints es mejor via current_app
    # Puedes hacer algo como:
    @app.before_request
    def before_request_stuff():
         # Ejemplo: Acceder a app.notion_client si necesitas usarlo globalmente
         pass # No necesitas hacer nada especial aquí solo para que current_app funcione

    # Añadir variables al contexto de la plantilla (opcional, si las usas en base.html por ejemplo)
    @app.context_processor
    def inject_user():
        # current_user ya se inyecta por Flask-Login, esto es solo un ejemplo
        return dict(current_user=current_user)


    # Retornar la instancia de la aplicación configurada
    return app

# NOTA: El bloque if __name__ == '__main__': CON app.run() ya NO va en este archivo.
# Tampoco va db.create_all(). La base de datos se maneja con Flask-Migrate.