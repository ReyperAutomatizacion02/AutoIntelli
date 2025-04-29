# autointelli/proyectos.py # <<< Corregir el nombre del archivo en el comentario

from flask import Blueprint, request, jsonify, render_template, current_app # Importar current_app
from flask_login import login_required, current_user
# Importar las funciones de creación de proyecto/partidas desde nuevosRegistros
from .nuevosRegistros import crear_proyecto, crear_partidas # <<< Importar las funciones correctas
# Importar db y AuditLog para registro de auditoría
from .models import db, AuditLog


import logging

logger = logging.getLogger(__name__) # Logger para este Blueprint

# Crear el Blueprint. Prefijo /proyectos.
# !!! ESTA LINEA DEBE DEFINIR EL BLUEPRINT proyectos_bp !!!
proyectos_bp = Blueprint('proyectos', __name__, url_prefix='/proyectos') # <<< Definición correcta

@proyectos_bp.route('/create', methods=['GET', 'POST']) # Ruta para la página y la acción de creación
@login_required
def create_project_page():
    # Obtener el cliente Notion y los IDs de DB desde la configuración central de la app
    notion_client = current_app.notion_client
    database_id_proyectos = current_app.config.get('DATABASE_ID_PROYECTOS')
    database_id_partidas = current_app.config.get('DATABASE_ID_PARTIDAS')

    # Verificar si la integración con Notion está configurada
    if notion_client is None or not database_id_proyectos or not database_id_partidas:
         error_msg = "La integración con Notion para Proyectos no está configurada correctamente."
         logger.error(f"[{current_user.username}] {error_msg}")
         if request.method == 'POST':
             # Registro de auditoría (Fallo de Configuración) - solo para POST
             try:
                  audit_log = AuditLog(
                      user_id=current_user.id,
                      action='Creación de Proyecto Fallida',
                      details=f'Error: Configuración de Notion incompleta ({error_msg}).'
                  )
                  db.session.add(audit_log)
                  db.session.commit()
             except Exception as audit_e:
                  logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo de configuración: {audit_e}")
                  db.session.rollback()
             return jsonify({"error": error_msg}), 503 # Service Unavailable para POST
         else:
              flash(error_msg, 'danger') # Mostrar mensaje en GET
              # Renderiza la plantilla incluso con el error para que el usuario vea el mensaje
              return render_template('proyectos/create_project.html') # Asume templates/proyectos/create_project.html


    # --- Lógica de POST (Crear Proyecto) ---
    if request.method == 'POST':
        logger.info(f"[{current_user.username}] Inicio de create_project_page (POST)")
        try:
            nombre_proyecto = request.form.get('nombre_proyecto')
            num_partidas_str = request.form.get('num_partidas', '0')

            if not nombre_proyecto:
                logger.warning(f"[{current_user.username}] Intento de crear proyecto sin nombre.")
                return jsonify({'error': 'El nombre del proyecto es obligatorio.'}), 400

            try:
                 num_partidas = int(num_partidas_str)
                 if num_partidas <= 0:
                      logger.warning(f"[{current_user.username}] Intento de crear proyecto '{nombre_proyecto}' con num_partidas <= 0: {num_partidas_str}")
                      return jsonify({'error': 'El número de partidas debe ser un número entero positivo.'}), 400
            except ValueError:
                 logger.warning(f"[{current_user.username}] Intento de crear proyecto '{nombre_proyecto}' con num_partidas no numérico: {num_partidas_str}")
                 return jsonify({'error': 'El número de partidas debe ser un número entero válido.'}), 400

            logger.info(f"[{current_user.username}] Solicitud para crear proyecto '{nombre_proyecto}' con {num_partidas} partidas.")

            # Llama a las funciones auxiliares, pasando el cliente Notion y los IDs
            proyecto_page_id = crear_proyecto(notion_client, database_id_proyectos, nombre_proyecto)

            if proyecto_page_id:
                logger.info(f"[{current_user.username}] Proyecto '{nombre_proyecto}' creado en Notion con ID: {proyecto_page_id}")
                partidas_ids = crear_partidas(notion_client, database_id_partidas, num_partidas, proyecto_page_id)

                if partidas_ids:
                    logger.info(f"[{current_user.username}] Creadas {len(partidas_ids)} partidas para el proyecto ID: {proyecto_page_id}")
                    # Registro de auditoría (Éxito)
                    try:
                        audit_log = AuditLog(
                            user_id=current_user.id,
                            action='Proyecto Creado',
                            details=f'Proyecto "{nombre_proyecto}" (ID Notion: {proyecto_page_id}) creado con {len(partidas_ids)} partidas.'
                        )
                        db.session.add(audit_log)
                        db.session.commit()
                        logger.info(f"[{current_user.username}] Registro de auditoría creado para creación de proyecto '{nombre_proyecto}'.")
                    except Exception as audit_e:
                         db.session.rollback()
                         logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para creación de proyecto: {audit_e}")

                    return jsonify({'message': f'Proyecto "{nombre_proyecto}" creado con éxito con {len(partidas_ids)} partidas.'}), 200
                else:
                    logger.error(f"[{current_user.username}] Error al crear las partidas para proyecto '{nombre_proyecto}' (ID: {proyecto_page_id}).")
                    # Registro de auditoría (Fallo en Partidas)
                    try:
                        audit_log = AuditLog(
                            user_id=current_user.id,
                            action='Creación de Proyecto Parcial',
                            details=f'Proyecto "{nombre_proyecto}" (ID Notion: {proyecto_page_id}) creado, pero fallaron las partidas.'
                        )
                        db.session.add(audit_log)
                        db.session.commit()
                        logger.info(f"[{current_user.username}] Registro de auditoría creado para fallo parcial (partidas) de proyecto '{nombre_proyecto}'.")
                    except Exception as audit_e:
                         db.session.rollback()
                         logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para fallo parcial: {audit_e}")
                    return jsonify({'error': 'Error al crear las partidas.'}), 500
            else:
                logger.error(f"[{current_user.username}] Error al crear el proyecto '{nombre_proyecto}' en Notion.")
                # Registro de auditoría (Fallo en Proyecto)
                try:
                    audit_log = AuditLog(
                        user_id=current_user.id,
                        action='Creación de Proyecto Fallida',
                        details=f'Error al crear el proyecto "{nombre_proyecto}" en Notion.'
                    )
                    db.session.add(audit_log)
                    db.session.commit()
                    logger.info(f"[{current_user.username}] Registro de auditoría creado para fallo en creación de proyecto '{nombre_proyecto}'.")
                except Exception as audit_e:
                     db.session.rollback()
                     logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría para fallo total: {audit_e}")
                return jsonify({'error': 'Error al crear el proyecto.'}), 500

        except Exception as e:
            error_msg = f"Error inesperado durante la creación del proyecto: {str(e)}"
            logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
            # Registro de auditoría (Fallo Inesperado)
            try:
                audit_log = AuditLog(
                    user_id=current_user.id,
                    action='Creación de Proyecto Fallida (Inesperado)',
                    details=f'Error inesperado: {error_msg}'
                )
                db.session.add(audit_log)
                db.session.commit()
                logger.info(f"[{current_user.username}] Registro de auditoría creado para fallo inesperado en creación de proyecto.")
            except Exception as audit_e:
                 logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo inesperado: {audit_e}")
                 db.session.rollback()
            return jsonify({'error': error_msg}), 500


    # --- Lógica de GET (Mostrar Formulario) ---
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /proyectos/create")
    # Renderiza la plantilla específica, usando un subdirectorio
    return render_template('proyectos/create_project.html') # Asume templates/proyectos/create_project.html