# autointelli/almacen.py

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user
from .models import db, AuditLog # Si necesitas registrar acciones de almacén en la DB
from .decorators import role_required # Importar el decorador
# Importar funciones para consultar/actualizar Notion si se necesitan
# Asegúrate de que estas funciones existen en notion_utils.py y aceptan notion_client y database_id como argumentos
from .notion_utils import get_pages_with_filter_util, update_page_util, build_filter_from_properties_util

import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /almacen.
# !!! ESTA LINEA CREA LA INSTANCIA DEL BLUEPRINT !!!
almacen_bp = Blueprint('almacen', __name__, url_prefix='/almacen')


@almacen_bp.route('/') # Ruta para la página principal del dashboard de Almacén
@login_required
@role_required(['almacen', 'admin']) # Solo roles 'almacen' y 'admin' pueden acceder
def almacen_dashboard():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /almacen/ (Almacén Dashboard)")

    # Lógica para cargar solicitudes de Notion para mostrar en el dashboard
    notion_client = current_app.notion_client
    # Asume que la DB de Solicitudes es una de las DBs de materiales
    # Necesitarás saber cuál usar, o si hay una DB de "Solicitudes Consolidadas"
    # Por ahora, asumiremos que consultamos DB1 de materiales, pero puede que necesites ajustar esto.
    database_id_solicitudes = current_app.config.get('DATABASE_ID_MATERIALES_DB1') # O la DB relevante para Almacén

    solicitudes = [] # Lista para almacenar las solicitudes obtenidas de Notion
    error_msg = None # Para almacenar un mensaje de error si falla la carga de Notion

    # Verificar si la integración con Notion está configurada correctamente para esta DB
    if notion_client and database_id_solicitudes:
         try:
              # Define los filtros relevantes para Almacén (ej: estatus 'Pendiente', 'En Proceso')
              # Esto requiere conocimiento de las propiedades de estatus en tu DB de materiales
              # Asume que tienes una propiedad 'Estatus' en tu DB de materiales.
              # Puedes ajustar este filtro según lo que Almacén necesita ver.
              filters_for_almacen = build_filter_from_properties_util(
                  notion_client,
                  database_id_solicitudes,
                  {"Estatus": "Pendiente"} # Ejemplo: filtrar por estatus "Pendiente"
                  # Puedes añadir más filtros aquí, o permitir filtros desde el frontend
              )
              logger.info(f"[{current_user.username}] Almacen: Filters built: {filters_for_almacen}")

              # Obtener las páginas (solicitudes) de Notion aplicando los filtros
              solicitudes = get_pages_with_filter_util(notion_client, database_id_solicitudes, filters_for_almacen)
              logger.info(f"[{current_user.username}] Almacen: Obtenidas {len(solicitudes)} solicitudes para Almacén.")

         except Exception as e:
              error_msg = f"Error al cargar solicitudes de Notion para Almacén: {e}"
              logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
              # Mostrar un mensaje flash en la UI si ocurre un error
              flash(error_msg, "danger")
    else:
         error_msg = "La integración con Notion para Almacén no está configurada correctamente (Cliente o DATABASE_ID_MATERIALES_DB1)."
         logger.warning(f"[{current_user.username}] {error_msg}")
         # Mostrar un mensaje flash en la UI si la configuración está incompleta
         flash(error_msg, "warning")


    # Renderiza la plantilla para la vista de Almacén, pasando la lista de solicitudes obtenidas
    # Asegúrate de que la plantilla existe en templates/almacen/dashboard.html
    return render_template('almacen/dashboard.html', solicitudes=solicitudes)

# --- Puedes añadir rutas para acciones de Almacén aquí (ej: actualizar estatus por AJAX) ---
# Esto requeriría funciones adicionales en notion_utils.py o lógica aquí.
# @almacen_bp.route('/update_status/<page_id>', methods=['POST'])
# @login_required
# @role_required(['almacen', 'admin'])
# def update_solicitud_status(page_id):
#     logger.info(f"[{current_user.username}] Recibiendo solicitud para actualizar estatus de solicitud {page_id}")
#     # ... Obtener el nuevo estatus (y quizás otros datos) del request.get_json() ...
#     # new_status = request.get_json().get('status')
#
#     notion_client = current_app.notion_client
#     if notion_client is None:
#         return jsonify({"error": "Cliente Notion no inicializado"}), 503
#
#     # Define las propiedades a actualizar. Necesitarás el nombre exacto de la propiedad de "Estatus" en Notion.
#     # properties_to_update = {
#     #     "Estatus": {"select": {"name": new_status}} # Ejemplo asumiendo una propiedad Select llamada "Estatus"
#     # }
#
#     # try:
#     #     status_code, response_data = update_page_util(notion_client, page_id, properties_to_update) # Asumiendo que update_page_util acepta un dict de propiedades
#     #
#     #     if 200 <= status_code < 300:
#     #         # Registrar auditoría si es necesario
#     #         # from .models import db, AuditLog
#     #         # try:
#     #         #     audit_log = AuditLog(user_id=current_user.id, action=f'Actualizar estatus solicitud {page_id}', details=f'Nuevo estatus: {new_status}')
#     #         #     db.session.add(audit_log)
#     #         #     db.session.commit()
#     #         # except Exception: db.session.rollback()
#     #         return jsonify({"message": "Estatus actualizado con éxito!"}), 200
#     #     else:
#     #         logger.error(f"Error al actualizar estatus de solicitud {page_id}: {response_data}")
#     #         return jsonify({"error": response_data.get('error', 'Error al actualizar estatus.')}), status_code
#     #
#     # except Exception as e:
#     #     logger.error(f"Error inesperado al actualizar estatus de solicitud {page_id}: {e}", exc_info=True)
#     #     return jsonify({"error": "Error interno del servidor al actualizar estatus."}), 500
#
#     pass # Implementar lógica si necesitas esta ruta