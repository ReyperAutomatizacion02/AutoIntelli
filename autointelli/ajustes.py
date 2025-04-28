# autointelli/ajustes.py

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user # Necesitas current_user para auditoría
from flask_cors import cross_origin # Si necesitas CORS
import os
from dotenv import load_dotenv # load_dotenv debe correr en __init__.py o app.py
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Union
import requests
import logging
import json
from notion_client import Client

# --- Importaciones locales desde el mismo paquete ---
# Necesitas importar la base de datos y el modelo AuditLog desde app.py (o models.py si los mueves)
from .app import db, AuditLog # Suponiendo que db y AuditLog están en app.py
# --- Fin Importaciones locales ---


# Configuración de logging (específica para este módulo si quieres logs separados)
# Si ya tienes logging configurado globalmente en app.py, puedes quitar esto
logger = logging.getLogger("notion_ajustes") # Cambia el nombre del logger
# Puedes añadir Handlers específicos si no quieres usar los globales de app.py
# logging.basicConfig(...)


# Cargar variables de entorno (load_dotenv debería llamarse en app.py principal)
# load_dotenv() # Normalmente no se llama aquí, sino una vez al inicio de la app


# --- Constantes y configuración de Notion (Específica para Ajustes) ---
# NOTION_API_KEY puede ser global si es el mismo para todas las herramientas
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
# Este ID es específico para Ajuste de Horarios
DATABASE_ID_PLANES = os.getenv("DATABASE_ID_PLANES")
API_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATE_PROPERTY_NAME = "Date" # OJO: Hardcodeado, considera hacerlo env var si se renombra
REQUEST_TIMEOUT = 30

# Verifica que las variables de entorno necesarias estén disponibles
if not NOTION_API_KEY or not DATABASE_ID_PLANES:
    logger.error("Variables de entorno requeridas para Ajustes no encontradas. Verifica NOTION_API_KEY y DATABASE_ID_PLANES.")
    # En lugar de raise EnvironmentError, manejamos esto más suavemente en una app web
    notion_client = None # Marca el cliente como no inicializado
    # No salimos de la aplicación
else:
     # Inicializar cliente Notion (solo si las variables están definidas)
    try:
        # El cliente Notion puede ser una instancia global si se usa mucho
        # O inicializado aquí si es solo para este blueprint
        notion_client = Client(auth=NOTION_API_KEY)
        logger.info("Cliente de Notion para Ajustes inicializado.")
    except Exception as e:
        logger.error(f"ERROR al inicializar Notion Client para Ajustes: {e}")
        notion_client = None # Marca el cliente como no inicializado


# Verifica que Notion Client esté disponible antes de definir HEADERS (si dependieran de él)
# Si HEADERS solo necesita NOTION_API_KEY, puedes definirlos antes del try/except
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


# --- Crear el Blueprint ---
# Nombre del blueprint: 'ajustes'
# Prefijo URL: '/ajustes' -> Rutas serán /ajustes/, /ajustes/run, etc.
ajustes_bp = Blueprint('ajustes', __name__, url_prefix='/ajustes')

# --- Definir Rutas DENTRO del Blueprint ---

@ajustes_bp.route('/') # Ruta completa: /ajustes/
@login_required # Requiere login
def adjust_dates_page(): # Nombre de función descriptivo para la página
    # Renderiza la plantilla específica para esta herramienta
    return render_template('adjust_dates.html')

