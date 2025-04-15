# coding: utf-8

# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os  # Importado para acceder a variables de entorno.
from datetime import datetime  # Importado para manejar fechas.
import mH2 as moverHorarios02  # Importa el script que define la función para mover horarios.
from flask_migrate import Migrate  # Import Flask-Migrate
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer # Para generar tokens seguros
from flask_mail import Mail, Message # Importa Flask-Mail
from email_validator import validate_email, EmailNotValidError # Importa la librería para validar el email
from itsdangerous import URLSafeTimedSerializer # Para generar tokens seguros
from flask_mail import Mail, Message # Importa Flask-Mail
from flask_cors import CORS  # Añadir CORS
from notion_client import Client # Añadir Notion Client
import json # Añadir json
import traceback # Añadir traceback

# Cargar variables de entorno
load_dotenv()

# =====================
# Creación de app Flask
# =====================
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') # Reemplaza 'una_clave...' por una clave real y segura.

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'reyper.automatizacion.2@gmail.com'
app.config['MAIL_PASSWORD'] = 'rcvw vkkw yecp qivn'
app.config['MAIL_DEFAULT_SENDER'] = 'reyper.automatizacion.2@gmail.com'
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID") # ID DB 1
DATABASE_ID_2 = os.environ.get("DATABASE_ID_2") # ID DB 2

mail = Mail(app) # Inicializa Flask-Mail

s = URLSafeTimedSerializer(app.config['SECRET_KEY']) # Inicializa el serializador

# Configuración de la base de datos (SQLite en este caso)
basedir = os.path.abspath(os.path.dirname(__file__)) # Obtiene el directorio base de la app
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gerry:YIRUsyZ8le1QbXwPsRUcOQDV3lWqrerw@dpg-cvq1fk24d50c73c0tesg-a.oregon-postgres.render.com/dbautointelli' # Usar la External Database URL de Render directamente
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Desactiva el tracking de modificaciones de SQLAlchemy (opcional, pero recomendado para evitar warnings)

# Validar credenciales de Notion
if not NOTION_TOKEN or not DATABASE_ID or not DATABASE_ID_2:
    print("FATAL ERROR: Variables de entorno Notion (TOKEN, ID, ID_2) no configuradas.")
    # Considera un manejo más robusto que 'exit(1)' en una app web,
    # quizás deshabilitar las rutas de Notion o mostrar un error.
    notion = None # Marcar como no inicializado
else:
    # Inicializar cliente Notion
    try:
        notion = Client(auth=NOTION_TOKEN)
        print("Cliente de Notion inicializado.")
    except Exception as e:
        print(f"FATAL ERROR al inicializar Notion Client: {e}")
        notion = None # Marcar como no inicializado
# --- Fin Configuración Notion ---

db = SQLAlchemy(app) # Inicializa Flask-SQLAlchemy
migrate = Migrate(app, db) # Initialize Flask-Migrate with your app and db instance

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Define la función (ruta) a la que redirigir si se requiere login

# Función para cargar usuario (requerida por Flask-Login)
@login_manager.user_loader # 4. Decorar load_user *después* de inicializar login_manager
def load_user(user_id):
    return User.query.get(int(user_id)) # Busca usuario por ID en la base de datos

# Clase de Usuario (Modelo de Base de Datos)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # Clave primaria, autoincremental
    username = db.Column(db.String(100), unique=True, nullable=False) # Nombre de usuario, único, no puede ser nulo
    password = db.Column(db.String(200), nullable=False) # Contraseña (¡Recuerda que luego usaremos HASHING, esto es solo un ejemplo inicial!)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Agrega el campo de correo electrónico

    def __init__(self, username, password, email):  # Constructor para crear objetos User
        self.username = username
        self.password = password
        self.email = email

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True) # ID único del registro de auditoría
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Fecha y hora de la acción
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # ID del usuario que realizó la acción (clave foránea a la tabla 'user')
    action = db.Column(db.String(200), nullable=False) # Descripción de la acción realizada
    details = db.Column(db.Text) # Detalles adicionales sobre la acción (puedes ser JSON, texto, etc.)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True)) # Relación con el modelo User para acceder al usuario que realizó la acción

    def __repr__(self):
        username = "Usuario Desconocido" # Default username if user is None
        if self.user: # Check if self.user is not None
            username = self.user.username # Use actual username if user exists

        return f'<AuditLog {self.id} - User: {username} - Action: {self.action} - Timestamp: {self.timestamp}>'

