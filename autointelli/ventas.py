# autointelli/ventas.py

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user
from .models import db, AuditLog # Si necesitas registrar acciones de ventas en la DB
from .decorators import role_required # Importar el decorador
# Importar funciones para consultar/actualizar Notion si se necesitan
# Asegúrate de que estas funciones existen en notion_utils.py y aceptan notion_client y database_id como argumentos
from .notion_utils import get_pages_with_filter_util, update_page_util, build_filter_from_properties_util

import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /ventas.
# !!! ESTA LINEA CREA LA INSTANCIA DEL BLUEPRINT QUE SE IMPORTA EN __init__.py !!!
ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')


@ventas_bp.route('/') # Ruta para la página principal del dashboard de Ventas
@login_required
@role_required(['ventas', 'admin']) # Solo roles 'ventas' y 'admin' pueden acceder
def ventas_dashboard():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /ventas/ (Ventas Dashboard)")

    # Lógica para cargar solicitudes de Notion para mostrar en el dashboard de Ventas
    notion_client = current_app.notion_client
    # Asume que la DB de Solicitudes es una de las DBs de materiales
    # Necesitarás saber cuál usar para Ventas.
    # Por ahora, asumiremos que consultamos DB1 de materiales, pero puede que necesites ajustar esto.
    database_id_solicitudes = current_app.config.get('DATABASE_ID_MATERIALES_DB1') # O la DB relevante para Ventas

    solicitudes = [] # Lista para almacenar las solicitudes obtenidas de Notion
    error_msg = None # Para almacenar un mensaje de error si falla la carga de Notion

    # Verificar si la integración con Notion está configurada correctamente para esta DB
    if notion_client and database_id_solicitudes:
         try:
              # Define los filtros relevantes para Ventas (ej: todas las solicitudes, o filtrar por estatus)
              # Aquí podrías no tener filtros por defecto, o filtrar por estatus 'Completada', 'Enviada', etc.
              # filters_for_ventas = build_filter_from_properties_util(...) # Si necesitas filtros por defecto

              # Obtener las páginas (solicitudes) de Notion aplicando los filtros (o sin filtros)
              solicitudes = get_pages_with_filter_util(notion_client, database_id_solicitudes) # Obtener todas las solicitudes (sin filtros) o aplicar filtros definidos arriba
              logger.info(f"[{current_user.username}] Ventas: Obtenidas {len(solicitudes)} solicitudes para Ventas.")

         except Exception as e:
              error_msg = f"Error al cargar solicitudes de Notion para Ventas: {e}"
              logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
              # Mostrar un mensaje flash en la UI si ocurre un error
              flash(error_msg, "danger")
    else:
         error_msg = "La integración con Notion para Ventas no está configurada correctamente (Cliente o DATABASE_ID_MATERIALES_DB1)."
         logger.warning(f"[{current_user.username}] {error_msg}")
         # Mostrar un mensaje flash en la UI si la configuración está incompleta
         flash(error_msg, "warning")


    # Renderiza la plantilla para la vista de Ventas, pasando la lista de solicitudes obtenidas
    # Asegúrate de que la plantilla existe en templates/ventas/dashboard.html
    return render_template('ventas/dashboard.html', solicitudes=solicitudes)

# --- Puedes añadir rutas para acciones de Ventas aquí (ej: actualizar estatus, asignar proyecto, etc.) ---
# Esto requeriría funciones adicionales en notion_utils.py o lógica aquí.
# @ventas_bp.route('/update_solicitud/<page_id>', methods=['POST'])
# @login_required
# @role_required(['ventas', 'admin'])
# def update_solicitud_ventas(page_id):
#     logger.info(f"[{current_user.username}] Recibiendo solicitud para actualizar estatus de solicitud {page_id}")
#     # ... obtener datos del request.get_json() ...
#     # ... llamar a update_page_util con el page_id y los datos a actualizar ...
#     # ... registrar auditoría si es necesario ...
#     # ... devolver respuesta JSON ...
#     pass # Implementar lógica si necesitas esta ruta