@ajustes_bp.route('/run', methods=['GET', 'POST']) # Ruta completa: /ajustes/run
@login_required # Requiere login
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def run_adjust_script(): # Nombre de función descriptivo para la acción
    # El GET en esta ruta no tiene mucho sentido si el formulario envía por POST
    # Si un GET llega aquí, redirigimos a la página del formulario
    if request.method == 'GET':
        return redirect(url_for('ajustes.adjust_dates_page')) # Redirige al endpoint del Blueprint

    logger.info("Inicio de la función run_adjust_script()")
    try:
        logger.info("Dentro del bloque try")

        # Validar que el cliente Notion esté disponible
        if notion_client is None:
             error_msg = "La integración con Notion para Ajustes no está configurada correctamente."
             logger.error(error_msg)
             return jsonify({"error": error_msg}), 503 # Service Unavailable

        # --- Validar y obtener datos del formulario ---
        hours_str = request.form.get("hours")
        if not hours_str:
             return jsonify({"error": "Debes ingresar las horas a ajustar."}), 400 # Bad Request
        try:
            hours_to_adjust = int(hours_str)
        except ValueError:
             return jsonify({"error": "Las horas a ajustar deben ser un número entero válido."}), 400 # Bad Request

        move_backward = request.form.get("move_backward") == 'on'
        hours = hours_to_adjust if not move_backward else - hours_to_adjust

        start_date_str = request.form.get("start_date")
        if not start_date_str:
            return jsonify({"error": "Debes seleccionar una fecha."}), 400 # Bad Request

        property_filters = {}
        property_name_1 = request.form.get("property_name_1")
        property_value_1 = request.form.get("property_value_1")
        property_name_2 = request.form.get("property_name_2")
        property_value_2 = request.form.get("property_value_2")

        if property_name_1 and property_value_1:
            property_filters[property_name_1] = property_value_1
        if property_name_2 and property_value_2:
            property_filters[property_name_2] = property_value_2

        logger.info(f"Datos de formulario recibidos: Horas={hours}, Fecha={start_date_str}, Filtros={property_filters}")
        # --- Fin validación y obtención ---

        # Llamar a la lógica principal del módulo mH2
        # Pasar el cliente notion si la lógica principal lo necesitara
        # adjust_dates_api ya está diseñada para usar el cliente global definido en este módulo
        result_dict = adjust_dates_api(hours, start_date_str, property_filters=property_filters)


        # *** REGISTRO DE AUDITORÍA (Dentro de la lógica del Blueprint) ***
        # Asegúrate de que current_user está disponible y tiene id
        if current_user and current_user.is_authenticated:
             try:
                 # Accedemos a db y AuditLog importados desde app.py
                 audit_log = AuditLog(
                     user_id=current_user.id,
                     action='Ajuste de Horarios Ejecutado',
                     details=f'Horas: {hours}, Fecha: {start_date_str}, Filtros: {property_filters}, Resultado: {result_dict.get("message", result_dict.get("error", "Desconocido"))}'
                 )
                 db.session.add(audit_log)
                 db.session.commit()
                 logger.info(f"Registro de auditoría creado para Ajuste de Horarios por usuario {current_user.username}")
             except Exception as audit_e:
                 logger.error(f"ERROR al crear registro de auditoría para Ajuste de Horarios: {audit_e}")
                 db.session.rollback()
        else:
             logger.warning("current_user no autenticado al intentar registrar auditoría de Ajuste de Horarios.")
        # *** FIN REGISTRO DE AUDITORÍA ***

        # --- Construir respuesta para el frontend ---
        if result_dict.get("success"):
            return jsonify({"message": result_dict.get("message")})
        else:
            # Devolver un error HTTP adecuado si la operación falló en el script
            return jsonify({"error": result_dict.get("error", "Error desconocido al ajustar fechas.")}), 500 # Internal Server Error (si es del script) o 400 (si es de entrada)

    except ValueError as e:
        # Manejar específicamente errores de conversión (ej. horas no es un número)
        error_msg = f"Entrada inválida: {str(e)}"
        logger.error(f"ERROR de validación en run_adjust_script: {error_msg}")
        return jsonify({"error": error_msg}), 400 # Bad Request

    except Exception as e:
        error_msg = f"Error inesperado en run_adjust_script: {str(e)}"
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500 # Internal Server Error


# --- Funciones de mH2.py (adaptadas) ---

# **Nota:** Las funciones validate_api_connection, get_database_properties,
# create_filter_condition, get_pages_with_filter, update_page,
# adjust_dates_with_filters, build_filter_from_properties, adjust_dates_api,
# y list_available_properties DEBEN ser copiadas aquí desde tu archivo mH2.py.
# Asegúrate de que usen las variables (DATABASE_ID_PLANES, notion_client, HEADERS)
# definidas en este archivo de Blueprint.

