# autointelli/ventas.py

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user
from .models import db, AuditLog # Si necesitas registrar acciones en la DB
from .decorators import role_required # Importar el decorador
# Importar funciones para consultar/actualizar Notion
from .notion_utils import get_pages_with_filter_util, update_page_util, build_filter_from_properties_util

import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /ventas.
ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')

@ventas_bp.route('/') # Ruta para la página principal del dashboard de Ventas
@login_required
@role_required(['ventas', 'admin']) # Solo roles 'ventas' y 'admin' pueden acceder
def ventas_dashboard():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /ventas/ (Ventas Dashboard)")

    # Lógica para cargar solicitudes de Notion para mostrar en el dashboard de Ventas
    notion_client = current_app.notion_client
    # Necesitarás saber cuál base de datos de Materiales es la fuente de solicitudes para Ventas.
    # Asumiremos que es la misma que Almacén (DATABASE_ID_MATERIALES_DB1), pero ajusta si es diferente.
    database_id_solicitudes_ventas = current_app.config.get('DATABASE_ID_MATERIALES_DB1') # O la DB relevante para Ventas

    solicitudes = [] # Lista para almacenar las solicitudes obtenidas de Notion
    error_msg = None # Para almacenar un mensaje de error si falla la carga de Notion

    # Verificar si la integración con Notion está configurada correctamente para esta DB
    if notion_client and database_id_solicitudes_ventas:
         try:
              # Define los filtros relevantes para Ventas.
              # Ejemplo: Ver todas las solicitudes (lista de filtros vacía).
              # O ejemplo: Ver solicitudes con estatus 'Completada'.
              # filters_for_ventas = build_filter_from_properties_util(
              #     notion_client,
              #     database_id_solicitudes_ventas,
              #     {"Estatus": "Completada"} # Ejemplo: filtrar por estatus "Completada"
              # )
              filters_for_ventas = [] # <<< Ejemplo: Obtener todas las solicitudes (sin filtros)


              logger.info(f"[{current_user.username}] Ventas: Filters built: {filters_for_ventas if filters_for_ventas else 'Ninguno'}")

              # Obtener las páginas (solicitudes) de Notion aplicando los filtros (o sin filtros)
              solicitudes = get_pages_with_filter_util(notion_client, database_id_solicitudes_ventas, filters_for_ventas)
              logger.info(f"[{current_user.username}] Ventas: Obtenidas {len(solicitudes)} solicitudes para Ventas con filtros.")

         except Exception as e:
              error_msg = f"Error al cargar solicitudes de Notion para Ventas: {e}"
              logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
              # Mostrar un mensaje flash en la UI si ocurre un error
              flash(error_msg, "danger")
    else:
         error_msg = "La integración con Notion para Ventas no está configurada correctamente (Cliente Notion o DATABASE_ID_MATERIALES_DB1)."
         logger.warning(f"[{current_user.username}] {error_msg}")
         # Mostrar un mensaje flash en la UI si la configuración está incompleta
         flash(error_msg, "warning")


    # Renderiza la plantilla para la vista de Ventas, pasando la lista de solicitudes obtenidas
    # Asegúrate de que la plantilla existe en templates/ventas/dashboard.html
    return render_template('ventas/dashboard.html', solicitudes=solicitudes)

# --- Puedes añadir rutas para acciones de Ventas aquí (ej: actualizar estatus, asignar proyecto, etc.) ---
# Esto requeriría funciones adicionales en notion_utils.py o lógica aquí.
# Es probable que Ventas necesite funcionalidades para actualizar más campos que solo el estatus.
# Por ejemplo, podrías tener una ruta para actualizar cualquier propiedad dada.
# @ventas_bp.route('/update_solicitud_prop/<page_id>', methods=['POST'])
# @login_required
# @role_required(['ventas', 'admin'])
# def update_solicitud_ventas_property(page_id):
#     logger.info(f"[{current_user.username}] Recibiendo solicitud para actualizar propiedad de solicitud {page_id} (Ventas)")
#     # ... Obtener del request.get_json() un diccionario con { "Nombre Propiedad Notion": "Nuevo Valor" } ...
#     # properties_to_update = request.get_json()
#
#     notion_client = current_app.notion_client
#     if notion_client is None:
#         return jsonify({"error": "Cliente Notion no inicializado"}), 503
#
#     # Necesitas una función en notion_utils.py que pueda actualizar propiedades generales por page_id.
#     # La función update_page_util actual SOLO actualiza la propiedad 'Date'.
#     # Tendrías que crear una nueva función en notion_utils.py:
#     # def update_notion_page_properties(notion_client, page_id, properties_dict): ...
#
#     # try:
#     #     # Asumiendo que creaste update_notion_page_properties en notion_utils.py
#     #     status_code, response_data = update_notion_page_properties(notion_client, page_id, properties_to_update)
#     #
#     #     if 200 <= status_code < 300:
#     #         # Registrar auditoría si es necesario
#     #         # from .models import db, AuditLog
#     #         # try:
#     #         #     audit_log = AuditLog(user_id=current_user.id, action=f'Actualizar solicitud {page_id}', details=f'Propiedades actualizadas: {properties_to_update}')
#     #         #     db.session.add(audit_log)
#     #         #     db.session.commit()
#     #         # except Exception: db.session.rollback()
#     #         return jsonify({"message": "Solicitud actualizada con éxito!"}), 200
#     #     else:
#     #         logger.error(f"Error al actualizar solicitud {page_id}: {response_data}")
#     #         return jsonify({"error": response_data.get('error', 'Error al actualizar solicitud.')}), status_code
#     #
#     # except Exception as e:
#     #     logger.error(f"Error inesperado al actualizar solicitud {page_id}: {e}", exc_info=True)
#     #     return jsonify({"error": "Error interno del servidor al actualizar solicitud."}), 500
#
#     pass # Implementar lógica si necesitas esta ruta