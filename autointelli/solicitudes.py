# autointelli/solicitudes.py

from flask import Blueprint, request, jsonify, render_template, current_app # Importar current_app
from flask_login import login_required, current_user # Necesitas current_user
from .notion_utils import submit_request_for_material_logic # Reutiliza la lógica principal
from .models import db, AuditLog # Importar para auditoría si es necesario en el Blueprint
from .decorators import role_required # Importar el decorador

import logging

logger = logging.getLogger(__name__)

# Crear el Blueprint. Prefijo /solicitudes.
solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/solicitudes')

@solicitudes_bp.route('/')
@login_required
@role_required(['logistica', 'admin']) # Solo roles 'logistica' y 'admin' pueden acceder
def standard_material_request_page(): # Nombre de función descriptivo
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /solicitudes/ (Formulario Estándar)")
    # Renderiza la plantilla específica para el formulario estándar
    # Asegúrate de que la plantilla existe en templates/solicitudes/standard_request_form.html
    return render_template('solicitudes/standard_request_form.html')


@solicitudes_bp.route('/submit_standard', methods=['POST']) # Nueva ruta para submit estándar
@login_required
@role_required(['logistica', 'admin']) # Solo roles 'logistica' y 'admin' pueden enviar
def submit_standard_request(): # Nombre de función descriptivo
    logger.info(f"[{current_user.username}] Recibiendo solicitud de Materiales Estándar en /solicitudes/submit_standard")

    # Obtener el cliente Notion y los IDs de DB para materiales desde la configuración central
    notion_client = current_app.notion_client
    database_id_db1 = current_app.config.get('DATABASE_ID_MATERIALES_DB1')
    database_id_db2 = current_app.config.get('DATABASE_ID_MATERIALES_DB2')

    if notion_client is None or not database_id_db1 or not database_id_db2:
         error_msg = "La integración con Notion para Solicitudes (Estándar) no está configurada correctamente."
         logger.error(f"[{current_user.username}] {error_msg}")
         # Puedes añadir registro de auditoría si quieres aquí (importando db y AuditLog)
         return jsonify({"error": error_msg}), 503 # Service Unavailable

    # data ya viene como JSON del frontend (asumimos que el script JS lo recolecta y envía como JSON)
    data = request.get_json()
    if not data:
        logger.warning(f"[{current_user.username}] No se recibieron datos en submit_standard_request.")
        return jsonify({"error": "No se recibieron datos."}), 400

    # --- Validar datos mínimos para solicitud estándar en backend ---
    # Aunque el frontend valide, es buena práctica validar en backend también
    required_fields = ['nombre_solicitante', 'proveedor', 'departamento_area', 'fecha_solicitud', 'proyecto', 'cantidad_solicitada', 'tipo_material', 'nombre_material', 'unidad_medida']
    missing_fields = [field for field in required_fields if not data.get(field) or (isinstance(data.get(field), str) and not data.get(field).strip())]

    # Validar cantidad solicitada > 0 si está presente
    cantidad = data.get('cantidad_solicitada')
    if cantidad is not None and (not isinstance(cantidad, (int, float)) or cantidad <= 0):
         missing_fields.append('cantidad_solicitada (debe ser un número > 0)')

    if missing_fields:
         error_msg = f"Faltan campos obligatorios o son inválidos: {', '.join(missing_fields)}"
         logger.warning(f"[{current_user.username}] {error_msg}")
         return jsonify({"error": error_msg}), 400 # Bad Request

    # Asegúrate de que el diccionario data NO incluye 'torni_items'
    # (Aunque la lógica principal lo ignora si no es modo Torni, es más limpio no enviarlo)
    if 'torni_items' in data:
        del data['torni_items'] # Eliminar la clave si se envió por error


    # Llamar a la lógica principal de procesamiento, pasándole los datos estándar
    # La lógica principal detectará que NO es modo Torni porque data no tiene 'torni_items'
    response_data, status_code = submit_request_for_material_logic(
        notion_client,
        database_id_db1,
        database_id_db2,
        data, # Pasa el diccionario data solo con campos estándar
        user_id=current_user.id
    )

    # Nota: El logging y el registro de auditoría se hacen dentro de submit_request_for_material_logic

    return jsonify(response_data), status_code