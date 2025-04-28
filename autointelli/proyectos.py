# autointelli/proyectos.py

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user # Necesitas current_user para auditoría
# from flask_cors import cross_origin # Si necesitas CORS
import os
# from dotenv import load_dotenv # load_dotenv debe correr en app.py o __init__.py
import logging # Importar logging
# Importar el cliente de Notion y los errores específicos
from notion_client import Client
from notion_client.errors import APIResponseError

# --- Importaciones locales desde el mismo paquete ---
# *** Importar db y AuditLog desde .models para el registro de auditoría ***
from .models import db, AuditLog
# *** Importar las funciones refactorizadas desde .nuevosRegistros ***
from .nuevosRegistros import crear_proyecto, crear_partidas
# --- Fin Importaciones locales ---

# Configuración de logging
logger = logging.getLogger("notion_proyectos")

# --- Configuración de Notion (Específica para Proyectos) ---
# NOTION_API_KEY puede ser global si es el mismo para todas las herramientas
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
# Estos IDs son específicos para Nuevo Proyecto
DATABASE_ID_PROYECTOS = os.getenv("DATABASE_ID_PROYECTOS")
DATABASE_ID_PARTIDAS = os.getenv("DATABASE_ID_PARTIDAS")

# Inicializar cliente Notion (solo si las variables están definidas)
notion_client = None # Inicializar a None
if NOTION_API_KEY and DATABASE_ID_PROYECTOS and DATABASE_ID_PARTIDAS:
    try:
        notion_client = Client(auth=NOTION_API_KEY)
        logger.info("Cliente de Notion para Proyectos inicializado.")
    except Exception as e:
        logger.error(f"ERROR al inicializar Notion Client para Proyectos: {e}")
else:
    logger.warning("Variables de entorno Notion para Proyectos no configuradas (NOTION_API_KEY, DATABASE_ID_PROYECTOS, DATABASE_ID_PARTIDAS). Las rutas de creación de proyectos no funcionarán.")


# --- Crear el Blueprint ---
# Nombre del blueprint: 'proyectos'
# Prefijo URL: '/proyectos' -> Rutas serán /proyectos/, /proyectos/create, etc.
proyectos_bp = Blueprint('proyectos', __name__, url_prefix='/proyectos')

# --- Definir Rutas DENTRO del Blueprint ---

@proyectos_bp.route('/create', methods=['GET', 'POST']) # Ruta completa: /proyectos/create
@login_required # Requiere login
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def create_project_page(): # Nombre de función descriptivo para la página/acción
    if request.method == 'POST':
        # Validar que el cliente Notion esté disponible
        if notion_client is None:
             error_msg = "La integración con Notion para Proyectos no está configurada correctamente."
             logger.error(f"[{current_user.username}] {error_msg}")
             # *** REGISTRO DE AUDITORÍA (Fallo de Configuración) ***
             try:
                  if current_user.is_authenticated:
                      audit_log = AuditLog(
                          user_id=current_user.id,
                          action='Creación de Proyecto Fallida',
                          details=f'Error: Configuración de Notion incompleta ({error_msg}).'
                      )
                      db.session.add(audit_log)
                      db.session.commit()
                  else:
                       logger.warning("Usuario no autenticado al registrar error de configuración de Creación de Proyecto.")
             except Exception as audit_e:
                  logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo de configuración: {audit_e}")
                  db.session.rollback()
             # *** FIN REGISTRO DE AUDITORÍA ***
             return jsonify({"error": error_msg}), 503 # Service Unavailable

        logger.info(f"[{current_user.username}] Inicio de la función create_project_page (POST)")
        try:
            # Llama a las funciones importadas desde .nuevosRegistros
            # *** CORRECCIÓN: Obtener datos del form request ***
            nombre_proyecto = request.form.get('nombre_proyecto')
            num_partidas_str = request.form.get('num_partidas', '0') # Obtener como str, default '0'

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

            # *** CORRECCIÓN: Pasar el cliente Notion y los IDs a las funciones ***
            proyecto_page_id = crear_proyecto(notion_client, DATABASE_ID_PROYECTOS, nombre_proyecto)

            if proyecto_page_id:
                logger.info(f"[{current_user.username}] Proyecto '{nombre_proyecto}' creado en Notion con ID: {proyecto_page_id}")
                partidas_ids = crear_partidas(notion_client, DATABASE_ID_PARTIDAS, num_partidas, proyecto_page_id)

                if partidas_ids:
                    logger.info(f"[{current_user.username}] Creadas {len(partidas_ids)} partidas para el proyecto ID: {proyecto_page_id}")
                    # *** REGISTRO DE AUDITORÍA (Éxito) ***
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
                    # *** FIN REGISTRO DE AUDITORÍA ***
                    return jsonify({'message': f'Proyecto "{nombre_proyecto}" creado con éxito con {len(partidas_ids)} partidas.'}), 200 # HTTP 200 OK
                else:
                    logger.error(f"[{current_user.username}] Error al crear las partidas para proyecto '{nombre_proyecto}' (ID: {proyecto_page_id}).")
                    # *** REGISTRO DE AUDITORÍA (Fallo en Partidas) ***
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
                    # *** FIN REGISTRO DE AUDITORÍA ***
                    return jsonify({'error': 'Error al crear las partidas.'}), 500 # Internal Server Error
            else:
                logger.error(f"[{current_user.username}] Error al crear el proyecto '{nombre_proyecto}' en Notion.")
                # *** REGISTRO DE AUDITORÍA (Fallo en Proyecto) ***
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
                # *** FIN REGISTRO DE AUDITORÍA ***
                return jsonify({'error': 'Error al crear el proyecto.'}), 500 # Internal Server Error

        except Exception as e:
            error_msg = f"Error inesperado durante la creación del proyecto: {str(e)}"
            logger.error(f"[{current_user.username}] {error_msg}", exc_info=True)
            # *** REGISTRO DE AUDITORÍA (Fallo Inesperado) ***
            try:
                audit_log = AuditLog(
                    user_id=current_user.id,
                    action='Creación de Proyecto Fallida (Inesperado)',
                    details=f'{error_msg}'
                )
                db.session.add(audit_log)
                db.session.commit()
                logger.info(f"[{current_user.username}] Registro de auditoría creado para fallo inesperado en creación de proyecto.")
            except Exception as audit_e:
                 logger.error(f"[{current_user.username}] ERROR al crear registro de auditoría de fallo inesperado: {audit_e}")
                 db.session.rollback()
            # *** FIN REGISTRO DE AUDITORÍA ***
            return jsonify({'error': error_msg}), 500 # Internal Server Error


    # Si es un GET request, renderiza la plantilla
    logger.info(f"[{current_user.username}] Solicitud GET recibida en /proyectos/create")
    return render_template('create_project.html') # Asegúrate de tener este template

# --- Elimina el bloque if __name__ == "__main__": de este archivo ---