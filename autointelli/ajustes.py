# autointelli/ajustes.py

from flask import Blueprint, request, jsonify, render_template, current_app # Importar current_app
from flask_login import login_required, current_user
from .notion.ajustes import adjust_dates_api
from .notion.utils import list_available_properties
from .models import db, AuditLog # Importarlos para registro de auditoría


import logging
# from flask_cors import cross_origin # Si necesitas CORS

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /ajustes.
ajustes_bp = Blueprint('ajustes', __name__, url_prefix='/ajustes')

@ajustes_bp.route('/')
@login_required
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def adjust_dates_page():
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /ajustes/")
    properties = []
    # Obtener el cliente Notion y el ID de DB desde la configuración central de la app
    notion_client = current_app.notion_client
    database_id_planes = current_app.config.get('DATABASE_ID_PLANES')

    # Verificar si la integración con Notion está configurada para esta base de datos
    if notion_client and database_id_planes:
        try:
            # Llama a la función auxiliar, pasando el cliente y el ID
            properties = list_available_properties(notion_client, database_id_planes)
            logger.info(f"[{current_user.username}] Propiedades de Notion obtenidas para formulario de ajuste.")
        except Exception as e:
            logger.error(f"[{current_user.username}] Error al obtener propiedades para el formulario de ajuste: {e}", exc_info=True)
            flash("Error al cargar las propiedades de Notion para filtros.", "warning")
            # Continúa sin propiedades, el usuario deberá ingresar manualmente
    else:
         warning_msg = "La integración con Notion para Ajustes no está configurada completamente (Cliente o DATABASE_ID_PLANES)."
         logger.warning(f"[{current_user.username}] {warning_msg}")
         flash(warning_msg, "warning")


    # Renderiza la plantilla específica, usando un subdirectorio
    return render_template('ajustes/adjust_dates.html', available_properties=properties) # Asume templates/ajustes/adjust_dates.html


@ajustes_bp.route('/run', methods=['POST']) # Cambiado a solo POST
@login_required
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def run_adjust_script():
    logger.info(f"[{current_user.username}] Inicio de la función run_adjust_script() (POST)")

    # Obtener el cliente Notion y el ID de DB desde la configuración central de la app
    notion_client = current_app.notion_client
    database_id_planes = current_app.config.get('DATABASE_ID_PLANES')

    # Validar que la integración con Notion esté configurada
    if notion_client is None or not database_id_planes:
         error_msg = "La integración con Notion para Ajustes no está configurada correctamente."
         logger.error(f"[{current_user.username}] {error_msg}")
         # Registro de auditoría (Fallo de Configuración)
         try:
              audit_log = AuditLog(
                  user_id=current_user.id,
                  action='Ajuste de Horarios Fallido',
                  details=f'Error: Configuración de Notion incompleta ({error_msg}).'
              )
              db.session.add(audit_log)
              db.session.commit()
         except Exception as audit_e:
              logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo: {audit_e}")
              db.session.rollback()
         return jsonify({"error": error_msg}), 503 # Service Unavailable


    try:
        logger.info(f"[{current_user.username}] Dentro del bloque try de run_adjust_script")

        # Validar y obtener datos del formulario
        hours_str = request.form.get("hours")
        if not hours_str:
             logger.warning(f"[{current_user.username}] Falta el campo 'hours'.")
             return jsonify({"error": "Debes ingresar las horas a ajustar."}), 400
        try:
            hours_to_adjust = int(hours_str)
        except ValueError:
             logger.warning(f"[{current_user.username}] Campo 'hours' no es un entero válido: {hours_str}")
             return jsonify({"error": "Las horas a ajustar deben ser un número entero válido."}), 400

        move_backward = request.form.get("move_backward") == 'on'
        hours = hours_to_adjust if not move_backward else - hours_to_adjust

        start_date_str = request.form.get("start_date")
        if not start_date_str:
            logger.warning(f"[{current_user.username}] Falta el campo 'start_date'.")
            return jsonify({"error": "Debes seleccionar una fecha."}), 400

        property_filters = {}
        for i in range(1, 4):
             prop_name = request.form.get(f"property_name_{i}")
             prop_value = request.form.get(f"property_value_{i}")
             if prop_name and prop_value:
                  property_filters[prop_name.strip()] = prop_value.strip()

        logger.info(f"[{current_user.username}] Datos de formulario recibidos: Horas={hours}, Fecha={start_date_str}, Filtros={property_filters}")

        # Llama a la lógica principal del módulo auxiliar, pasando el cliente Notion y el ID
        result_dict = adjust_dates_api(notion_client, database_id_planes, hours, start_date_str, property_filters=property_filters)


        # Registro de auditoría
        try:
             action = f'Ajuste Horarios {"Exitoso" if result_dict.get("success") else "Fallido"}'
             details = f'Horas: {hours}, Fecha: {start_date_str}, Filtros: {property_filters}, Resultado: {result_dict.get("message", result_dict.get("error", "Desconocido"))}'
             audit_log = AuditLog(
                 user_id=current_user.id,
                 action=action,
                 details=details[:500] # Limitar longitud
             )
             db.session.add(audit_log)
             db.session.commit()
             logger.info(f"[{current_user.username}] Registro de auditoría creado para Ajuste de Horarios.")
        except Exception as audit_e:
             logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para Ajuste de Horarios: {audit_e}")
             db.session.rollback()

        # Construir respuesta para el frontend
        if result_dict.get("success"):
            return jsonify({"message": result_dict.get("message")})
        else:
            return jsonify({"error": result_dict.get("error", "Error desconocido al ajustar fechas.")}), result_dict.get("status_code", 500)

    except ValueError as e:
        error_msg = f"Entrada inválida: {str(e)}"
        logger.error(f"[{current_user.username}] ERROR de validación en run_adjust_script: {error_msg}")
        # Registro de auditoría (Fallo de Validación)
        try:
             audit_log = AuditLog(
                 user_id=current_user.id,
                 action='Ajuste de Horarios Fallido (Validación)',
                 details=f'Error de validación: {error_msg}'
             )
             db.session.add(audit_log)
             db.session.commit()
        except Exception as audit_e:
             logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo de validación: {audit_e}")
             db.session.rollback()
        return jsonify({"error": error_msg}), 400

    except Exception as e:
        error_msg = f"Error inesperado en run_adjust_script: {str(e)}"
        logger.error(f"[{current_user.username}] ERROR INESPERADO: {error_msg}", exc_info=True)
        # Registro de auditoría (Fallo Inesperado)
        try:
             audit_log = AuditLog(
                 user_id=current_user.id,
                 action='Ajuste de Horarios Fallido (Inesperado)',
                 details=f'Error inesperado: {error_msg}'
             )
             db.session.add(audit_log)
             db.session.commit()
        except Exception as audit_e:
             logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo inesperado: {audit_e}")
             db.session.rollback()
        return jsonify({"error": error_msg}), 500