# ===========================================
# Definición de la ruta / (página principal):
# ===========================================
@app.route('/')                          
def index():                             
    return render_template('index.html')  # Renderiza el archivo index.html. 

@app.route('/login', methods=['GET', 'POST'])

# Ruta para la página de login
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first() # Busca usuario por username en la base de datos

        if user and check_password_hash(user.password, password): # ¡VERIFICACIÓN CON HASHING!
            login_user(user) # Iniciar sesión del usuario
            flash('Login exitoso.', 'success') # Mensaje flash (opcional)
            next_page = request.args.get('next') # Obtener parámetro 'next' para redirección después de login
            return redirect(next_page or url_for('index')) # Redirigir a 'index' o a la página solicitada antes del login
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger') # Mensaje flash de error (opcional)

    return render_template('login.html') # Renderizar formulario de login (login.html)

# Ruta para la página de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email'] # Obtiene el correo electrónico del formulario

        if not username or not password or not confirm_password or not email:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')
        
        try:
            # Valida el formato del correo electrónico
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

        hashed_password = generate_password_hash(password) # Hashea la contraseña
        new_user = User(username=username, password=hashed_password, email=email) # ¡RECUERDA: Contraseña en texto plano solo para ejemplo inicial!
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login')) # Redirigir a la página de login después del registro

    return render_template('register.html') # Renderizar formulario de registro (register.html)

# Ruta para el logout
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

        user = User.query.filter_by(username=username, email=email).first()

        if user:
            token = s.dumps(user.email, salt='recover-key')
            link = url_for('reset_password', token=token, _external=True)
            print(f"Reset password link: {link}") # Log the reset password link

            # Store the token in the database
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

    # Verify that the token has not been used before
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

        user = User.query.filter_by(email=email).first()

        if user:
            hashed_password = generate_password_hash(password)
            user.password = hashed_password

            # Delete the token from the database
            db.session.delete(audit_log)
            db.session.commit()

            flash('La contraseña se ha restablecido correctamente.', 'success')
            return redirect(url_for('login'))
        else:
            flash('El enlace para restablecer la contraseña es inválido.', 'danger')
            return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)

@app.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        from nuevosRegistros import crear_proyecto, crear_partidas  # Importa las funciones aquí para evitar problemas de dependencia circular
        nombre_proyecto = request.form['nombre_proyecto']
        num_partidas = int(request.form['num_partidas'])

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

@app.route('/adjust_dates', methods=['GET'])
@login_required
def adjust_dates():
    return render_template('adjust_dates.html')

# ======================================================================
@app.route('/run_script', methods=['GET', 'POST'])
@login_required

