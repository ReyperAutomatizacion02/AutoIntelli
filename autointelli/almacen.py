# autointelli/almacen.py

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user
from .models import db, AuditLog # Importar para auditoría si es necesario en el Blueprint
from .decorators import role_required # Importar el decorador
# Importar funciones para consultar/actualizar Notion
from .notion_utils import get_pages_with_filter_util, update_page_util, build_filter_from_properties_util # Necesitaremos get_pages y build_filter

import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /almacen.
almacen_bp = Blueprint('almacen', __name__, url_prefix='/almacen')


@almacen_bp.route('/') # Ruta para la página principal del dashboard de Almacén
@login_required
@role_required(['almacen', 'admin']) # Solo roles 'almacen' y 'admin' pueden acceder
def almacen_dashboard():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /almacen/ (Almacén Dashboard)")

    # Lógica para cargar solicitudes de Notion para mostrar en el dashboard de Almacén
    notion_client = current_app.notion_client
    # Necesitarás saber cuál base de datos de Materiales es la fuente de solicitudes para Almacén.
    # Asumimos que es una de las DBs de Materiales definidas en __init__.py.
    # Usa el ID de la base de datos que Almacén debe consultar.
    # Por ahora, usaremos DATABASE_ID_MATERIALES_DB1 como ejemplo.
    database_id_solicitudes_almacen = current_app.config.get('DATABASE_ID_MATERIALES_DB1') # O la DB relevante para Almacén

    solicitudes = [] # Lista para almacenar las solicitudes obtenidas de Notion
    error_msg = None # Para almacenar un mensaje de error si falla la carga de Notion

    # Verificar si la integración con Notion está configurada correctamente para esta DB
    if notion_client and database_id_solicitudes_almacen:
         try:
              # Define los filtros relevantes para Almacén (ej: estatus 'Pendiente', 'En Proceso')
              # Esto requiere conocimiento de las propiedades de estatus en tu DB de materiales en Notion.
              # Asume que tienes una propiedad "Estatus" de tipo "Select" en tu base de datos de materiales.
              # Este es un ejemplo. Ajusta el nombre de la propiedad y los valores según tu base de datos.
              filters_for_almacen = build_filter_from_properties_util(
                  notion_client, # Pasa el cliente Notion
                  database_id_solicitudes_almacen, # Pasa el ID de la DB
                  {
                      "Estatus": "Pendiente" # Ejemplo: filtrar por estatus "Pendiente"
                      # Puedes añadir más filtros si Almacén solo ve ciertos tipos, proveedores, etc.
                      # "Proveedor": "Torni" # Ejemplo: si Almacén solo ve solicitudes Torni (no es tu caso aquí, pero como ejemplo)
                  }
              )
              logger.info(f"[{current_user.username}] Almacen: Filters built: {filters_for_almacen}")

              # Obtener las páginas (solicitudes) de Notion aplicando los filtros
              # get_pages_with_filter_util ya usa el cliente y el ID
              solicitudes = get_pages_with_filter_util(notion_client, database_id_solicitudes_almacen, filters_for_almacen)
              logger.info(f"[{current_user.username}] Almacen: Obtenidas {len(solicitudes)} solicitudes para Almacén con filtros.")

         except Exception as e:
              error_msg = f"Error al cargar solicitudes de Notion para Almacén: {e}"
              logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
              # Mostrar un mensaje flash en la UI si ocurre un error
              flash(error_msg, "danger")
    else:
         error_msg = "La integración con Notion para Almacén no está configurada correctamente (Cliente Notion o DATABASE_ID_MATERIALES_DB1)."
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
#     #     # Asumiendo que update_page_util se adapta para aceptar dict de propiedades, no solo fechas
#     #     # update_page_util ahora mismo solo actualiza la propiedad 'Date'. Necesitaría ser más genérica.
#     #     # O creas una nueva función en notion_utils.py para actualizar propiedades generales.
#     #     # status_code, response_data = update_page_util_general(notion_client, page_id, properties_to_update)
#     #
#     #     # Si necesitas usar la función actual update_page_util, tendrías que adaptarla o crear una nueva.
#     #     # Por ahora, la función actual SÓLO sirve para Fechas.
#     #     logger.error(f"La función update_page_util actual SOLO actualiza fechas. Se necesita una función genérica para actualizar estatus.")
#     #     return jsonify({"error": "Funcionalidad de actualización no implementada para estatus."}), 501 # Not Implemented
#
#     # except Exception as e:
#     #     logger.error(f"Error inesperado al actualizar estatus de solicitud {page_id}: {e}", exc_info=True)
#     #     return jsonify({"error": "Error interno del servidor al actualizar estatus."}), 500
#
#     pass # Implementar lógica si necesitas esta ruta