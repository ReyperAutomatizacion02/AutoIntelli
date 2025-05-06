# autointelli/accesorios.py

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from .notion.solicitudes import submit_request_for_material_logic # Reutiliza la lógica principal
from .models import db, AuditLog # Importar para auditoría
from .decorators import role_required # Importar el decorador

import logging

logger = logging.getLogger(__name__)

# Crear el Blueprint. Prefijo /accesorios.
accesorios_bp = Blueprint('accesorios', __name__, url_prefix='/accesorios')


@accesorios_bp.route('/solicitar', methods=['GET']) # Ruta para el formulario Torni
@login_required
@role_required(['diseno', 'admin']) # Solo roles 'diseno' y 'admin' pueden acceder
def torni_accessories_request_page(): # Nombre de función descriptivo
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /accesorios/solicitar (Formulario Torni)")
    # Renderiza la plantilla específica para el formulario Torni
    # Asegúrate de que la plantilla existe en templates/accesorios/torni_request_form.html
    return render_template('accesorios/torni_request_form.html')


@accesorios_bp.route('/submit_torni', methods=['POST']) # Ruta para submit Torni
@login_required
@role_required(['diseno', 'admin']) # Solo roles 'diseno' y 'admin' pueden enviar
def submit_torni_accessories_request(): # Nombre de función descriptivo
    logger.info(f"[{current_user.username}] Recibiendo solicitud de Accesorios Torni en /accesorios/submit_torni")

    # Obtener el cliente Notion y los IDs de DB para materiales desde la configuración central
    notion_client = current_app.notion_client
    database_id_db1 = current_app.config.get('DATABASE_ID_MATERIALES_DB1')
    database_id_db2 = current_app.config.get('DATABASE_ID_MATERIALES_DB2')

    if notion_client is None or not database_id_db1 or not database_id_db2:
         error_msg = "La integración con Notion para Solicitudes (Torni) no está configurada correctamente."
         logger.error(f"[{current_user.username}] {error_msg}")
         # Puedes añadir registro de auditoría si quieres aquí (importando db y AuditLog)
         return jsonify({"error": error_msg}), 503 # Service Unavailable

    # data ya viene como JSON del frontend (asumimos que el script JS lo recolecta y envía como JSON)
    data = request.get_json()
    if not data:
        logger.warning(f"[{current_user.username}] No se recibieron datos en submit_torni_accessories_request.")
        return jsonify({"error": "No se recibieron datos."}), 400

    # --- Validar datos para solicitud Torni en backend ---
    # Validar campos comunes requeridos (puedes copiarlos de la lista en solicitudes.py, excepto los estándar específicos)
    # Y validar que la lista 'torni_items' existe y no está vacía
    required_common_fields = ['nombre_solicitante', 'proveedor', 'departamento_area', 'fecha_solicitud', 'Proyecto'] # 'proveedor' debería ser 'Torni'
    missing_common_fields = [field for field in required_common_fields if not data.get(field) or (isinstance(data.get(field), str) and not data.get(field).strip())]

    # Validar que el proveedor sea 'Torni' (opcional si el formulario solo permite Torni)
    if data.get('proveedor') != 'Torni':
         missing_common_fields.append("proveedor (debe ser 'Torni' para este formulario)")

    # Validar la lista de items Torni
    torni_items_list = data.get('torni_items')
    if not isinstance(torni_items_list, list) or not torni_items_list:
         # Añadir un mensaje a missing_common_fields o manejarlo como un error separado
         # Depende de cómo quieras reportar el error en el frontend
         missing_common_fields.append("productos Torni (debe añadir al menos un producto válido)") # Añadir error a la lista

    # Si hay campos comunes faltantes O la lista de items Torni está vacía/inválida
    if missing_common_fields:
         error_msg = f"Faltan campos obligatorios o son inválidos: {', '.join(missing_common_fields)}"
         logger.warning(f"[{current_user.username}] {error_msg}")
         return jsonify({"error": error_msg}), 400 # Bad Request

    # Validar cada item dentro de la lista torni_items_list
    # Esto es una validación más detallada que la de existencia de la lista
    invalid_item_indices = []
    for index, item in enumerate(torni_items_list):
        if not isinstance(item, dict) or not item.get('quantity') or not item.get('id') or not item.get('description') or item.get('quantity') <= 0 or not str(item.get('id')).strip() or not str(item.get('description')).strip():
             invalid_item_indices.append(index + 1) # Reportar el índice del item inválido

    if invalid_item_indices:
         error_msg = f"Items Torni inválidos o incompletos encontrados (Cantidad > 0, ID y Descripción obligatorios): {', '.join(map(str, invalid_item_indices))}"
         logger.warning(f"[{current_user.username}] {error_msg}")
         return jsonify({"error": error_msg}), 400 # Bad Request


    # Si la validación pasa, asegurarse de que el proveedor es Torni en los datos procesados
    # para que la lógica principal en notion_utils sepa cómo procesarlo
    data['proveedor'] = 'Torni'


    # Llamar a la lógica principal de procesamiento
    # La lógica principal detectará que es modo Torni porque data tiene 'proveedor' = 'Torni'
    # y la clave 'torni_items' con una lista (ya validamos que existe y no está vacía)
    response_data, status_code = submit_request_for_material_logic(
        notion_client,
        database_id_db1,
        database_id_db2,
        data, # Pasa el diccionario data con los campos comunes y 'torni_items'
        user_id=current_user.id
    )

    # Nota: El logging y el registro de auditoría se hacen dentro de submit_request_for_material_logic

    return jsonify(response_data), status_code