def run_script():
    if request.method == 'GET':
        return redirect(url_for('adjust_dates'))
    print("DEBUG: Inicio de la función run_script()")
    try:
        print("DEBUG: Dentro del bloque try")
        hours_to_adjust = int(request.form.get("hours"))  # Nombre más descriptivo para la variable

        # Verificar si el checkbox 'move_backward' está marcado
        move_backward = request.form.get("move_backward") == 'on' # Devuelve True si está marcado, False si no

        # Ajustar las horas para restar si el checkbox está marcado
        hours = hours_to_adjust if not move_backward else - hours_to_adjust
 
        start_date_str = request.form.get("start_date")
        if not start_date_str:
            return jsonify({"error": "Debes seleccionar una fecha"}), 400
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        # Recoger los filtros del formulario
        property_filters = {}
        property_name_1 = request.form.get("property_name_1")
        property_value_1 = request.form.get("property_value_1")
        property_name_2 = request.form.get("property_name_2")
        property_value_2 = request.form.get("property_value_2")

        # Construir diccionario de filtros solo si se proporcionaron valores
        if property_name_1 and property_value_1:
            property_filters[property_name_1] = property_value_1
        if property_name_2 and property_value_2:
            property_filters[property_name_2] = property_value_2

        # Llamar a la función adjust_dates_api con los filtros
        result_dict = moverHorarios02.adjust_dates_api(hours, start_date_str, property_filters=property_filters)

        # *** LOGGING current_user ***
        print(f"*** run_script: current_user = {current_user}, current_user.id = {current_user.id if current_user else None}") # Log current_user and current_user.id
        # *** FIN LOGGING current_user ***

        # *** PRUEBA DE PERSISTENCIA - ESCRITURA ***
        print("DEBUG: Intentando escribir registro de prueba de persistencia...") # NUEVO LOGGING - PRUEBA PERSISTENCIA ESCRITURA
        prueba_persist_log = AuditLog(
            user_id=current_user.id,
            action='PRUEBA DE PERSISTENCIA - ESCRITURA', # Acción especial para prueba
            details='Este es un registro de prueba para verificar persistencia en Render'
        )
        db.session.add(prueba_persist_log)
        # *** FIN PRUEBA DE PERSISTENCIA - ESCRITURA ***

        # *** LOGGING current_user ***
        print(f"*** run_script: current_user = {current_user}, current_user.id = {current_user.id if current_user else None}") # Log current_user and current_user.id
        # *** FIN LOGGING current_user ***

        # *** REGISTRO DE AUDITORÍA CON LOGGING DETALLADO ***
        print("DEBUG: Antes de crear objeto AuditLog") # NUEVO LOGGING - ANTES DE CREAR AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action='Ajuste de Horarios',
            details=f'Horas ajustadas: {hours}, Fecha de inicio: {start_date_str}, Filtros: {property_filters}, Resultado API: {result_dict}'
        )
        print("DEBUG: Después de crear objeto AuditLog") # NUEVO LOGGING - DESPUÉS DE CREAR AuditLog
        db.session.add(audit_log)
        print("DEBUG: Después de db.session.add(audit_log), ANTES de commit") # NUEVO LOGGING - DESPUÉS DE ADD, ANTES DE COMMIT
        print(f"*** INTENTANDO HACER COMMIT DEL REGISTRO DE AUDITORÍA: {audit_log}") # LOGGING ANTES DEL COMMIT (YA EXISTENTE)
        db.session.commit()
        print("*** COMMIT DEL REGISTRO DE AUDITORÍA EXITOSO") # LOGGING DESPUÉS DEL COMMIT (YA EXISTENTE)
        print("DEBUG: Después de db.session.commit()") # NUEVO LOGGING - DESPUÉS DE COMMIT
        # *** FIN REGISTRO DE AUDITORÍA CON LOGGING DETALLADO ***

        # *** PRUEBA DE PERSISTENCIA - LECTURA ***
        print("DEBUG: Intentando leer registro de prueba de persistencia...") # NUEVO LOGGING - PRUEBA PERSISTENCIA LECTURA
        prueba_persist_leido = AuditLog.query.filter_by(action='PRUEBA DE PERSISTENCIA - ESCRITURA').first() # Busca registro de prueba
        if prueba_persist_leido:
            print("DEBUG: Registro de prueba de persistencia LEÍDO exitosamente de la base de datos en Render!") # LOGGING - PRUEBA PERSISTENCIA LECTURA ÉXITO
        else:
            print("DEBUG: NO SE ENCONTRÓ registro de prueba de persistencia en la base de datos en Render!") # LOGGING - PRUEBA PERSISTENCIA LECTURA FALLO
        # *** FIN PRUEBA DE PERSISTENCIA - LECTURA ***

        if result_dict.get("success"):
            return jsonify({"message": result_dict.get("message")})
        else:
            return jsonify({"error": result_dict.get("error")}), 500

    except Exception as e:
        print(f"*** ERROR en run_script: {e}") # Imprime el mensaje de error básico
        import traceback # Importa la librería traceback
        traceback.print_exc() # Imprime el traceback completo del error
        return jsonify({"error": str(e)}), 500

# ========= RUTAS PARA NOTION REQUEST TOOL =========

@app.route('/notion-request') # <- CAMBIADA LA RUTA de '/'
@login_required # <- AÑADIDO: Requerir login para acceder
def notion_request_index(): # <- CAMBIADO NOMBRE de la función
    print("Solicitud GET recibida en /notion-request")
    # Renderiza el archivo HTML renombrado
    return render_template('request_for_material.html')

