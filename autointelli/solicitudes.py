# autointelli/solicitudes.py

from flask import Blueprint, request, jsonify, render_template, current_app # Importar current_app
from flask_login import login_required, current_user # Necesitas current_user para auditoría y logging
# Importar la lógica de submit desde notion_utils
from .notion_utils import submit_request_for_material_logic
# Importar db y AuditLog si quieres registrar auditoría DENTRO de este Blueprint
# from .models import db, AuditLog # Puedes importarlos si los necesitas aquí

import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /solicitudes.
solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/solicitudes')


@solicitudes_bp.route('/')
@login_required
def request_for_material_index():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /solicitudes/")
    # Renderiza la plantilla específica para esta herramienta, usando un subdirectorio
    return render_template('solicitudes/request_for_material.html') # Asume templates/solicitudes/request_for_material.html


@solicitudes_bp.route('/submit', methods=['POST'])
@login_required
def submit_request_for_material():
    logger.info(f"[{current_user.username}] Recibiendo nueva solicitud de Materiales en /solicitudes/submit")

    # Obtener el cliente Notion y los IDs de DB desde la configuración central de la app
    notion_client = current_app.notion_client # Acceder a la instancia guardada en la fábrica
    database_id_db1 = current_app.config.get('DATABASE_ID_MATERIALES_DB1')
    database_id_db2 = current_app.config.get('DATABASE_ID_MATERIALES_DB2')


    # Verificar si la integración con Notion está configurada
    if notion_client is None or not database_id_db1 or not database_id_db2:
         error_msg = "La integración con Notion para Solicitudes no está configurada correctamente."
         logger.error(f"[{current_user.username}] {error_msg}")
         # Aquí podrías añadir un registro de auditoría si importas db y AuditLog
         # from .models import db, AuditLog
         # try:
         #     audit_log = AuditLog(...)
         #     db.session.add(audit_log)
         #     db.session.commit()
         # except Exception: db.session.rollback()
         return jsonify({"error": error_msg}), 503 # Service Unavailable

    data = request.get_json()
    if not data:
        logger.warning(f"[{current_user.username}] No se recibieron datos en /solicitudes/submit")
        return jsonify({"error": "No se recibieron datos."}), 400

    # Llama a la función auxiliar que contiene la lógica de procesamiento
    # Pasa el cliente Notion y los IDs a la función auxiliar
    # También puedes pasar current_user.id para logging o auditoría *dentro* de la función auxiliar si es necesario
    response_data, status_code = submit_request_for_material_logic(
        notion_client,
        database_id_db1,
        database_id_db2,
        data,
        user_id=current_user.id # Pasar el ID de usuario para usar en el log auxiliar
    )

    # Nota: submit_request_for_material_logic debería manejar su propio logging interno
    # y devolver la respuesta y el código de estado adecuados.
    # Aquí, puedes añadir registro de auditoría *después* de obtener el resultado
    # si no lo manejas dentro de la función auxiliar.

    # Ejemplo de registro de auditoría después (requiere importar db y AuditLog)
    # from .models import db, AuditLog
    # try:
    #     action = f'Solicitud Materiales {"Exitosa" if status_code < 300 else "Fallida"}'
    #     details = f"Status: {status_code}, Folio: {response_data.get('folio_solicitud', 'N/A')}, Detalles: {response_data.get('message') or response_data.get('error')}"
    #     audit_log = AuditLog(user_id=current_user.id, action=action, details=details[:500]) # Limitar longitud detalles
    #     db.session.add(audit_log)
    #     db.session.commit()
    # except Exception as audit_e:
    #     db.session.rollback()
    #     logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para solicitud de materiales: {audit_e}")


    return jsonify(response_data), status_code