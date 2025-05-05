# autointelli/solicitudes.py

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
# Importa la función de lógica de submit principal
from .notion_utils import submit_request_for_material_logic, list_available_properties # Importa list_available_properties si la usas en este archivo
# from .models import db, AuditLog
from .decorators import role_required # Importar el decorador

import logging

logger = logging.getLogger(__name__)

# Crear el Blueprint. Prefijo /solicitudes.
solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/solicitudes')

@solicitudes_bp.route('/')
@login_required
@role_required(['logistica', 'admin'])
def standard_material_request_page():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /solicitudes/ (Formulario Estándar)")
    # Los IDs de base de datos se obtienen en el backend POST endpoint (submit_standard_request)
    # y se usan en notion_utils. No necesitas pasarlos a la plantilla HTML.
    return render_template('solicitudes/standard_request_form.html')


@solicitudes_bp.route('/submit_standard', methods=['POST'])
@login_required
@role_required(['logistica', 'admin'])
def submit_standard_request():
    logger.info(f"[{current_user.username}] Recibiendo solicitud de Materiales Estándar en /solicitudes/submit_standard")

    # Obtener el cliente Notion y los IDs de DB desde la configuración de Flask
    notion_client = current_app.notion_client
    database_id_db1 = current_app.config.get('DATABASE_ID_MATERIALES_DB1')
    database_id_db2 = current_app.config.get('DATABASE_ID_MATERIALES_DB2')
    # *** NUEVO: Obtener ID de la BD de Proyectos de la configuración ***
    database_id_proyectos = current_app.config.get('DATABASE_ID_PROYECTOS')
    # *** FIN NUEVO ***

    # *** VALIDACIÓN DE IDs DE BASE DE DATOS (AHORA INCLUYE PROYECTOS) ***
    if notion_client is None or not database_id_db1 or not database_id_db2 or not database_id_proyectos: # <<<< Incluye database_id_proyectos
         error_msg = "La integración con Notion para Solicitudes o Proyectos no está configurada correctamente (IDs o cliente faltante)."
         logger.error(f"[{current_user.username}] {error_msg}")
         return jsonify({"error": error_msg}), 503 # Service Unavailable

    data = request.get_json()

    # --- DEBUG: Log de datos recibidos en la ruta Flask ---
    current_app.logger.debug(f"[{current_user.username}] Datos JSON recibidos para solicitud estándar en ruta Flask: {data}")
    # --- Fin Debugging ---


    if not data:
        logger.warning(f"[{current_user.username}] No se recibieron datos en submit_standard_request.")
        return jsonify({"error": "No se recibieron datos."}), 400

    # --- Validaciones backend mínimas (solo campos requeridos básicos por seguridad) ---
    # La validación detallada de dimensiones y conflictos se realiza en notion_utils.py
    # 'proveedor', 'departamento_area' are from hidden fields, assumed present.
    # 'fecha_solicitud' is readonly set by JS, assumed present and in format YYYY-MM-DD.
    # 'tipo_material' is set by JS based on material, assumed present if material is selected.
    # 'proyecto' is validated for existence in Notion within notion_utils.py.
    # 'especificaciones_adicionales' is optional.
    required_fields_basic = ['nombre_solicitante', 'cantidad_solicitada', 'nombre_material', 'unidad_medida']
    missing_fields_basic = []

    for field in required_fields_basic:
        value = data.get(field)
        # Check for None or empty string after strip
        if value is None or (isinstance(value, str) and not value.strip()):
             missing_fields_basic.append(field)

    # Validación específica para cantidad > 0 (si está presente)
    cantidad = data.get('cantidad_solicitada')
    if cantidad is not None and (not isinstance(cantidad, (int, float)) or cantidad <= 0):
        # Si cantidad estaba en missing_fields_basic por estar vacía, la removemos antes de añadir el mensaje específico.
        if 'cantidad_solicitada' in missing_fields_basic:
             missing_fields_basic.remove('cantidad_solicitada')
        missing_fields_basic.append('cantidad_solicitada (debe ser un número > 0)')


    if missing_fields_basic:
         error_msg = f"Faltan campos obligatorios o son inválidos: {', '.join(missing_fields_basic)}"
         logger.warning(f"[{current_user.username}] {error_msg}")
         return jsonify({"error": error_msg}), 400 # Bad Request


    # La validación de dimensiones (conjunto completo, conflicto) y la existencia del proyecto en Notion
    # se manejan dentro de submit_request_for_material_logic.


    # Asegúrate de que el diccionario data NO incluye 'torni_items' si no es modo Torni.
    # Esto es para asegurar que submit_request_for_material_logic procesa correctamente
    # el modo estándar cuando no hay items Torni. Aunque notion_utils lo gestiona,
    # es una capa de seguridad adicional si los datos del frontend fueran mixtos por error.
    is_torni_mode = data.get("proveedor") == 'Torni'
    if not is_torni_mode and 'torni_items' in data:
         del data['torni_items']
         logger.warning(f"[{current_user.username}] Campo 'torni_items' encontrado en modo no Torni. Eliminado antes de pasar a lógica principal.")


    # --- DEBUG: Imprimir los datos que se pasarán a Notion (ya estaba) ---
    current_app.logger.debug(f"[{current_user.username}] Pasando datos a submit_request_for_material_logic: {data}")
    # --- Fin Debugging ---


    # Llamar a la lógica principal de procesamiento en notion_utils, pasándole todos los IDs necesarios
    response_data, status_code = submit_request_for_material_logic(
        notion_client,
        database_id_db1,
        database_id_db2,
        database_id_proyectos, # <<<< PASAR EL ID DE PROYECTOS AQUÍ <<<<
        data, # Pasar el diccionario data completo (con todos los campos recolectados del frontend)
        user_id=current_user.id # Asegúrate de pasar el user_id si la función lo usa para auditoría, etc.
    )

    # La respuesta del backend (response_data y status_code) proviene de submit_request_for_material_logic
    # Incluye folio_solicitud, message/warning/error, notion_url, notion_url_db2

    return jsonify(response_data), status_code

# ... (resto de rutas si las tienes) ...