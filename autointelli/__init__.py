# autointelli/__init__.py

import os
from flask import Flask, current_app # Importar current_app si lo necesitas en la fábrica
# Importar la instancia *única* de db desde models.py
from .models import db # <<< Importa la instancia db de models.py

# Importar las otras extensiones
from flask_login import LoginManager, current_user # Importar current_user para user_loader
from flask_migrate import Migrate
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
from notion_client import Client

# Inicializar otras extensiones (db ya está importada, no la crees aquí)
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

# Serializer (se inicializará con SECRET_KEY)
s = URLSafeTimedSerializer("default_secret_key") # Valor temporal


def create_app():
    load_dotenv()

    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    
    app = Flask(__name__,
                instance_relative_config=True,
                template_folder=template_dir,
                static_folder=static_dir
               )

    # --- Configuración de la Aplicación ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una_clave_secreta_por_defecto_muy_segura_cambiar_en_produccion')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        print("ERROR FATAL: DATABASE_URL no configurada. La aplicación no puede iniciar.")

    # Configuración de Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465)) if os.environ.get('MAIL_PORT') else 465
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
         print("ADVERTENCIA: Configuración de correo incompleta. La funcionalidad de correo no funcionará.")

    # Configuración de Notion
    app.config['NOTION_API_KEY'] = os.environ.get("NOTION_API_KEY")
    app.config['DATABASE_ID_PROYECTOS'] = os.environ.get("DATABASE_ID_PROYECTOS")
    app.config['DATABASE_ID_PARTIDAS'] = os.environ.get("DATABASE_ID_PARTIDAS")
    app.config['DATABASE_ID_PLANES'] = os.environ.get("DATABASE_ID_PLANES")
    app.config['DATABASE_ID_MATERIALES_DB1'] = os.environ.get("DATABASE_ID")
    app.config['DATABASE_ID_MATERIALES_DB2'] = os.environ.get("DATABASE_ID_2")

    # Inicializar Cliente Notion y guardarlo en la instancia de app
    app.notion_client = None
    if app.config.get('NOTION_API_KEY'):
         print("DEBUG: NOTION_API_KEY encontrada en config, intentando inicializar Notion Client...") 
         try:
              app.notion_client = Client(auth=app.config['NOTION_API_KEY'])
              print("DEBUG: Cliente de Notion inicializado.")
         except Exception as e:
              print(f"DEBUG: ERROR al inicializar Notion Client: {e}") 
              app.notion_client = None
    else:
          print("DEBUG: NOTION_API_KEY NO encontrada en config. Cliente de Notion no inicializado.")

    # --- Inicializar Extensiones con la App ---
    # Usar la instancia db IMPORTADA de models.py
    db.init_app(app) # <<< CORRECTO: Inicializa la instancia importada

    migrate.init_app(app, db) # migrate también necesita la instancia db
    login_manager.init_app(app)
    mail.init_app(app)

    app.mail = mail

    # Actualizar el serializer con la SECRET_KEY de la app configurada
    global s # Acceder a la variable global s
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    app.url_serializer = s # Guardar en la app para fácil acceso desde Blueprints


    # Configuración de Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'

    # Configurar la función user_loader
    @login_manager.user_loader
    def load_user(user_id):
        # Importar User DENTRO de la función user_loader es una buena práctica
        # para evitar importaciones circulares si User necesitara db en su definición.
        # Sin embargo, con la estructura db = SQLAlchemy() en models.py
        # y la importación de db y Modelos al inicio de Blueprints,
        # importar User al inicio del Blueprint y usar User.query suele funcionar.
        # Mantener la importación aquí también es válido.
        from .models import User
        try:
            # db.session es accesible dentro de un contexto de solicitud/aplicación
            return db.session.get(User, int(user_id)) # Usa la instancia db IMPORTADA
        except (ValueError, TypeError):
             return None


    # --- Registrar Blueprints ---
    from .auth import auth_bp
    from .solicitudes import solicitudes_bp
    from .ajustes import ajustes_bp
    from .proyectos import proyectos_bp
    from .main_routes import main_bp
    from .accesorios import accesorios_bp
    from .almacen import almacen_bp
    from .ventas import ventas_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(solicitudes_bp, url_prefix='/solicitudes')
    app.register_blueprint(ajustes_bp, url_prefix='/ajustes')
    app.register_blueprint(proyectos_bp, url_prefix='/proyectos')
    app.register_blueprint(accesorios_bp, url_prefix='/accesorios')
    app.register_blueprint(almacen_bp, url_prefix='/almacen')
    app.register_blueprint(ventas_bp, url_prefix='/ventas') 

    # Retornar la instancia de la aplicación configurada
    return app