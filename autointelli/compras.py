# autointelli/compras.py

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user
from .models import db, AuditLog
from .decorators import role_required
# Importar funciones para consultar/actualizar Notion
from .notion.utils import get_pages_with_filter_util, update_notion_page_properties, build_filter_from_properties_util

import logging

logger = logging.getLogger(__name__)

compras_bp = Blueprint('compras', __name__, url_prefix='/compras')

@compras_bp.route('/')
@login_required
@role_required(['compras', 'admin'])
def compras_dashboard():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /compras/ (Compras Dashboard)")
    # ... (lógica para cargar solicitudes existentes y pasar a la plantilla) ...

    notion_client = current_app.notion_client
    database_id_solicitudes_compras = current_app.config.get('DATABASE_ID_MATERIALES_DB1') # O la DB relevante para Compras

    solicitudes = []
    error_msg = None

    if notion_client and database_id_solicitudes_compras:
         try:
              # Define los filtros relevantes para Compras (ej: ver todas, o filtrar por estatus)
              filters_for_compras = [] # Ejemplo: Obtener todas las solicitudes (sin filtros)
              # filters_for_compras = build_filter_from_properties_util(...) # Si necesitas filtros por defecto


              logger.info(f"[{current_user.username}] Compras: Filters built: {filters_for_compras if filters_for_compras else 'Ninguno'}")

              solicitudes = get_pages_with_filter_util(notion_client, database_id_solicitudes_compras, filters_for_compras)
              logger.info(f"[{current_user.username}] Compras: Obtenidas {len(solicitudes)} solicitudes para Compras con filtros.")

         except Exception as e:
              error_msg = f"Error al cargar solicitudes de Notion para Compras: {e}"
              logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
              flash(error_msg, "danger")
    else:
         error_msg = "La integración con Notion para Compras no está configurada correctamente (Cliente Notion o DATABASE_ID_MATERIALES_DB1)."
         logger.warning(f"[{current_user.username}] {error_msg}")
         flash(error_msg, "warning")


    return render_template('compras/dashboard_compras.html', solicitudes=solicitudes)


# --- NUEVA RUTA POST para actualizar el estatus de una solicitud ---
# Esta ruta recibirá el page_id y el nuevo estatus (u otras propiedades) del frontend via AJAX
@compras_bp.route('/update_solicitud_status/<string:page_id>', methods=['POST'])
@login_required
@role_required(['compras', 'admin']) # Solo roles 'compras' y 'admin' pueden actualizar
def update_solicitud_status(page_id):
    logger.info(f"[{current_user.username}] Recibiendo solicitud para actualizar solicitud {page_id} (Compras)")

    # Obtener los datos a actualizar del request.get_json() enviado por el frontend AJAX
    data = request.get_json()
    if not data:
        logger.warning(f"[{current_user.username}] Solicitud de actualización para {page_id} sin datos recibidos.")
        return jsonify({"error": "Datos inválidos: no se recibieron datos."}), 400 # Bad Request

    # Validar que los datos recibidos tienen la estructura esperada para la actualización
    # Por ejemplo, si solo esperas un nuevo estatus:
    # if 'status' not in data or not isinstance(data['status'], str):
    #     logger.warning(f"[{current_user.username}] Solicitud de actualización para {page_id} sin campo 'status' o tipo incorrecto.")
    #     return jsonify({"error": "Datos inválidos: se esperaba un campo 'status' (string)."}), 400

    # Si esperas un diccionario de propiedades a actualizar (más flexible):
    properties_to_update = data.get('properties', {}) # Asume que el frontend envía {"properties": {...}}
    if not isinstance(properties_to_update, dict) or not properties_to_update:
         logger.warning(f"[{current_user.username}] Solicitud de actualización para {page_id} sin diccionario 'properties' o está vacío.")
         return jsonify({"error": "Datos inválidos: se esperaba un diccionario no vacío en el campo 'properties'."}), 400


    # Obtener el cliente Notion desde la configuración central
    notion_client = current_app.notion_client
    if notion_client is None:
        error_msg = "Cliente Notion no inicializado."
        logger.error(f"[{current_user.username}] {error_msg}")
        return jsonify({"error": error_msg}), 503 # Service Unavailable


    try:
        # Llamar a la nueva función para actualizar propiedades generales
        # Le pasamos el diccionario properties_to_update directamente
        status_code, response_data = update_notion_page_properties(notion_client, page_id, properties_to_update)

        if 200 <= status_code < 300:
            # Registrar auditoría si la actualización fue exitosa
            from .models import db, AuditLog
            try:
                # Detalles del log: Incluir las propiedades actualizadas
                details_log = f'Solicitud ID Notion: {page_id}, Propiedades: {properties_to_update}'
                audit_log = AuditLog(user_id=current_user.id, action=f'Actualizar solicitud', details=details_log[:500]) # Limitar a 500 chars
                db.session.add(audit_log)
                db.session.commit()
                logger.info(f"[{current_user.username}] Registro de auditoría creado para actualización de solicitud {page_id}.")
            except Exception as audit_e:
                 db.session.rollback()
                 logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para actualización de solicitud: {audit_e}", exc_info=True)


            # Devolver un mensaje de éxito, quizás incluyendo los datos de la respuesta de Notion si son útiles
            return jsonify({"message": "Solicitud actualizada con éxito!", "notion_response": response_data}), 200

        else:
            # Si update_notion_page_properties devolvió un error (API de Notion u otro)
            logger.error(f"[{current_user.username}] Error al actualizar solicitud {page_id}: {response_data}")
            # Devolver el mensaje de error que viene de update_notion_page_properties
            return jsonify({"error": response_data.get('error', 'Error desconocido al actualizar solicitud.')}), status_code

    except Exception as e:
        # Capturar cualquier excepción inesperada durante el proceso de backend
        logger.error(f"[{current_user.username}] Error inesperado en update_solicitud_status para {page_id}: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor al actualizar estatus."}), 500