# Ejemplo (copia TODAS las funciones):
# def validate_api_connection() -> bool:
#     # ... código copiado de mH2.py ...
#     pass # Reemplaza con el código real

# def get_database_properties() -> Dict[str, Dict]:
#      # ... código copiado de mH2.py ...
#     pass # Reemplaza con el código real

# ... y así sucesivamente para TODAS las funciones de mH2.py ...


def validate_api_connection() -> bool:
    try:
        # NOTA: Usa DATABASE_ID_PLANES definido en este archivo
        url = f"{API_BASE_URL}/databases/{DATABASE_ID_PLANES}"
        # NOTA: Usa HEADERS definido en este archivo
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Conexión a la API de Notion validada correctamente")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al validar la conexión a la API de Notion: {str(e)}")
        return False

def get_database_properties() -> Dict[str, Dict]:
    try:
        url = f"{API_BASE_URL}/databases/{DATABASE_ID_PLANES}"
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        database_info = response.json()
        properties = database_info.get("properties", {})

        logger.info(f"Propiedades obtenidas de la base de datos: {', '.join(properties.keys())}")
        return properties
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener propiedades de la base de datos: {str(e)}")
        return {}
        
def create_filter_condition(property_name: str, property_type: str, value: Any) -> Dict:
    # Esta función es genérica, no necesita cambios si no depende de variables globales específicas
    if property_type == "select":
        return {
            "property": property_name,
            "select": {
                "equals": value
            }
        }
    elif property_type == "multi_select":
        return {
            "property": property_name,
            "multi_select": {
                "contains": value
            }
        }
    elif property_type in ["title", "rich_text"]:
        return {
            "property": property_name,
            "rich_text": {
                "contains": value
            }
        }
    elif property_type == "number":
        return {
            "property": property_name,
            "number": {
                "equals": value
            }
        }
    elif property_type == "checkbox":
        return {
            "property": property_name,
            "checkbox": {
                "equals": value
            }
        }
    elif property_type == "people":
        return {
            "property": property_name,
            "people": {
                "contains": value
            }
        }
    elif property_type == "formula":
        return {
            "property": property_name,
            "rich_text": {
                "contains": value
            }
        }
    else:
        logger.warning(f"Tipo de propiedad no soportado para filtrado: {property_type}")
        return {}

def get_pages_with_filter(filters: List[Dict] = None, page_size: int = 100) -> List[Dict]:
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        try:
            url = f"{API_BASE_URL}/databases/{DATABASE_ID_PLANES}/query" # Usa DATABASE_ID_PLANES
            payload = {
                "page_size": page_size
            }

            if filters and len(filters) > 0:
                if len(filters) == 1:
                    payload["filter"] = filters[0]
                else:
                    payload["filter"] = {
                        "and": filters
                    }

            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT) # Usa HEADERS
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            all_pages.extend(results)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            logger.info(f"Obtenidas {len(results)} páginas con filtros. Total acumulado: {len(all_pages)}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener páginas de Notion con filtros: {str(e)}")
            break

    return all_pages

def update_page(page_id: str, new_start: datetime, new_end: Optional[datetime]) -> Tuple[int, Dict]:
    url = f"{API_BASE_URL}/pages/{page_id}"

    date_value = {
        "start": new_start.isoformat()
    }

    if new_end:
        date_value["end"] = new_end.isoformat()

    payload = {
        "properties": {
            DATE_PROPERTY_NAME: { # Usa DATE_PROPERTY_NAME
                "date": date_value
            }
        }
    }

    try:
        response = requests.patch(url, json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT) # Usa HEADERS
        response.raise_for_status()
        logger.info(f"Página {page_id} actualizada correctamente")
        return response.status_code, response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP al actualizar página {page_id}: {str(e)}")
        return e.response.status_code, e.response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al actualizar página {page_id}: {str(e)}")
        return 500, {"error": str(e)}