@app.route('/submit-request', methods=['POST']) # <- RUTA MANTENIDA (probablemente única)
@login_required # <- AÑADIDO: Requerir login para enviar
def submit_notion_request(): # <- CAMBIADO NOMBRE de la función
    # --- INICIO DEL CÓDIGO COPIADO DE LA FUNCIÓN submit_request DE LA HERRAMIENTA ---
    folio_solicitud = None
    status_code = 500
    error_occurred = False
    items_processed_count = 0
    items_failed_count = 0
    first_page1_url = None
    first_page2_url = None

    # Verificar si el cliente Notion se inicializó correctamente
    if notion is None:
         print("ERROR: El cliente de Notion no está inicializado. No se puede procesar la solicitud.")
         return jsonify({"error": "La integración con Notion no está configurada correctamente."}), 503 # Service Unavailable

    print("\n--- Recibiendo nueva solicitud Notion ---")
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No se recibieron datos."}), 400
        print("Datos recibidos:", json.dumps(data, indent=2, ensure_ascii=False))

        selected_proveedor = data.get("proveedor")
        torni_items = data.get('torni_items')
        # Generar Folio único si no viene
        folio_solicitud = data.get("folio_solicitud", f"EMG-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")
        print(f"--- Procesando Folio Notion: {folio_solicitud} ---")

        # --- Propiedades Comunes ---
        common_properties = {}
        # ... (COPIA EXACTA de la lógica de common_properties del app.py de la herramienta) ...
        if data.get("nombre_solicitante"): common_properties["Nombre del solicitante"] = {"select": {"name": data["nombre_solicitante"]}}
        if selected_proveedor: common_properties["Proveedor"] = {"select": {"name": selected_proveedor}}
        if data.get("departamento_area"): common_properties["Departamento/Área"] = {"select": {"name": data["departamento_area"]}}
        if data.get("fecha_solicitud"): common_properties["Fecha de solicitud"] = {"date": {"start": data["fecha_solicitud"]}}
        if folio_solicitud: common_properties["Folio de solicitud"] = {"rich_text": [{"type": "text", "text": {"content": folio_solicitud}}]}
        if data.get("Proyecto"): common_properties["Proyecto"] = {"rich_text": [{"type": "text", "text": {"content": data["Proyecto"]}}]}
        if data.get("especificaciones_adicionales"): common_properties["Especificaciones adicionales"] = {"rich_text": [{"type": "text", "text": {"content": data["especificaciones_adicionales"]}}]}

        # --- Lógica Condicional ---
        items_to_process = torni_items if selected_proveedor == 'Torni' and isinstance(torni_items, list) else [data]
        is_torni_mode = selected_proveedor == 'Torni'

        if not items_to_process or (is_torni_mode and len(items_to_process) == 0):
             return jsonify({"error": "No hay items para procesar."}), 400

        for index, item_data in enumerate(items_to_process):
            # ... (COPIA EXACTA de toda la lógica DENTRO DEL BUCLE for del app.py de la herramienta) ...
            # ... (Incluyendo la creación de item_properties, llamadas a notion.pages.create, etc.) ...
            item_index_str = f"Item {index + 1}" if is_torni_mode else "Item Único"
            print(f"--- Procesando {item_index_str} ---")
            item_properties = common_properties.copy()

            # --- Construir Propiedades COMPLETAS para este item ---
            if is_torni_mode:
                 try: quantity = int(item_data.get("quantity", 0)); item_properties["Cantidad solicitada"] = {"number": quantity if quantity > 0 else 0}
                 except (ValueError, TypeError): item_properties["Cantidad solicitada"] = {"number": 0}
                 item_id = str(item_data.get("id", "")).strip(); item_desc = str(item_data.get("description", "")).strip()
                 if item_id: item_properties["ID de producto"] = {"rich_text": [{"type": "text", "text": {"content": item_id}}]}
                 if item_desc: item_properties["Descripción"] = {"rich_text": [{"type": "text", "text": {"content": item_desc}}]}
            else: # Proveedor estándar
                 if item_data.get("cantidad_solicitada") is not None:
                    try: item_properties["Cantidad solicitada"] = {"number": int(item_data["cantidad_solicitada"])}
                    except (ValueError, TypeError): item_properties["Cantidad solicitada"] = {"number": 0}
                 if item_data.get("tipo_material"): item_properties["Tipo de material"] = {"select": {"name": item_data["tipo_material"]}}
                 if item_data.get("nombre_material"): item_properties["Nombre del material"] = {"select": {"name": item_data["nombre_material"]}}
                 if item_data.get("unidad_medida"): item_properties["Unidad de medida"] = {"select": {"name": item_data["unidad_medida"]}}
                 if item_data.get("largo"): item_properties["Largo (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["largo"])}}]}
                 if item_data.get("ancho"): item_properties["Ancho (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["ancho"])}}]}
                 if item_data.get("alto"): item_properties["Alto (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["alto"])}}]}
                 if item_data.get("diametro"): item_properties["Diametro (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["diametro"])}}]}

            print(f"\n  --- DEBUG: Propiedades FINALES para Notion ({item_index_str}) ---");
            try: print(json.dumps(item_properties, indent=2, ensure_ascii=False))
            except Exception as json_e: print(f"  Error imprimiendo JSON: {json_e}", item_properties)

            # --- Crear página en DB 1 ---
            page1_created = False; error1_details = None; page1_url_current = None
            try:
                print(f"  Intentando crear página en DB 1 ({DATABASE_ID})...")
                response1 = notion.pages.create(parent={"database_id": DATABASE_ID}, properties=item_properties)
                page1_url_current = response1.get("url")
                if index == 0: first_page1_url = page1_url_current
                print(f"  Página creada en DB 1: {page1_url_current}")
                page1_created = True
            except Exception as e1: error1_details = str(e1); print(f"ERROR en DB 1 ({item_index_str}): {error1_details}")

            # --- Crear página en DB 2 ---
            page2_created = False; error2_details = None; page2_url_current = None
            try:
                print(f"  Intentando crear página en DB 2 ({DATABASE_ID_2})...")
                response2 = notion.pages.create(parent={"database_id": DATABASE_ID_2}, properties=item_properties)
                page2_url_current = response2.get("url")
                if index == 0: first_page2_url = page2_url_current
                print(f"  Página creada en DB 2: {page2_url_current}")
                page2_created = True
            except Exception as e2: error2_details = str(e2); print(f"ERROR en DB 2 ({item_index_str}): {error2_details}")

            # Registrar si hubo algún fallo
            if not page1_created or not page2_created: error_occurred = True; items_failed_count += 1
            else: items_processed_count += 1
        # --- Fin del bucle ---

        # --- Construir Respuesta Final ---
        # ... (COPIA EXACTA de la lógica de respuesta final del app.py de la herramienta) ...
        status_code = 200
        final_response = {}
        if items_processed_count > 0 and not error_occurred:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count} item(s)) registrada en ambas DBs."
             final_response["notion_url"] = first_page1_url
             final_response["notion_url_db2"] = first_page2_url
        elif items_processed_count > 0 and error_occurred:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count} OK, {items_failed_count} fallaron. Ver logs."
             final_response["notion_url"] = first_page1_url
             status_code = 207 # Partial Content
        else:
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado. Ver logs."
             status_code = 500

        print(f"--- Procesamiento Notion completado para Folio {folio_solicitud}. Resultado: {final_response} ---")
        return jsonify(final_response), status_code

    # --- Manejo de Errores Generales ---
    except Exception as e:
        error_message = str(e)
        print(f"\n--- ERROR INESPERADO en submit_notion_request (Folio: {folio_solicitud or 'NO ASIGNADO'}) ---")
        print(traceback.format_exc())
        print(f"--- FIN ERROR ---")
        return jsonify({"error": "Error inesperado al procesar la solicitud Notion.", "details": error_message}), 500
    # --- FIN DEL CÓDIGO COPIADO ---

# ========= FIN RUTAS NOTION REQUEST TOOL =========

# ================================
# Ejecución de la aplicación Flask
# ================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea la base de datos y tablas (si no existen)
        print("Base de datos y tablas creadas (si no existían).")

        # *** CREACIÓN DE USUARIOS DE EJEMPLO EN LA BASE DE DATOS (SOLO LA PRIMERA VEZ) ***
        # Comprobar si ya existen usuarios en la base de datos
        if User.query.count() == 0: # Si no hay usuarios en la base de datos...
            print("No se encontraron usuarios en la base de datos. Creando usuarios de ejemplo...")
            # Crear usuarios de ejemplo y añadirlos a la base de datos
            hashed_password_admin = generate_password_hash('password123') # Hashea la contraseña de admin
            hashed_password_usuario = generate_password_hash('password456') # Hashea la contraseña de usuario
            user_admin = User(username='admin', password=hashed_password_admin, email='admin@example.com') # Guarda el hash de admin
            user_usuario = User(username='usuario', password=hashed_password_usuario, email='usuario@example.com') # Guarda el hash de usuario
            db.session.add(user_admin) # Añade el objeto usuario a la sesión de base de datos
            db.session.add(user_usuario) # Añade el objeto usuario a la sesión de base de datos
            db.session.commit() # ¡Guarda los cambios en la base de datos!
            print("Usuarios de ejemplo 'admin' y 'usuario' creados en la base de datos.")
        else:
            print("Ya existen usuarios en la base de datos. Omitiendo creación de usuarios de ejemplo.")
        # *** FIN DE CREACIÓN DE USUARIOS DE EJEMPLO ***
        
    port = int(os.environ.get('PORT', 5000)) # Lee la variable PORT de entorno, si no existe usa 5000 por defecto (local)
    app.run(host='0.0.0.0', port=port, debug=True)

    with app.app_context():
        users = User.query.all()
        for user in users:
            if not user.email:
                user.email = f'{user.username}@example.com'
        db.session.commit()