def adjust_dates_with_filters(
    hours: int,
    start_date: datetime,
    filters: List[Dict[str, Any]] = None
) -> str:
    # NOTA: validate_api_connection y get_pages_with_filter, update_page deben existir aquí
    if not validate_api_connection():
        return "Error: No se pudo conectar a la API de Notion. Verifica tu conexión y credenciales."

    pages = get_pages_with_filter(filters)
    total_pages = len(pages)
    updated_pages = 0
    failed_updates = 0
    skipped_pages = 0

    filter_description = "ninguno"
    if filters and len(filters) > 0:
        filter_props = [f.get("property", "desconocido") for f in filters]
        filter_description = ", ".join(filter_props)

    logger.info(f"Iniciando ajuste de fechas: {hours} horas a partir de {start_date.isoformat()}")
    logger.info(f"Filtros aplicados: {filter_description}")
    logger.info(f"Total de páginas a procesar: {total_pages}")

    for page in pages:
        properties = page.get("properties", {})
        page_id = page.get("id")

        if not page_id:
            logger.warning("Página sin ID encontrada, omitiendo")
            skipped_pages += 1
            continue

        date_info = properties.get(DATE_PROPERTY_NAME, {}).get("date", {})

        if not date_info or "start" not in date_info:
            logger.info(f"Página {page_id} sin fecha, omitiendo")
            skipped_pages += 1
            continue

        try:
            start_date_notion = datetime.fromisoformat(date_info["start"]).replace(tzinfo=None)
            end_date_notion = None

            if date_info.get("end"):
                end_date_notion = datetime.fromisoformat(date_info["end"]).replace(tzinfo=None)

            if start_date_notion >= start_date:
                new_start = start_date_notion + timedelta(hours=hours)
                new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None

                status_code, _ = update_page(page_id, new_start, new_end)

                if 200 <= status_code < 300:
                    updated_pages += 1
                else:
                    failed_updates += 1
            else:
                logger.info(f"Página {page_id} con fecha anterior a {start_date.isoformat()}, omitiendo")
                skipped_pages += 1

        except (ValueError, TypeError) as e:
            logger.error(f"Error al procesar fecha de página {page_id}: {str(e)}")
            failed_updates += 1

    logger.info(f"Proceso completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")

    resumen = (
        f"Operación completada: Se actualizaron {updated_pages} registros a partir del {start_date.strftime('%Y-%m-%d')}.\n"
        f"Filtros aplicados: {filter_description}\n"
        f"Total de registros filtrados: {total_pages}\n"
        f"Registros actualizados: {updated_pages}\n"
        f"Registros omitidos: {skipped_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: {hours} horas"
    )

    return resumen

def build_filter_from_properties(property_filters: Dict[str, Any]) -> List[Dict]:
    if not property_filters:
        return []

    filters = []
    # get_database_properties debe existir aquí
    db_properties = get_database_properties()

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos, omitiendo filtro")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")

        # create_filter_condition debe existir aquí
        filter_condition = create_filter_condition(prop_name, prop_type, prop_value)

        if filter_condition:
            filters.append(filter_condition)

    return filters

def adjust_dates_api(
    hours: int,
    start_date_str: str,
    property_filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    try:
        # adjust_dates_with_filters y build_filter_from_properties deben existir aquí
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        filters = build_filter_from_properties(property_filters) if property_filters else None
        result_message = adjust_dates_with_filters(hours, start_date, filters)

        return {
            "success": True,
            "message": result_message
        }

    except ValueError as e:
        error_msg = f"Formato de fecha inválido: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error al ajustar fechas: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def list_available_properties() -> List[Dict[str, str]]:
    # get_database_properties debe existir aquí
    properties = get_database_properties()
    property_list = []

    for name, info in properties.items():
        prop_type = info.get("type", "unknown")
        property_list.append({
            "name": name,
            "type": prop_type
        })

    return property_list

# --- Elimina el bloque if __name__ == "__main__": ---
# Esto solo se ejecuta cuando el script es el punto de entrada principal,
# no cuando es importado como parte de un Blueprint.