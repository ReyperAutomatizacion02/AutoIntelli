# autointelli/notion_utils.py
# Este archivo contiene funciones auxiliares de Notion para Ajustes y Solicitudes.
# NO debe cargar .env ni inicializar el cliente Notion directamente.
# NO debe tener un bloque __main__.

import logging
import requests
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback # Importar traceback

logger = logging.getLogger("notion_utils")

# --- Constantes (o podrían pasarse como argumentos si fueran configurables) ---
DATE_PROPERTY_NAME = "Date" # Nombre de la propiedad de Fecha para Ajustes (usado solo en funciones de Ajuste)
REQUEST_TIMEOUT = 30
NOTION_VERSION = "2022-06-28"
API_BASE_URL = "https://api.notion.com/v1"

# --- IDs de Base de Datos de Notion ---
# Estos IDs DEBEN ser pasados como argumentos desde la configuración de Flask.
# No los definimos aquí con valores reales.
# database_id_db1, database_id_db2, database_id_proyectos deben venir de Flask config.


# --- Nombre exacto de las propiedades en tus Bases de Datos de Notion ---
# ¡¡¡REEMPLAZA LOS VALORES DE ESTAS CONSTANTES CON LOS NOMBRES EXACTOS EN TUS BDs DE NOTION!!!
# ¡¡¡Case-sensitive!!! ¡Respeta espacios, mayúsculas/minúsculas y acentos!

# --- Propiedades en Base(s) de Datos de Materiales ---
NOTION_PROP_FOLIO = "Folio de solicitud" # Asumiendo Rich Text
NOTION_PROP_SOLICITANTE = "Nombre del solicitante" # Asumiendo que es un Select (basado en error anterior)
NOTION_PROP_FECHA_SOLICITUD = "Fecha de solicitud" # Asumiendo que es Date
NOTION_PROP_PROVEEDOR = "Proveedor" # Asumiendo que es un Select (basado en error anterior)
NOTION_PROP_DEPARTAMENTO = "Departamento/Área" # Asumiendo que es un Select (basado en error anterior)
# *** NOTION_PROP_PROYECTO: El nombre de la propiedad tipo RELATION en tu BD de MATERIALES que enlaza a Proyectos ***
NOTION_PROP_MATERIALES_PROYECTO_RELATION = "Proyecto" # <<<< Nombre EXACTO de la propiedad RELATION en BD Materiales <<<<
NOTION_PROP_ESPECIFICACIONES = "Especificaciones adicionales" # Asumiendo Rich Text

NOTION_PROP_CANTIDAD = "Cantidad solicitada" # Asumiendo Number
NOTION_PROP_TIPO_MATERIAL = "Tipo de material" # Asumiendo Select (basado en error anterior)
NOTION_PROP_NOMBRE_MATERIAL = "Nombre del material" # Asumiendo Select (basado en error anterior)
NOTION_PROP_UNIDAD_MEDIDA = "Unidad de medida" # Asumiendo Select (basado en error anterior)

NOTION_PROP_LARGO = "Largo (dimensión)" # Asumiendo Rich Text
NOTION_PROP_ANCHO = "Ancho (dimensión)" # Asumiendo Rich Text
NOTION_PROP_ALTO = "Alto (dimensión)"   # Asumiendo Rich Text
NOTION_PROP_DIAMETRO = "Diametro (dimensión)" # Asumiendo Rich Text

# Propiedades específicas de Torni (ajusta si es necesario)
NOTION_PROP_TORNI_ID = "ID de producto" # Asumiendo Rich Text
NOTION_PROP_TORNI_DESCRIPTION = "Descripción" # Asumiendo Rich Text

# --- Propiedades en Base de Datos de PROYECTOS ---
# *** NOTION_PROP_PROYECTO_BUSQUEDA_ID: El nombre de la propiedad en tu BD de PROYECTOS que usas para IDENTIFICAR UN PROYECTO (ej. "Número de Proyecto", "Código", "Nombre") ***
NOTION_PROP_PROYECTO_BUSQUEDA_ID = "ID del proyecto" # <<<< Nombre EXACTO de la propiedad para BUSCAR en BD Proyectos <<<<


# --- Fin Nombres de Propiedad ---


# --- Funciones Auxiliares Generales ---

def get_database_properties_util(notion_client: Client, database_id: str) -> Dict[str, Dict]:
    """Obtiene el diccionario de propiedades de una base de datos de Notion."""
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para obtener propiedades.")
        return {}
    try:
        database_info = notion_client.databases.retrieve(database_id)
        properties = database_info.get("properties", {})
        # logger.debug(f"Propiedades obtenidas de la base de datos {database_id}: {', '.join(properties.keys())}") # Demasiado verbose
        return properties
    except Exception as e:
        logger.error(f"Error al obtener propiedades de la base de datos {database_id}: {str(e)}", exc_info=True)
        return {}

def create_filter_condition_util(property_name: str, property_type: str, value: Any) -> Dict:
     """Construye una condición de filtro para consultas a la API de Notion."""
     # Maneja casos comunes de tipos de propiedades para filtrado.
     # Asume que para 'text', 'rich_text', 'title', 'url', 'email', 'phone_number' usas el filtro 'contains'
     # Asume que para 'number', 'select', 'checkbox' usas el filtro 'equals'
     # Relaciones y Multi-select son más complejos, aquí implementamos casos básicos si necesitas buscarlos.
     if value is None or str(value).strip() == "": # Un valor vacío no genera una condición de filtro "positive match"
          # Si quieres buscar campos vacíos, la lógica debe ser {"is_empty": true}. Esto no se maneja aquí.
          logger.warning(f"Valor nulo o vacío para crear filtro de propiedad '{property_name}'. Omitiendo.")
          return {}

     cleaned_value = str(value).strip()

     if property_type in ["text", "rich_text", "title", "url", "email", "phone_number"]:
          # Filtro 'contains' para campos de texto
          return { "property": property_name, property_type if property_type != 'text' else 'rich_text' : { "contains": cleaned_value } } # Usar rich_text en lugar de text
     elif property_type == "number":
         try:
             float_value = float(cleaned_value)
             return { "property": property_name, "number": { "equals": float_value } }
         except (ValueError, TypeError):
             logger.warning(f"Valor '{value}' no es un número válido para filtro 'equals' en propiedad Number '{property_name}'.")
             return {}
     elif property_type == "select":
         # Filtro 'equals' para Select
         return { "property": property_name, "select": { "equals": cleaned_value } }
     elif property_type == "checkbox":
         # Filtro 'equals' para Checkbox
         bool_value = cleaned_value.lower() in ['true', 'yes', 'on', '1'] # Intenta convertir a booleano
         return { "property": property_name, "checkbox": { "equals": bool_value } }
     elif property_type == "multi_select":
          # Filtro 'contains' para Multi-select (busca si contiene UNA opción específica)
          return { "property": property_name, "multi_select": { "contains": cleaned_value } }
     # Añadir otros tipos de propiedades según necesidad para filtrado
     # elif property_type == "relation":
     #     # Filtrar por Relation es más complejo, generalmente se busca si CONTIENE la página por su ID.
     #     # Si el value es un page_id válido:
     #     if is_valid_notion_id(cleaned_value): # Debes tener una función para validar IDs si usas esto
     #          return { "property": property_name, "relation": { "contains": cleaned_value } }
     #     else:
     #          logger.warning(f"Valor '{value}' no parece un Page ID válido para filtro Relation en propiedad '{property_name}'.")
     #          return {}


     else:
         logger.warning(f"Tipo de propiedad no soportado para filtrado en create_filter_condition_util: '{property_type}' para propiedad '{property_name}'.")
         return {}


def get_pages_with_filter_util(notion_client: Client, database_id: str, filters: List[Dict] = None, page_size: int = 100) -> List[Dict]:
    """Ejecuta una consulta filtrada a una base de datos de Notion."""
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para obtener páginas con filtro.")
        return []
    all_pages = []
    has_more = True
    start_cursor = None

    try:
        query_args = {
            "database_id": database_id,
            "page_size": page_size,
        }

        filter_arg = None
        if filters and len(filters) > 0:
            if len(filters) == 1:
                filter_arg = filters[0]
            else:
                # Usar filtro 'and' para combinar múltiples condiciones
                filter_arg = { "and": filters }


        if filter_arg is not None:
             query_args["filter"] = filter_arg
             # logger.debug(f"Filtros aplicados a consulta Notion para {database_id}: {json.dumps(filter_arg, ensure_ascii=False)}")


        while has_more:
            if start_cursor:
                query_args["start_cursor"] = start_cursor

            response = notion_client.databases.query(**query_args)

            data = response

            results = data.get("results", [])
            all_pages.extend(results)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            # logger.debug(f"Obtenidas {len(results)} páginas con filtros de {database_id}. Total acumulado: {len(all_pages)}")

    except APIResponseError as e:
        logger.error(f"Error API al consultar base de datos {database_id}: Código={e.code if hasattr(e, 'code') else 'N/A'} Mensaje={e.message if hasattr(e, 'message') else str(e)}", exc_info=True)
        notion_response_body = getattr(e, 'response', None)
        if notion_response_body:
             try: logger.error(f"Detalles adicionales del error de Notion (Consulta DB {database_id}): {json.dumps(notion_response_body.json(), ensure_ascii=False)}")
             except Exception: pass

    except Exception as e:
        logger.error(f"Error inesperado al obtener páginas de Notion con filtros de {database_id}: {str(e)}", exc_info=True)

    logger.info(f"Consulta a DB {database_id} completada. Total de páginas encontradas: {len(all_pages)}")
    return all_pages

def update_notion_page_properties(notion_client: Client, page_id: str, properties_to_update: Dict) -> Tuple[int, Dict]:
    """
    Actualiza propiedades generales de una página de Notion.
    properties_to_update debe ser un diccionario con el formato de la API de Notion.
    Ej: {"Nombre Propiedad": {"tipo_propiedad": {...}}, ...}
    """
    if not notion_client or not page_id or not properties_to_update:
         logger.error("Cliente de Notion, Page ID o propiedades a actualizar faltantes.")
         return 400, {"error": "Request inválido."} # Bad Request

    payload = {
        "properties": properties_to_update
    }

    try:
        # logger.debug(f"Intentando actualizar propiedades para página {page_id}: {properties_to_update}") # Muy verbose
        response = notion_client.pages.update(page_id=page_id, properties=payload["properties"])
        logger.info(f"Página {page_id} actualizada correctamente")
        # El cliente Notion no devuelve status_code directamente en el éxito, asumimos 200
        return 200, response
    except APIResponseError as e:
        logger.error(f"Error API al actualizar página {page_id}: Código={e.code if hasattr(e, 'code') else 'N/A'} Mensaje={e.message if hasattr(e, 'message') else str(e)}", exc_info=True)
        notion_response_body = getattr(e, 'response', None)
        notion_error_details = None
        if notion_response_body:
             try: notion_error_details = notion_response_body.json()
             except Exception: pass

        return e.status, {"error": f"Notion API Error: {e.message if hasattr(e, 'message') else str(e)}", "code": e.code if hasattr(e, 'code') else 'N/A', "notion_error_details": notion_error_details}
    except Exception as e:
        logger.error(f"Error inesperado al actualizar página {page_id}: {str(e)}", exc_info=True)
        return 500, {"error": f"Error interno: {str(e)}"}


# --- Funciones Auxiliares para Ajuste de Horarios ---

def update_page_util(notion_client: Client, page_id: str, new_start: datetime, new_end: Optional[datetime]) -> Tuple[int, Dict]:
    """Actualiza la propiedad de Fecha (Date) de una página específica."""
    # Reutiliza update_notion_page_properties
    properties_to_update = {
        DATE_PROPERTY_NAME: {"date": {"start": new_start.isoformat(), "end": new_end.isoformat() if new_end else None}}
    }
    logger.info(f"Intentando actualizar fecha en página {page_id}")
    return update_notion_page_properties(notion_client, page_id, properties_to_update)


def adjust_dates_with_filters_util(
    notion_client: Client,
    database_id: str,
    hours: int,
    start_date: datetime,
    filters: List[Dict[str, Any]] = None
) -> str:
    """
    Busca páginas en una base de datos usando filtros y ajusta sus fechas.
    Usada por adjust_dates_api (modulo Ajustes). No se usa en Solicitudes de Materiales.
    """
    if not notion_client or not database_id:
         return "Error interno: Cliente de Notion o Database ID faltante."

    pages = get_pages_with_filter_util(notion_client, database_id, filters)
    total_pages = len(pages)
    updated_pages = 0
    failed_updates = 0
    skipped_pages = 0

    filter_description = "ninguno"
    if filters and len(filters) > 0:
        try:
             filter_desc_parts = []
             for f in filters:
                  prop_name = f.get("property", "desconocido")
                  filter_value_desc = "valor"
                  for key, val in f.items():
                      if key not in ['property', 'and', 'or', 'not']:
                           if isinstance(val, dict) and len(val) == 1:
                                condition_key = list(val.keys())[0]
                                if condition_key in ['equals', 'contains', 'starts_with', 'ends_with', 'greater_than', 'less_than', 'is_empty']:
                                    filter_value_text = 'vacío' if condition_key == 'is_empty' else str(val[condition_key])[:50]
                                    filter_value_desc = f"{condition_key.replace('_', ' ')} '{filter_value_text}'"
                                else:
                                     filter_value_desc = f"condición: {str(val)[:50]}"
                           else:
                                filter_value_desc = str(val).replace('_', ' ')

                  filter_desc_parts.append(f"{prop_name} {filter_value_desc}")
             filter_description = ", ".join(filter_desc_parts)
        except Exception:
             filter_description = "detalles no disponibles (error al parsear filtros)"

    logger.info(f"Iniciando ajuste de fechas en {database_id}: {hours} horas a partir de {start_date.isoformat()}. Filtros: {filter_description}. Total de páginas encontradas para procesar: {total_pages}")


    if total_pages == 0:
        resumen = f"Operación completada: No se encontraron registros que coincidieran con los filtros. Filtros: {filter_description}."
        logger.info(f"Ajuste de fechas completado con 0 páginas encontradas.")
        return resumen

    for page in pages:
        properties = page.get("properties", {})
        page_id = page.get("id")

        if not page_id:
            logger.warning("Página sin ID encontrada, omitiendo.")
            skipped_pages += 1
            continue

        date_property_value = properties.get(DATE_PROPERTY_NAME, {}).get("date", {})

        if date_property_value and "start" in date_property_value:
            try:
                start_date_notion_str = date_property_value["start"]
                start_date_notion = datetime.fromisoformat(start_date_notion_str.replace('Z', '+00:00') if start_date_notion_str and start_date_notion_str.endswith('Z') else start_date_notion_str).replace(tzinfo=None)

                if start_date_notion >= start_date:
                    new_start = start_date_notion + timedelta(hours=hours)

                    new_end = None
                    if date_property_value.get("end"):
                         end_date_notion_str = date_property_value["end"]
                         end_date_notion = datetime.fromisoformat(end_date_notion_str.replace('Z', '+00:00') if end_date_notion_str and end_date_notion_str.endswith('Z') else end_date_notion_str).replace(tzinfo=None)
                         new_end = end_date_notion + timedelta(hours=hours)

                    properties_to_update = {
                         DATE_PROPERTY_NAME: {"date": {"start": new_start.isoformat(), "end": new_end.isoformat() if new_end else None}}
                    }

                    status_code, update_response = update_notion_page_properties(notion_client, page_id, properties_to_update)

                    if 200 <= status_code < 300:
                        updated_pages += 1
                    else:
                        failed_updates += 1
                        logger.error(f"Fallo al actualizar fecha en página {page_id}: Estado={status_code}, Respuesta={update_response.get('error', 'Desconocido')}. Notion Msg: {update_response.get('notion_message', 'N/A')}")
                else:
                    logger.info(f"Página {page_id} con fecha {start_date_notion.strftime('%Y-%m-%d')} anterior al filtro {start_date.strftime('%Y-%m-%d')}, omitiendo.")
                    skipped_pages += 1

            except (ValueError, TypeError) as e:
                logger.error(f"Error al procesar o parsear fecha de página {page_id}: {str(e)}", exc_info=True)
                failed_updates += 1
            except Exception as e:
                 logger.error(f"Error inesperado al procesar página {page_id}: {str(e)}", exc_info=True)
                 failed_updates += 1
        else:
             logger.info(f"Página {page_id} sin fecha válida en propiedad '{DATE_PROPERTY_NAME}', omitiendo.")
             skipped_pages += 1


    logger.info(f"Proceso de ajuste de fechas completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")

    resumen = (
        f"Resumen del Ajuste de Fechas:\n"
        f"Filtros aplicados: {filter_description}\n"
        f"Total de registros encontrados: {total_pages}\n"
        f"Registros actualizados con éxito: {updated_pages}\n"
        f"Registros omitidos: {skipped_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: {hours} horas a partir del {start_date.strftime('%Y-%m-%d')}"
    )

    if failed_updates > 0:
         resumen += f"\n¡ADVERTENCIA! Hubo {failed_updates} actualizaciones fallidas. Revisa los logs del servidor para más detalles."

    return resumen


def build_filter_from_properties_util(notion_client: Client, database_id: str, property_filters: Dict[str, Any]) -> List[Dict]:
    """
    Construye una lista de objetos filtro para consultas a la API de Notion
    basado en un diccionario de propiedades y sus valores.
    """
    if not property_filters:
        return []
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para construir filtros.")
        return []

    filters = []
    db_properties = get_database_properties_util(notion_client, database_id)

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos '{database_id}', omitiendo filtro para esta propiedad.")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")

        filter_condition = create_filter_condition_util(prop_name, prop_type, prop_value)

        if filter_condition:
            filters.append(filter_condition)
        else:
             logger.warning(f"No se pudo crear condición de filtro válida para propiedad '{prop_name}' con valor '{prop_value}' (tipo '{prop_type}').")

    # logger.debug(f"Filtros construidos para DB {database_id}: {filters}") # Demasiado verbose
    return filters

# *** FUNCIÓN adjust_dates_api (llamada desde ajustes.py) ***
def adjust_dates_api(
    notion_client: Client,
    database_id: str, # Este es el ID de la base de datos de Ajustes/Proyectos (donde se ajustan fechas)
    hours: int,
    start_date_str: str,
    property_filters: Dict[str, Any] = None
) -> Tuple[Dict, int]: # Retorna (respuesta_dict, status_code HTTP)
    """
    Endpoint lógica para ajustar fechas en registros de Notion basado en filtros.
    """
    if not notion_client or not database_id:
         error_msg = "Cliente de Notion no inicializado o Database ID faltante para Ajustes."
         logger.error(error_msg)
         return {
            "success": False,
            "error": error_msg,
            "status_code": 503
        }, 503 # Service Unavailable

    try:
        # Validar y convertir la fecha de string a objeto datetime
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        # Construir los filtros para la consulta a Notion
        filters = build_filter_from_properties_util(notion_client, database_id, property_filters) if property_filters else []

        # Llamar a la función auxiliar que realiza el ajuste de fechas con los filtros
        result_message = adjust_dates_with_filters_util(notion_client, database_id, hours, start_date, filters)

        # Determinar el status code de la respuesta API basado en el mensaje resumen
        status_code_return = 200
        if "¡ADVERTENCIA!" in result_message or "fallidas" in result_message:
             status_code_return = 207 # Partial Content

        return {
            "success": True,
            "message": result_message,
            "status_code": status_code_return
        }, status_code_return


    except ValueError as e:
        error_msg = f"Formato de fecha inválido o error en conversión: {str(e)}. Asegúrate de usar formato AAAA-MM-DD."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 400
        }, 400

    except Exception as e:
        error_msg = f"Error inesperado al ajustar fechas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 500
        }, 500

def list_available_properties(notion_client: Client, database_id: str) -> List[Dict[str, str]]:
    """Lista propiedades disponibles de una base de datos dada."""
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para listar propiedades.")
        return []
    try:
        properties = get_database_properties_util(notion_client, database_id)
        property_list = []
        for name, info in properties.items():
            prop_type = info.get("type", "unknown")
            prop_id = info.get("id", name)
            property_list.append({
                "name": name,
                "type": prop_type,
                "id": prop_id
            })
        # logger.debug(f"Listadas {len(property_list)} propiedades para DB {database_id}.") # Demasiado verbose
        return property_list
    except Exception as e:
        logger.error(f"Error al listar propiedades de la base de datos {database_id}: {e}", exc_info=True)
        return []


# *** FUNCIÓN find_project_page_by_property_value (NUEVA - para buscar proyectos) ***
def find_project_page_by_property_value(
    notion_client: Client,
    database_id_proyectos: str, # ID de la BD de Proyectos
    property_name: str,        # Nombre de la propiedad para buscar (ej. "Número de Proyecto")
    property_value: Any        # Valor a buscar
) -> Optional[str]:
    """
    Busca una página en la base de datos de Proyectos por el valor de una propiedad específica.
    Devuelve el page_id si encuentra una página, None en caso contrario.
    """
    if not notion_client or not database_id_proyectos or not property_name or property_value is None or str(property_value).strip() == "":
        logger.warning(f"Datos insuficientes para buscar página de proyecto. DB ID Proyectos: {database_id_proyectos}, Prop Nombre: '{property_name}', Prop Valor: '{property_value}'")
        return None

    try:
        # Obtenemos las propiedades de la BD de Proyectos para saber el tipo de propiedad de búsqueda.
        # Hacemos esto solo una vez al principio de la búsqueda.
        db_proyectos_properties = get_database_properties_util(notion_client, database_id_proyectos)

        if property_name not in db_proyectos_properties:
            logger.warning(f"Propiedad de búsqueda '{property_name}' no encontrada en la base de datos de Proyectos '{database_id_proyectos}'. No se puede buscar el proyecto.")
            return None

        prop_info = db_proyectos_properties[property_name]
        prop_type = prop_info.get("type")

        # Crear una condición de filtro usando el tipo y valor
        # Usar "equals" para buscar coincidencias exactas para identificadores
        # O "contains" si se espera que el valor del formulario esté contenido en la propiedad de Notion
        # Decidimos usar 'equals' para Select y Number, y 'contains' para Rich Text/Title por flexibilidad.
        filter_condition = {}
        cleaned_value = str(property_value).strip()

        if prop_type == "select":
             filter_condition = { "property": property_name, "select": { "equals": cleaned_value } }
        elif prop_type == "number":
             try:
                 float_value = float(cleaned_value)
                 filter_condition = { "property": property_name, "number": { "equals": float_value } }
             except (ValueError, TypeError):
                  logger.warning(f"Valor '{cleaned_value}' no es un número válido para buscar en propiedad Number '{property_name}'.")
                  return None
        elif prop_type in ["rich_text", "title", "url", "email", "phone_number"]:
             # Usamos contains para texto, título, etc.
             filter_condition = { "property": property_name, prop_type if prop_type != 'text' else 'rich_text': { "contains": cleaned_value } } # Usar rich_text en lugar de text
             # Si necesitas coincidencia exacta con Rich Text, usar {"rich_text": {"equals": [{"text": {"content": cleaned_value}}]}} - más complejo

        # Añadir otros tipos si es necesario


        if not filter_condition: # Doble check si no se pudo crear la condición (ej. tipo no manejado)
            logger.warning(f"No se pudo crear condición de filtro válida para buscar página de proyecto. Prop: '{property_name}', Tipo: '{prop_type}', Valor: '{property_value}'")
            return None


        # Usar get_pages_with_filter_util para buscar la(s) página(s). Limitamos a 2 para detectar posibles duplicados.
        # get_pages_with_filter_util ya incluye logging.
        found_pages = get_pages_with_filter_util(
            notion_client,
            database_id_proyectos,
            filters=[filter_condition],
            page_size=2 # Obtenemos hasta 2 resultados
        )

        if found_pages:
            if len(found_pages) > 1:
                 logger.warning(f"Múltiples páginas encontradas en DB Proyectos para filtro '{property_name}'='{property_value}'. Usando la primera encontrada.")

            # Asumimos que la primera coincidencia es la correcta.
            project_page_id = found_pages[0].get("id")
            if project_page_id:
                # logger.debug(f"Página de proyecto encontrada con ID={project_page_id}.") # Ya se loggea en get_pages_with_filter_util
                return project_page_id
            else:
                logger.warning(f"Página encontrada para filtro '{property_name}'='{property_value}', pero el objeto de página no tiene ID válido. Omitiendo.")
                return None
        else:
            logger.warning(f"No se encontró ninguna página en DB Proyectos con filtro '{property_name}'='{property_value}'.")
            return None

    except Exception as e:
        logger.error(f"Error inesperado al buscar página de proyecto para valor '{property_value}': {e}", exc_info=True)
        return None


# --- Lógica para Solicitudes de Materiales (CORREGIDA PARA RELATION DE PROYECTO) ---

# Función principal llamada desde la ruta /solicitudes/submit_standard en solicitudes.py
# Recibe el cliente Notion, IDs de DBs de Materiales y de Proyectos, y el diccionario 'data'
# Devuelve (respuesta_dict, status_code HTTP)
def submit_request_for_material_logic(
        notion_client: Client,
        database_id_db1: str,
        database_id_db2: str,
        database_id_proyectos: str, # <<<< NUEVO ARGUMENTO: ID de la BD de Proyectos <<<<
        data: Dict,
        user_id: Optional[int] = None
    ) -> Tuple[Dict, int]:

    # El bloque try/except debe envolver la lógica principal
    try:
        # user_log_prefix se define pronto, usar un default hasta entonces
        user_log_prefix_initial = f"[User ID: {user_id or 'N/A'}] Folio: N/A"
        logger.info(f"{user_log_prefix_initial} Iniciando procesamiento de solicitud de material...")


        folio_solicitud = data.get("folio_solicitud")
        if not folio_solicitud:
             folio_solicitud = f"EMG-BE-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
             logger.warning(f"{user_log_prefix_initial} Folio de solicitud no recibido del frontend. Generando fallback: {folio_solicitud}")

        # Ahora que tenemos el folio (generado o del frontend), actualizamos el prefijo para logs subsiguientes
        user_log_prefix = f"[User ID: {user_id or 'N/A'}] Folio: {folio_solicitud}"
        logger.info(f"{user_log_prefix} Prefijo de log establecido.")


        items_processed_count = 0
        items_failed_count = 0
        first_page_total_success_url1 = None # Guarda la URL de la PRIMERA página creada con ÉXITO en DB1
        first_page_total_success_url2 = None # Guarda la URL de la PRIMERA página creada con ÉXITO en DB2


        # *** VALIDACIÓN DE IDs DE BASE DE DATOS ***
        # Incluye la validación para database_id_proyectos aquí también
        if not notion_client or not database_id_db1 or not database_id_db2 or not database_id_proyectos: # <<<< Incluye database_id_proyectos
             error_msg = "La integración con Notion para Solicitudes o Proyectos no está configurada correctamente (IDs o cliente faltante)."
             logger.error(f"{user_log_prefix} {error_msg}")
             # Es un problema de configuración del servidor, no del usuario
             return {"error": error_msg, "folio_solicitud": folio_solicitud}, 503 # Service Unavailable


        if not data:
            logger.warning(f"{user_log_prefix} No se recibieron datos válidos en submit_request_for_material_logic.")
            return {"error": "No se recibieron datos válidos."}, 400

        selected_proveedor = data.get("proveedor")
        is_torni_mode = selected_proveedor == 'Torni'


        # --- PROPIEDAD DEL PROYECTO (BUSQUEDA Y RELATION) ---
        proyecto_valor_frontend = data.get("proyecto", "") # Valor ingresado en el formulario
        project_page_id = None # Variable para guardar el ID de la página de proyecto encontrada

        # Buscar la página del proyecto en la BD de Proyectos si se proporcionó un valor en el frontend
        if proyecto_valor_frontend and database_id_proyectos: # Asegúrate de que hay un valor Y un ID de BD de proyectos configurado
             logger.info(f"{user_log_prefix}: Buscando ID de página para proyecto: '{proyecto_valor_frontend}' en BD Proyectos '{database_id_proyectos}'...")
             # Usar la función de búsqueda
             project_page_id = find_project_page_by_property_value(
                 notion_client,
                 database_id_proyectos,
                 NOTION_PROP_PROYECTO_BUSQUEDA_ID, # Nombre de la propiedad en la BD de Proyectos para buscar
                 proyecto_valor_frontend # El valor a buscar
             )
             if project_page_id:
                  logger.info(f"{user_log_prefix}: ID de página de proyecto encontrado: {project_page_id}")
             else:
                  logger.warning(f"{user_log_prefix}: No se encontró página de proyecto para '{proyecto_valor_frontend}'. La propiedad Relation en Notion quedará vacía.")
                  # Si un proyecto *válido existente en Notion* es obligatorio, descomenta lo siguiente:
                  # error_msg = f"No se encontró ningún proyecto existente con el valor '{proyecto_valor_frontend}'. Verifica el código del proyecto."
                  # logger.warning(f"{user_log_prefix} {error_msg}")
                  # return {"error": error_msg, "folio_solicitud": folio_solicitud}, 400 # Bad Request


        # --- Construir Propiedad RELATION 'Proyecto' ---
        # Esta propiedad se añade a common_properties para aplicarse a cada item
        # La propiedad en la BD de Materiales se llama NOTION_PROP_MATERIALES_PROYECTO_RELATION
        project_relation_property = {"relation": []} # Relación vacía por defecto
        if project_page_id:
            project_relation_property = {"relation": [{"id": project_page_id}]} # Relación con el ID encontrado

        # Añadir la propiedad Relation al diccionario común
        # Asegúrate de usar la constante correcta para la propiedad RELATION en la BD de Materiales
        common_properties[NOTION_PROP_MATERIALES_PROYECTO_RELATION] = project_relation_property


        # --- Propiedades Comunes restantes (aplican a cada página creada para un item) ---
        # Estas se extraen directamente del diccionario 'data' principal y se añaden a common_properties.

        # Folio (Generalmente Rich Text o Title)
        if folio_solicitud:
             # Ya se añadió arriba al generar el folio si no venía y se puso en common_properties.
             # Si quieres que Folio sea la propiedad Title de la página en Notion DB1:
             # common_properties[NOTION_PROP_FOLIO] = {"title": [{"type": "text", "text": {"content": folio_solicitud}}]} # Asumiendo Folio es el Title
             # Pero si Folio NO es la propiedad Title y es Rich Text:
             # Ya se añadió arriba, no hacer nada más aquí.
             pass


        # Solicitante, Proveedor, Departamento/Área (ASUMIMOS SELECT)
        solicitante_val = data.get("nombre_solicitante", "")
        # Ya se añadió a common_properties arriba. Si es Select, el valor vacío ("") dará error si la opción no existe.
        # La validación frontend ya asegura que no esté vacío.

        proveedor_val = selected_proveedor or ""
        # Ya se añadió a common_properties arriba.

        departamento_val = data.get("departamento_area", "")
        # Ya se añadió a common_properties arriba.


        # Fecha de solicitud (Date)
        # Ya se añadió arriba en common_properties si el formato es válido.

        # Especificaciones adicionales (Opcional, Rich Text)
        # Ya se añadió arriba en common_properties si no está vacío.


        # --- Determinar la lista final de items a procesar ---
        items_to_process_list = []

        if is_torni_mode:
             torni_items_list_from_data = data.get('torni_items', [])
             if not isinstance(torni_items_list_from_data, list):
                  logger.error(f"{user_log_prefix}: Se esperaba una lista para 'torni_items', pero se recibió {type(torni_items_list_from_data)}. No se procesarán items Torni.")
                  return {"error": "Datos de productos Torni inválidos recibidos. Se esperaba una lista."}, 400

             valid_torni_items = []
             for idx, item in enumerate(torni_items_list_from_data):
                  quantity = item.get("quantity")
                  item_id = item.get("id")
                  item_desc = item.get("description")

                  is_quantity_valid = isinstance(quantity, (int, float)) and quantity >= 0
                  is_id_valid = item_id is not None and str(item_id).strip() != ""
                  is_desc_valid = item_desc is not None and str(item_desc).strip() != ""

                  if not is_quantity_valid or not is_id_valid or not is_desc_valid:
                       logger.warning(f"{user_log_prefix}: Item Torni incompleto o inválido en índice {idx}: {item}. Req: quantity(num), id(str/num), description(str). Omitiendo.")
                       continue

                  valid_torni_items.append(item)

             items_to_process_list = valid_torni_items

        else: # Proveedor estándar
             # En modo estándar, el diccionario 'data' contiene los campos del único item.
             # Verificamos si data contiene al menos un campo indicativo de un item estándar
             # para evitar procesar un diccionario 'data' completamente vacío.
             # La validación frontend maneja campos obligatorios. Aquí solo checkeamos si hay ALGO de data item.
             if any(data.get(key) is not None and str(data.get(key)).strip() != "" for key in ['nombre_material', 'cantidad_solicitada', 'unidad_medida', 'largo', 'ancho', 'alto', 'diametro', 'tipo_material']):
                items_to_process_list = [data] # Lista con un solo item
             else:
                 logger.warning(f"{user_log_prefix}: Diccionario 'data' estándar vacío de campos de item principal. No se procesará.")


        if not items_to_process_list:
             logger.warning(f"{user_log_prefix}: No hay items válidos para procesar después de determinar la lista.")
             return {"error": "No hay items válidos para procesar. Asegúrate de llenar la información del material."}, 400


        logger.info(f"{user_log_prefix}: Items a procesar ({'Torni' if is_torni_mode else 'Estándar'}): {len(items_to_process_list)}")


        # --- Iterar sobre la lista FINAL de items a procesar y crear páginas en Notion ---
        for index, item_data in enumerate(items_to_process_list):
            item_index_str = f"Item {index + 1}"
            logger.info(f"{user_log_prefix}: --- Procesando {item_index_str} ---")

            # Copiar propiedades comunes (incluyendo la Relation del Proyecto) e inicializar con ellas.
            item_properties = common_properties.copy();

            # --- Construir Propiedades ESPECÍFICAS para este item ---
            # Extraer los valores de item_data. Usar .get() con valor por defecto para seguridad.

            quantity = item_data.get("cantidad_solicitada")
            tipo_material = item_data.get("tipo_material", "")
            nombre_material = item_data.get("nombre_material", "")
            unidad_medida = item_data.get("unidad_medida", "")
            largo = item_data.get("largo")
            ancho = item_data.get("ancho")
            alto = item_data.get("alto")
            diametro = item_data.get("diametro")


            # Cantidad (Number)
            cantidad_num_val = None
            if quantity is not None and str(quantity).strip() != "":
                 try:
                     cantidad_num_val = float(str(quantity).strip())
                 except (ValueError, TypeError):
                      logger.warning(f"{user_log_prefix}: {item_index_str} - Cantidad '{quantity}' no es numérica válida. Se enviará null a Notion.")
                      cantidad_num_val = None
            if cantidad_num_val is not None:
                 item_properties[NOTION_PROP_CANTIDAD] = {"number": cantidad_num_val}


            # Tipo de material, Nombre de material, Unidad de medida (ASUMIDO SELECT)
            if tipo_material: item_properties[NOTION_PROP_TIPO_MATERIAL] = {"select": {"name": tipo_material}}
            # else: if NOTION_PROP_TIPO_MATERIAL: item_properties[NOTION_PROP_TIPO_MATERIAL] = {"select": None}

            if nombre_material: item_properties[NOTION_PROP_NOMBRE_MATERIAL] = {"select": {"name": nombre_material}}
            # else: if NOTION_PROP_NOMBRE_MATERIAL: item_properties[NOTION_PROP_NOMBRE_MATERIAL] = {"select": None}

            if unidad_medida: item_properties[NOTION_PROP_UNIDAD_MEDIDA] = {"select": {"name": unidad_medida}}
            # else: if NOTION_PROP_UNIDAD_MEDIDA: item_properties[NOTION_PROP_UNIDAD_MEDIDA] = {"select": None}


            # Dimensiones (ASUMIDO RICH TEXT)
            if largo is not None and str(largo).strip() != "":
                 item_properties[NOTION_PROP_LARGO] = {"rich_text": [{"type": "text", "text": {"content": str(largo).strip()}}]}

            if ancho is not None and str(ancho).strip() != "":
                 item_properties[NOTION_PROP_ANCHO] = {"rich_text": [{"type": "text", "text": {"content": str(ancho).strip()}}]}

            if alto is not None and str(alto).strip() != "":
                 item_properties[NOTION_PROP_ALTO] = {"rich_text": [{"type": "text", "text": {"content": str(alto).strip()}}]}

            if diametro is not None and str(diametro).strip() != "":
                 item_properties[NOTION_PROP_DIAMETRO] = {"rich_text": [{"type": "text", "text": {"content": str(diametro).strip()}}]}


            # Si es modo Torni, añadir las propiedades específicas
            if is_torni_mode:
                 item_id_torni = item_data.get("id", "")
                 item_desc_torni = item_data.get("description", "")
                 if item_id_torni: item_properties[NOTION_PROP_TORNI_ID] = {"rich_text": [{"type": "text", "text": {"content": str(item_id_torni).strip()}}]}
                 if item_desc_torni: item_properties[NOTION_PROP_TORNI_DESCRIPTION] = {"rich_text": [{"type": "text", "text": {"content": str(item_desc_torni).strip()}}]}


            # --- DEBUG: Log de propiedades listas para enviar para este item ---
            logger.debug(f"{user_log_prefix}: {item_index_str} - Propiedades para enviar a Notion: {json.dumps(item_properties, ensure_ascii=False, indent=2)}")


            # --- Crear página en DB 1 ---
            page1_created = False; page1_url_current = None; error1_info = {}
            try:
                logger.info(f"{user_log_prefix}: {item_index_str} - Intentando crear página en DB 1 Materiales ({database_id_db1})...")
                response1 = notion_client.pages.create(parent={"database_id": database_id_db1}, properties=item_properties)
                page1_url_current = response1.get("url")
                if first_page_total_success_url1 is None and page1_url_current: # Guarda la URL del primer item creado con ÉXITO en DB1
                     first_page_total_success_url1 = page1_url_current

                logger.info(f"{user_log_prefix}: {item_index_str} - Página creada en DB 1: {page1_url_current}")
                page1_created = True
            except APIResponseError as e1:
                 api_error_msg = e1.message if hasattr(e1, 'message') else str(e1)
                 notion_response_body = getattr(e1, 'response', None)
                 notion_error_details = None
                 if notion_response_body:
                      try: notion_error_details = notion_response_body.json()
                      except Exception: pass

                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR API en DB 1 Materiales: Código={e1.code if hasattr(e1, 'code') else 'N/A'} Mensaje={api_error_msg}", exc_info=True)
                 if notion_error_details: logger.error(f"Detalles adicionales del error de Notion (DB 1): {json.dumps(notion_error_details, ensure_ascii=False)}")
                 error1_info = {"code": e1.code if hasattr(e1, 'code') else 'N/A', "message": api_error_msg, "notion_error_details": notion_error_details}
            except Exception as e1:
                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR inesperado en DB 1 Materiales: {e1}", exc_info=True)
                 error1_info = {"message": str(e1)}


            # --- Crear página en DB 2 ---
            page2_created = False; page2_url_current = None; error2_info = {}
            try:
                logger.info(f"{user_log_prefix}: {item_index_str} - Intentando crear página en DB 2 Materiales ({database_id_db2})...")
                response2 = notion_client.pages.create(parent={"database_id": database_id_db2}, properties=item_properties)
                page2_url_current = response2.get("url")
                if first_page_total_success_url2 is None and page2_url_current: # Guarda la URL del primer item creado con ÉXITO en DB2
                     first_page_total_success_url2 = page2_url_current


                logger.info(f"{user_log_prefix}: {item_index_str} - Página creada en DB 2: {page2_url_current}")
                page2_created = True
            except APIResponseError as e2:
                 api_error_msg = e2.message if hasattr(e2, 'message') else str(e2)
                 notion_response_body = getattr(e2, 'response', None)
                 notion_error_details = None
                 if notion_response_body:
                      try: notion_error_details = notion_response_body.json()
                      except Exception: pass

                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR API en DB 2 Materiales: Código={e2.code if hasattr(e2, 'code') else 'N/A'} Mensaje={api_error_msg}", exc_info=True)
                 if notion_error_details: logger.error(f"Detalles adicionales del error de Notion (DB 2): {json.dumps(notion_error_details, ensure_ascii=False)}")
                 error2_info = {"code": e2.code if hasattr(e2, 'code') else 'N/A', "message": api_error_msg, "notion_error_details": notion_error_details}

            except Exception as e2:
                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR inesperado en DB 2 Materiales: {e2}", exc_info=True)
                 error2_info = {"message": str(e2)}


            # Contar items procesados/fallidos
            if page1_created and page2_created:
                items_processed_count += 1
                logger.info(f"{user_log_prefix}: {item_index_str} procesado con éxito en ambas DBs.")
                # Si este es el primer item que se procesa COMPLETAMENTE con éxito en ambas DBs
                # No necesitamos re-asignar here, already done when setting the first URL found.
                pass # Logic to update first_page_total_success_url1/2 is outside the loop.
            else:
                 items_failed_count += 1
                 error_details = {
                     "item_index": index + 1,
                     "item_data_sent_partial": {k: item_data.get(k) for k in ['cantidad_solicitada', 'nombre_material', 'unidad_medida', 'largo', 'ancho', 'alto', 'diametro', 'id', 'description', 'tipo_material', 'nombre_solicitante', 'proveedor', 'departamento_area', 'fecha_solicitud', 'proyecto', 'especificaciones_adicionales']} if not is_torni_mode else item_data,
                     "db1_success": page1_created, "db1_error": error1_info,
                     "db2_success": page2_created, "db2_error": error2_info
                 }
                 #logger.debug(f"{user_log_prefix}: {item_index_str} - Propiedades que causaron el fallo: {json.dumps(item_properties, ensure_ascii=False, indent=2)}")
                 logger.error(f"{user_log_prefix}: {item_index_str} falló al procesar. Detalles resumen: {json.dumps(error_details, ensure_ascii=False)}")


        # --- Fin del bucle for ---

        # --- Construir Respuesta Final ---
        final_response = {"folio_solicitud": folio_solicitud}
        status_code_return = 200 # Default éxito
        total_items_intended = len(items_to_process_list)

        # Si hubo al menos un item procesado con éxito en ambas DBs, usamos sus URLs para la respuesta.
        # Los first_page_total_success_url1/2 se guardan la primera vez que una página se crea CON ÉXITO en su respectiva DB.
        if items_processed_count > 0 and items_failed_count == 0:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count}/{total_items_intended} item(s)) registrada con éxito en ambas DBs."
             # Usamos las URLs de la primera página que se creó en cada DB
             final_response["notion_url"] = first_page_total_success_url1 # URL de la 1ra página creada en DB1
             final_response["notion_url_db2"] = first_page_total_success_url2 # URL de la 1ra página creada en DB2 (si aplica)
             status_code_return = 200

        elif items_processed_count > 0 and items_failed_count > 0:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count}/{total_items_intended} item(s) OK, {items_failed_count} fallaron. Ver logs del servidor para detalles."
             # Si hubo éxito parcial, mostramos las URLs del primer item que tuvo éxito TOTAL (si existió)
             # o las URLs de la primera página creada en cada DB si no hubo éxito total en un solo item
             final_response["notion_url"] = first_page_total_success_url1 # URL del primer item creado en DB1 que tuvo éxito
             final_response["notion_url_db2"] = first_page_total_success_url2 # URL del primer item creado en DB2 que tuvo éxito

             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             status_code_return = 207 # Partial Content

        else: # items_processed_count == 0
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado con éxito. {items_failed_count}/{total_items_intended} item(s) fallaron. Ver logs del servidor para detalles."
             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             if total_items_intended > 0:
                 status_code_return = 500
             else:
                 status_code_return = 400
                 final_response["error"] = f"No hay items válidos para procesar en Folio '{folio_solicitud}'. Asegúrate de llenar la información del material correctamente."


        logger.info(f"{user_log_prefix}: Procesamiento de Materiales completado. Resultado general: {status_code_return}")
        return final_response, status_code_return


    except Exception as e:
        # Usa traceback.format_exc() para obtener la traza completa en el log
        error_message = f"Error inesperado de servidor al procesar la solicitud de Materiales: {str(e)}"
        logger.error(f"--- {user_log_prefix} ERROR INESPERADO en submit_request_for_material_logic --- Exception: {e}", exc_info=True)
        # Intenta obtener el folio si está disponible
        folio_para_respuesta = data.get('folio_solicitud', "No asignado") if 'data' in locals() and data else "No asignado"
        return {"error": error_message, "folio_solicitud": folio_para_respuesta}, 500


# *** DEFINICIÓN COMPLETA DE find_project_page_by_property_value (para buscar proyectos) ***
def find_project_page_by_property_value(
    notion_client: Client,
    database_id_proyectos: str, # ID de la BD de Proyectos
    property_name: str,        # Nombre de la propiedad para buscar (ej. "Número de Proyecto")
    property_value: Any        # Valor a buscar
) -> Optional[str]:
    """
    Busca una página en la base de datos de Proyectos por el valor de una propiedad específica.
    Devuelve el page_id si encuentra una página, None en caso contrario.
    """
    if not notion_client or not database_id_proyectos or not property_name or property_value is None or str(property_value).strip() == "":
        logger.warning(f"Datos insuficientes para buscar página de proyecto. DB ID Proyectos: '{database_id_proyectos}', Prop Nombre: '{property_name}', Prop Valor: '{property_value}'")
        return None

    try:
        # Obtenemos las propiedades de la BD de Proyectos para saber el tipo de propiedad de búsqueda.
        db_proyectos_properties = get_database_properties_util(notion_client, database_id_proyectos)

        if property_name not in db_proyectos_properties:
            logger.warning(f"Propiedad de búsqueda '{property_name}' no encontrada en la base de datos de Proyectos '{database_id_proyectos}'. No se puede buscar el proyecto.")
            return None

        prop_info = db_proyectos_properties[property_name]
        prop_type = prop_info.get("type")

        # Crear una condición de filtro usando el tipo y valor
        filter_condition = {}
        cleaned_value = str(property_value).strip()

        if prop_type == "select":
             filter_condition = { "property": property_name, "select": { "equals": cleaned_value } }
        elif prop_type == "number":
             try:
                 float_value = float(cleaned_value)
                 filter_condition = { "property": property_name, "number": { "equals": float_value } }
             except (ValueError, TypeError):
                  logger.warning(f"Valor '{cleaned_value}' no es un número válido para buscar en propiedad Number '{property_name}'.")
                  return None
        elif prop_type in ["rich_text", "title", "url", "email", "phone_number"]:
             # Usamos contains para texto, título, etc.
             filter_condition = { "property": property_name, prop_type if prop_type != 'text' else 'rich_text': { "contains": cleaned_value } }
        # Añadir otros tipos si es necesario para buscar por ellos


        if not filter_condition:
            logger.warning(f"No se pudo crear condición de filtro válida para buscar página de proyecto. Prop: '{property_name}', Tipo: '{prop_type}', Valor: '{property_value}'")
            return None


        logger.info(f"Realizando búsqueda de página de proyecto en DB '{database_id_proyectos}' con filtro: {json.dumps(filter_condition, ensure_ascii=False)}")

        # Usar get_pages_with_filter_util para buscar la(s) página(s). Limitamos a 2 para detectar posibles duplicados.
        found_pages = get_pages_with_filter_util(
            notion_client,
            database_id_proyectos,
            filters=[filter_condition],
            page_size=2
        )

        if found_pages:
            if len(found_pages) > 1:
                 logger.warning(f"Múltiples páginas encontradas en DB Proyectos para filtro '{property_name}'='{property_value}'. Usando la primera encontrada.")

            project_page_id = found_pages[0].get("id")
            if project_page_id:
                # logger.debug(f"Página de proyecto encontrada con ID={project_page_id}.")
                return project_page_id
            else:
                logger.warning(f"Página encontrada para filtro '{property_name}'='{property_value}', pero el objeto de página no tiene ID válido. Omitiendo.")
                return None
        else:
            logger.warning(f"No se encontró ninguna página en DB Proyectos con filtro '{property_name}'='{property_value}'.")
            return None

    except Exception as e:
        logger.error(f"Error inesperado al buscar página de proyecto para valor '{property_value}': {e}", exc_info=True)
        return None


# *** DEFINICIÓN COMPLETA DE adjust_dates_with_filters_util (para ajustes) ***
def adjust_dates_with_filters_util(
    notion_client: Client,
    database_id: str, # Este es el ID de la base de datos donde se ajustan fechas
    hours: int,
    start_date: datetime,
    filters: List[Dict[str, Any]] = None
) -> str:
    """
    Busca páginas en una base de datos usando filtros y ajusta sus fechas.
    Usada por adjust_dates_api (modulo Ajustes). No se usa en Solicitudes de Materiales.
    """
    if not notion_client or not database_id:
         return "Error interno: Cliente de Notion o Database ID faltante."

    pages = get_pages_with_filter_util(notion_client, database_id, filters)
    total_pages = len(pages)
    updated_pages = 0
    failed_updates = 0
    skipped_pages = 0

    filter_description = "ninguno"
    if filters and len(filters) > 0:
        try:
             filter_desc_parts = []
             for f in filters:
                  prop_name = f.get("property", "desconocido")
                  filter_value_desc = "valor"
                  for key, val in f.items():
                      if key not in ['property', 'and', 'or', 'not']:
                           if isinstance(val, dict) and len(val) == 1:
                                condition_key = list(val.keys())[0]
                                if condition_key in ['equals', 'contains', 'starts_with', 'ends_with', 'greater_than', 'less_than', 'is_empty']:
                                    filter_value_text = 'vacío' if condition_key == 'is_empty' else str(val[condition_key])[:50]
                                    filter_value_desc = f"{condition_key.replace('_', ' ')} '{filter_value_text}'"
                                else:
                                     filter_value_desc = f"condición: {str(val)[:50]}"
                           else:
                                filter_value_desc = str(val).replace('_', ' ')

                  filter_desc_parts.append(f"{prop_name} {filter_value_desc}")
             filter_description = ", ".join(filter_desc_parts)
        except Exception:
             filter_description = "detalles no disponibles (error al parsear filtros)"

    logger.info(f"Iniciando ajuste de fechas en {database_id}: {hours} horas a partir de {start_date.isoformat()}. Filtros: {filter_description}. Total de páginas encontradas para procesar: {total_pages}")


    if total_pages == 0:
        resumen = f"Operación completada: No se encontraron registros que coincidieran con los filtros. Filtros: {filter_description}."
        logger.info(f"Ajuste de fechas completado con 0 páginas encontradas.")
        return resumen

    for page in pages:
        properties = page.get("properties", {})
        page_id = page.get("id")

        if not page_id:
            logger.warning("Página sin ID encontrada, omitiendo.")
            skipped_pages += 1
            continue

        date_property_value = properties.get(DATE_PROPERTY_NAME, {}).get("date", {})

        if date_property_value and "start" in date_property_value:
            try:
                start_date_notion_str = date_property_value["start"]
                start_date_notion = datetime.fromisoformat(start_date_notion_str.replace('Z', '+00:00') if start_date_notion_str and start_date_notion_str.endswith('Z') else start_date_notion_str).replace(tzinfo=None)

                if start_date_notion >= start_date:
                    new_start = start_date_notion + timedelta(hours=hours)

                    new_end = None
                    if date_property_value.get("end"):
                         end_date_notion_str = date_property_value["end"]
                         end_date_notion = datetime.fromisoformat(end_date_notion_str.replace('Z', '+00:00') if end_date_notion_str and end_date_notion_str.endswith('Z') else end_date_notion_str).replace(tzinfo=None)
                         new_end = end_date_notion + timedelta(hours=hours)

                    properties_to_update = {
                         DATE_PROPERTY_NAME: {"date": {"start": new_start.isoformat(), "end": new_end.isoformat() if new_end else None}}
                    }

                    status_code, update_response = update_notion_page_properties(notion_client, page_id, properties_to_update)

                    if 200 <= status_code < 300:
                        updated_pages += 1
                    else:
                        failed_updates += 1
                        logger.error(f"Fallo al actualizar fecha en página {page_id}: Estado={status_code}, Respuesta={update_response.get('error', 'Desconocido')}. Notion Msg: {update_response.get('notion_message', 'N/A')}")
                else:
                    logger.info(f"Página {page_id} con fecha {start_date_notion.strftime('%Y-%m-%d')} anterior al filtro {start_date.strftime('%Y-%m-%d')}, omitiendo.")
                    skipped_pages += 1

            except (ValueError, TypeError) as e:
                logger.error(f"Error al procesar o parsear fecha de página {page_id}: {str(e)}", exc_info=True)
                failed_updates += 1
            except Exception as e:
                 logger.error(f"Error inesperado al procesar página {page_id}: {str(e)}", exc_info=True)
                 failed_updates += 1
        else:
             logger.info(f"Página {page_id} sin fecha válida en propiedad '{DATE_PROPERTY_NAME}', omitiendo.")
             skipped_pages += 1


    logger.info(f"Proceso de ajuste de fechas completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")

    resumen = (
        f"Resumen del Ajuste de Fechas:\n"
        f"Filtros aplicados: {filter_description}\n"
        f"Total de registros encontrados: {total_pages}\n"
        f"Registros actualizados con éxito: {updated_pages}\n"
        f"Registros omitidos: {skipped_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: {hours} horas a partir del {start_date.strftime('%Y-%m-%d')}"
    )

    if failed_updates > 0:
         resumen += f"\n¡ADVERTENCIA! Hubo {failed_updates} actualizaciones fallidas. Revisa los logs del servidor para más detalles."

    return resumen


def build_filter_from_properties_util(notion_client: Client, database_id: str, property_filters: Dict[str, Any]) -> List[Dict]:
    """
    Construye una lista de objetos filtro para consultas a la API de Notion
    basado en un diccionario de propiedades y sus valores.
    """
    if not property_filters:
        return []
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para construir filtros.")
        return []

    filters = []
    db_properties = get_database_properties_util(notion_client, database_id)

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos '{database_id}', omitiendo filtro para esta propiedad.")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")

        filter_condition = create_filter_condition_util(prop_name, prop_type, prop_value)

        if filter_condition:
            filters.append(filter_condition)
        else:
             logger.warning(f"No se pudo crear condición de filtro válida para propiedad '{prop_name}' con valor '{prop_value}' (tipo '{prop_type}').")

    # logger.debug(f"Filtros construidos para DB {database_id}: {filters}") # Demasiado verbose
    return filters

# *** FUNCIÓN adjust_dates_api (llamada desde ajustes.py) ***
def adjust_dates_api(
    notion_client: Client,
    database_id: str, # Este es el ID de la base de datos de Ajustes/Proyectos (donde se ajustan fechas)
    hours: int,
    start_date_str: str,
    property_filters: Dict[str, Any] = None
) -> Tuple[Dict, int]: # Retorna (respuesta_dict, status_code HTTP)
    """
    Endpoint lógica para ajustar fechas en registros de Notion basado en filtros.
    """
    if not notion_client or not database_id:
         error_msg = "Cliente de Notion no inicializado o Database ID faltante para Ajustes."
         logger.error(error_msg)
         return {
            "success": False,
            "error": error_msg,
            "status_code": 503
        }, 503 # Service Unavailable

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        filters = build_filter_from_properties_util(notion_client, database_id, property_filters) if property_filters else []

        result_message = adjust_dates_with_filters_util(notion_client, database_id, hours, start_date, filters)

        status_code_return = 200
        if "¡ADVERTENCIA!" in result_message or "fallidas" in result_message:
             status_code_return = 207 # Partial Content

        return {
            "success": True,
            "message": result_message,
            "status_code": status_code_return
        }, status_code_return


    except ValueError as e:
        error_msg = f"Formato de fecha inválido o error en conversión: {str(e)}. Asegúrate de usar formato AAAA-MM-DD."
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 400
        }, 400

    except Exception as e:
        error_msg = f"Error inesperado al ajustar fechas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 500
        }, 500

def list_available_properties(notion_client: Client, database_id: str) -> List[Dict[str, str]]:
    """Lista propiedades disponibles de una base de datos dada."""
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para listar propiedades.")
        return []
    try:
        properties = get_database_properties_util(notion_client, database_id)
        property_list = []
        for name, info in properties.items():
            prop_type = info.get("type", "unknown")
            prop_id = info.get("id", name)
            property_list.append({
                "name": name,
                "type": prop_type,
                "id": prop_id
            })
        # logger.debug(f"Listadas {len(property_list)} propiedades para DB {database_id}.") # Demasiado verbose
        return property_list
    except Exception as e:
        logger.error(f"Error al listar propiedades de la base de datos {database_id}: {e}", exc_info=True)
        return []


# --- Lógica para Solicitudes de Materiales (FINAL CON RELATION DE PROYECTO) ---

# Función principal llamada desde la ruta /solicitudes/submit_standard en solicitudes.py
# Recibe el cliente Notion, IDs de DBs de Materiales y de Proyectos, y el diccionario 'data'
# Devuelve (respuesta_dict, status_code HTTP)
def submit_request_for_material_logic(
        notion_client: Client,
        database_id_db1: str,
        database_id_db2: str,
        database_id_proyectos: str, # <<<< NUEVO ARGUMENTO: ID de la BD de Proyectos <<<<
        data: Dict,
        user_id: Optional[int] = None
    ) -> Tuple[Dict, int]:

    # El bloque try/except debe envolver la lógica principal
    try:
        user_log_prefix_initial = f"[User ID: {user_id or 'N/A'}] Folio: N/A"
        logger.info(f"{user_log_prefix_initial} Iniciando procesamiento de solicitud de material...")


        folio_solicitud = data.get("folio_solicitud")
        if not folio_solicitud:
             folio_solicitud = f"EMG-BE-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
             logger.warning(f"{user_log_prefix_initial} Folio de solicitud no recibido del frontend. Generando fallback: {folio_solicitud}")

        user_log_prefix = f"[User ID: {user_id or 'N/A'}] Folio: {folio_solicitud}" # Prefijo de log establecido/actualizado
        logger.info(f"{user_log_prefix} Prefijo de log establecido.")


        items_processed_count = 0
        items_failed_count = 0
        first_page_total_success_url1 = None # Guarda la URL de la PRIMERA página creada con ÉXITO en DB1
        first_page_total_success_url2 = None # Guarda la URL de la PRIMERA página creada con ÉXITO en DB2


        # *** VALIDACIÓN DE IDs DE BASE DE DATOS ***
        # Incluye la validación para database_id_proyectos aquí también
        if not notion_client or not database_id_db1 or not database_id_db2 or not database_id_proyectos: # <<<< Incluye database_id_proyectos
             error_msg = "La integración con Notion para Solicitudes o Proyectos no está configurada correctamente (IDs o cliente faltante)."
             logger.error(f"{user_log_prefix} {error_msg}")
             return {"error": error_msg, "folio_solicitud": folio_solicitud}, 503 # Service Unavailable


        if not data:
            logger.warning(f"{user_log_prefix} No se recibieron datos válidos en submit_request_for_material_logic.")
            return {"error": "No se recibieron datos válidos."}, 400

        selected_proveedor = data.get("proveedor")
        is_torni_mode = selected_proveedor == 'Torni'


        # --- PROPIEDAD DEL PROYECTO (BUSQUEDA Y RELATION) ---
        proyecto_valor_frontend = data.get("proyecto", "") # Valor ingresado en el formulario
        project_page_id = None # Variable para guardar el ID de la página de proyecto encontrada

        # Buscar la página del proyecto en la BD de Proyectos si se proporcionó un valor en el frontend
        # y si el ID de la BD de Proyectos está configurado.
        if proyecto_valor_frontend and database_id_proyectos:
             logger.info(f"{user_log_prefix}: Buscando ID de página para proyecto: '{proyecto_valor_frontend}' en BD Proyectos '{database_id_proyectos}'...")
             # Usar la función de búsqueda
             project_page_id = find_project_page_by_property_value(
                 notion_client,
                 database_id_proyectos,
                 NOTION_PROP_PROYECTO_BUSQUEDA_ID, # Nombre de la propiedad en la BD de Proyectos para buscar
                 proyecto_valor_frontend # El valor a buscar
             )
             if project_page_id:
                  logger.info(f"{user_log_prefix}: ID de página de proyecto encontrado: {project_page_id}")
             else:
                  # Si un proyecto *válido existente en Notion* es obligatorio, descomenta lo siguiente:
                  # error_msg = f"No se encontró ningún proyecto existente con el valor '{proyecto_valor_frontend}'. Verifica el código del proyecto."
                  # logger.warning(f"{user_log_prefix} {error_msg}")
                  # return {"error": error_msg, "folio_solicitud": folio_solicitud}, 400 # Bad Request
                  logger.warning(f"{user_log_prefix}: No se encontró página de proyecto para '{proyecto_valor_frontend}'. La propiedad Relation en Notion quedará vacía.")

        # --- Construir Propiedad RELATION 'Proyecto' ---
        # Esta propiedad se añade a common_properties para aplicarse a cada item
        # La propiedad en la BD de Materiales se llama NOTION_PROP_MATERIALES_PROYECTO_RELATION
        project_relation_property_payload = {"relation": []} # Relación vacía por defecto (formato API)
        if project_page_id:
            # Si se encontró un project_page_id, crea el payload de Relation con el ID encontrado
            project_relation_property_payload = {"relation": [{"id": project_page_id}]}

        # common_properties ahora es donde agrupamos las propiedades que son iguales para cada item/página
        # Inicializamos common_properties y añadimos el folio primero
        common_properties = {}
        if folio_solicitud:
             common_properties[NOTION_PROP_FOLIO] = {"rich_text": [{"type": "text", "text": {"content": folio_solicitud}}]}

        # Añadir la propiedad Relation del Proyecto a common_properties
        # Se añade usando la constante correcta para la propiedad RELATION en la BD de Materiales
        common_properties[NOTION_PROP_MATERIALES_PROYECTO_RELATION] = project_relation_property_payload


        # --- Propiedades Comunes restantes (aplican a cada página creada para un item) ---
        # Estas se extraen directamente del diccionario 'data' principal y se añaden a common_properties.

        # Solicitante, Proveedor, Departamento/Área (ASUMIMOS SELECT)
        solicitante_val = data.get("nombre_solicitante", "")
        # Solo añadir si el valor no está vacío.
        if solicitante_val: common_properties[NOTION_PROP_SOLICITANTE] = {"select": {"name": solicitante_val}}
        # else: if NOTION_PROP_SOLICITANTE: common_properties[NOTION_PROP_SOLICITANTE] = {"select": None} # Descomenta si la propiedad requiere ser enviada incluso si vacía/null

        proveedor_val = selected_proveedor or ""
        if proveedor_val: common_properties[NOTION_PROP_PROVEEDOR] = {"select": {"name": proveedor_val}}
        # else: if NOTION_PROP_PROVEEDOR: common_properties[NOTION_PROP_PROVEEDOR] = {"select": None}

        departamento_val = data.get("departamento_area", "")
        if departamento_val: common_properties[NOTION_PROP_DEPARTAMENTO] = {"select": {"name": departamento_val}}
        # else: if NOTION_PROP_DEPARTAMENTO: common_properties[NOTION_PROP_DEPARTAMENTO] = {"select": None}


        # Fecha de solicitud (Date)
        fecha_solicitud_str = data.get("fecha_solicitud")
        if fecha_solicitud_str:
             try:
                 datetime.fromisoformat(fecha_solicitud_str)
                 common_properties[NOTION_PROP_FECHA_SOLICITUD] = {"date": {"start": fecha_solicitud_str}}
             except ValueError:
                 logger.warning(f"{user_log_prefix} Fecha de solicitud en formato inválido '{fecha_solicitud_str}'. No se añadirá la propiedad de fecha a Notion o se enviará null.")
                 # if NOTION_PROP_FECHA_SOLICITUD: common_properties[NOTION_PROP_FECHA_SOLICITUD] = {"date": None} # Si Notion requiere la propiedad pero permite null
                 pass

        # Especificaciones adicionales (Opcional, Rich Text)
        especificaciones_val = data.get("especificaciones_adicionales", "")
        if especificaciones_val:
             common_properties[NOTION_PROP_ESPECIFICACIONES] = {"rich_text": [{"type": "text", "text": {"content": especificaciones_val}}]}
        # else: if NOTION_PROP_ESPECIFICACIONES: common_properties[NOTION_PROP_ESPECIFICACIONES] = {"rich_text": []} # Descomenta si requiere Rich Text vacío


        # --- Determinar la lista final de items a procesar ---
        items_to_process_list = []

        if is_torni_mode:
             torni_items_list_from_data = data.get('torni_items', [])
             if not isinstance(torni_items_list_from_data, list):
                  logger.error(f"{user_log_prefix}: Se esperaba una lista para 'torni_items', pero se recibió {type(torni_items_list_from_data)}. No se procesarán items Torni.")
                  return {"error": "Datos de productos Torni inválidos recibidos. Se esperaba una lista."}, 400

             valid_torni_items = []
             for idx, item in enumerate(torni_items_list_from_data):
                  quantity = item.get("quantity")
                  item_id = item.get("id")
                  item_desc = item.get("description")

                  is_quantity_valid = isinstance(quantity, (int, float)) and quantity >= 0
                  is_id_valid = item_id is not None and str(item_id).strip() != ""
                  is_desc_valid = item_desc is not None and str(item_desc).strip() != ""

                  if not is_quantity_valid or not is_id_valid or not is_desc_valid:
                       logger.warning(f"{user_log_prefix}: Item Torni incompleto o inválido en índice {idx}. Datos: {item}. Requisitos: quantity(num), id(str/num), description(str). Omitiendo.")
                       continue

                  valid_torni_items.append(item)

             items_to_process_list = valid_torni_items

        else: # Proveedor estándar
             # En modo estándar, el diccionario 'data' contiene los campos del único item.
             # Verificamos si data contiene al menos un campo indicativo de un item estándar
             # para evitar procesar un diccionario 'data' completamente vacío.
             if any(data.get(key) is not None and str(data.get(key)).strip() != "" for key in ['nombre_material', 'cantidad_solicitada', 'unidad_medida', 'largo', 'ancho', 'alto', 'diametro', 'tipo_material']):
                items_to_process_list = [data]
             else:
                 logger.warning(f"{user_log_prefix}: Diccionario 'data' estándar vacío de campos de item principal. No se procesará.")


        if not items_to_process_list:
             logger.warning(f"{user_log_prefix}: No hay items válidos para procesar después de determinar la lista.")
             return {"error": "No hay items válidos para procesar. Asegúrate de llenar la información del material."}, 400


        logger.info(f"{user_log_prefix}: Items a procesar ({'Torni' if is_torni_mode else 'Estándar'}): {len(items_to_process_list)}")


        # --- Iterar sobre la lista FINAL de items a procesar y crear páginas en Notion ---
        for index, item_data in enumerate(items_to_process_list):
            item_index_str = f"Item {index + 1}"
            logger.info(f"{user_log_prefix}: --- Procesando {item_index_str} ---")

            # Copiar propiedades comunes (incluyendo la Relation del Proyecto) e inicializar con ellas.
            item_properties = common_properties.copy();

            # --- Construir Propiedades ESPECÍFICAS para este item ---
            # Extraer los valores de item_data. Usar .get() con valor por defecto para seguridad.

            quantity = item_data.get("cantidad_solicitada")
            tipo_material = item_data.get("tipo_material", "")
            nombre_material = item_data.get("nombre_material", "")
            unidad_medida = item_data.get("unidad_medida", "")
            largo = item_data.get("largo")
            ancho = item_data.get("ancho")
            alto = item_data.get("alto")
            diametro = item_data.get("diametro")


            # Cantidad (Number)
            cantidad_num_val = None
            if quantity is not None and str(quantity).strip() != "":
                 try:
                     cantidad_num_val = float(str(quantity).strip())
                 except (ValueError, TypeError):
                      logger.warning(f"{user_log_prefix}: {item_index_str} - Cantidad '{quantity}' no es numérica válida. Se enviará null a Notion.")
                      cantidad_num_val = None
            if cantidad_num_val is not None:
                 item_properties[NOTION_PROP_CANTIDAD] = {"number": cantidad_num_val}


            # Tipo de material, Nombre de material, Unidad de medida (ASUMIDO SELECT)
            if tipo_material: item_properties[NOTION_PROP_TIPO_MATERIAL] = {"select": {"name": tipo_material}}
            if nombre_material: item_properties[NOTION_PROP_NOMBRE_MATERIAL] = {"select": {"name": nombre_material}}
            if unidad_medida: item_properties[NOTION_PROP_UNIDAD_MEDIDA] = {"select": {"name": unidad_medida}}


            # Dimensiones (ASUMIDO RICH TEXT)
            if largo is not None and str(largo).strip() != "":
                 item_properties[NOTION_PROP_LARGO] = {"rich_text": [{"type": "text", "text": {"content": str(largo).strip()}}]}

            if ancho is not None and str(ancho).strip() != "":
                 item_properties[NOTION_PROP_ANCHO] = {"rich_text": [{"type": "text", "text": {"content": str(ancho).strip()}}]}

            if alto is not None and str(alto).strip() != "":
                 item_properties[NOTION_PROP_ALTO] = {"rich_text": [{"type": "text", "text": {"content": str(alto).strip()}}]}

            if diametro is not None and str(diametro).strip() != "":
                 item_properties[NOTION_PROP_DIAMETRO] = {"rich_text": [{"type": "text", "text": {"content": str(diametro).strip()}}]}


            # Si es modo Torni, añadir las propiedades específicas
            if is_torni_mode:
                 item_id_torni = item_data.get("id", "")
                 item_desc_torni = item_data.get("description", "")
                 if item_id_torni: item_properties[NOTION_PROP_TORNI_ID] = {"rich_text": [{"type": "text", "text": {"content": str(item_id_torni).strip()}}]}
                 if item_desc_torni: item_properties[NOTION_PROP_TORNI_DESCRIPTION] = {"rich_text": [{"type": "text", "text": {"content": str(item_desc_torni).strip()}}]}


            # --- DEBUG: Log de propiedades listas para enviar para este item ---
            logger.debug(f"{user_log_prefix}: {item_index_str} - Propiedades para enviar a Notion: {json.dumps(item_properties, ensure_ascii=False, indent=2)}")


            # --- Crear página en DB 1 ---
            page1_created = False; page1_url_current = None; error1_info = {}
            try:
                logger.info(f"{user_log_prefix}: {item_index_str} - Intentando crear página en DB 1 Materiales ({database_id_db1})...")
                response1 = notion_client.pages.create(parent={"database_id": database_id_db1}, properties=item_properties)
                page1_url_current = response1.get("url")
                if first_page_total_success_url1 is None and page1_url_current: # Guarda la URL del primer item creado con ÉXITO en DB1
                     first_page_total_success_url1 = page1_url_current

                logger.info(f"{user_log_prefix}: {item_index_str} - Página creada en DB 1: {page1_url_current}")
                page1_created = True
            except APIResponseError as e1:
                 api_error_msg = e1.message if hasattr(e1, 'message') else str(e1)
                 notion_response_body = getattr(e1, 'response', None)
                 notion_error_details = None
                 if notion_response_body:
                      try: notion_error_details = notion_response_body.json()
                      except Exception: pass

                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR API en DB 1 Materiales: Código={e1.code if hasattr(e1, 'code') else 'N/A'} Mensaje={api_error_msg}", exc_info=True)
                 if notion_error_details: logger.error(f"Detalles adicionales del error de Notion (DB 1): {json.dumps(notion_error_details, ensure_ascii=False)}")
                 error1_info = {"code": e1.code if hasattr(e1, 'code') else 'N/A', "message": api_error_msg, "notion_error_details": notion_error_details}
            except Exception as e1:
                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR inesperado en DB 1 Materiales: {e1}", exc_info=True)
                 error1_info = {"message": str(e1)}


            # --- Crear página en DB 2 ---
            page2_created = False; page2_url_current = None; error2_info = {}
            try:
                logger.info(f"{user_log_prefix}: {item_index_str} - Intentando crear página en DB 2 Materiales ({database_id_db2})...")
                response2 = notion_client.pages.create(parent={"database_id": database_id_db2}, properties=item_properties)
                page2_url_current = response2.get("url")
                if first_page_total_success_url2 is None and page2_url_current: # Guarda la URL del primer item creado con ÉXITO en DB2
                     first_page_total_success_url2 = page2_url_current


                logger.info(f"{user_log_prefix}: {item_index_str} - Página creada en DB 2: {page2_url_current}")
                page2_created = True
            except APIResponseError as e2:
                 api_error_msg = e2.message if hasattr(e2, 'message') else str(e2)
                 notion_response_body = getattr(e2, 'response', None)
                 notion_error_details = None
                 if notion_response_body:
                      try: notion_error_details = notion_response_body.json()
                      except Exception: pass

                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR API en DB 2 Materiales: Código={e2.code if hasattr(e2, 'code') else 'N/A'} Mensaje={api_error_msg}", exc_info=True)
                 if notion_error_details: logger.error(f"Detalles adicionales del error de Notion (DB 2): {json.dumps(notion_error_details, ensure_ascii=False)}")
                 error2_info = {"code": e2.code if hasattr(e2, 'code') else 'N/A', "message": api_error_msg, "notion_error_details": notion_error_details}

            except Exception as e2:
                 logger.error(f"{user_log_prefix}: {item_index_str} - ERROR inesperado en DB 2 Materiales: {e2}", exc_info=True)
                 error2_info = {"message": str(e2)}


            # Contar items procesados/fallidos
            if page1_created and page2_created:
                items_processed_count += 1
                logger.info(f"{user_log_prefix}: {item_index_str} procesado con éxito en ambas DBs.")
                # Si este es el primer item que se procesa COMPLETAMENTE con éxito en ambas DBs
                # No necesitamos re-asignar here, already done when setting the first URL found.
                pass
            else:
                 items_failed_count += 1
                 error_details = {
                     "item_index": index + 1,
                     "item_data_sent_partial": {k: item_data.get(k) for k in ['cantidad_solicitada', 'nombre_material', 'unidad_medida', 'largo', 'ancho', 'alto', 'diametro', 'id', 'description', 'tipo_material', 'nombre_solicitante', 'proveedor', 'departamento_area', 'fecha_solicitud', 'proyecto', 'especificaciones_adicionales']} if not is_torni_mode else item_data,
                     "db1_success": page1_created, "db1_error": error1_info,
                     "db2_success": page2_created, "db2_error": error2_info
                 }
                 #logger.debug(f"{user_log_prefix}: {item_index_str} - Propiedades que causaron el fallo: {json.dumps(item_properties, ensure_ascii=False, indent=2)}")
                 logger.error(f"{user_log_prefix}: {item_index_str} falló al procesar. Detalles resumen: {json.dumps(error_details, ensure_ascii=False)}")


        # --- Fin del bucle for ---

        # --- Construir Respuesta Final ---
        final_response = {"folio_solicitud": folio_solicitud}
        status_code_return = 200 # Default éxito
        total_items_intended = len(items_to_process_list)

        # Si hubo al menos un item procesado con éxito en ambas DBs, usamos sus URLs para la respuesta.
        if items_processed_count > 0 and items_failed_count == 0:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count}/{total_items_intended} item(s)) registrada con éxito en ambas DBs."
             final_response["notion_url"] = first_page_total_success_url1
             final_response["notion_url_db2"] = first_page_total_success_url2
             status_code_return = 200

        elif items_processed_count > 0 and items_failed_count > 0:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count}/{total_items_intended} item(s) OK, {items_failed_count} fallaron. Ver logs del servidor para detalles."
             final_response["notion_url"] = first_page_total_success_url1
             final_response["notion_url_db2"] = first_page_total_success_url2

             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             status_code_return = 207 # Partial Content

        else: # items_processed_count == 0
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado con éxito. {items_failed_count}/{total_items_intended} item(s) fallaron. Ver logs del servidor para detalles."
             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             if total_items_intended > 0:
                 status_code_return = 500
             else:
                 status_code_return = 400
                 final_response["error"] = f"No hay items válidos para procesar en Folio '{folio_solicitud}'. Asegúrate de llenar la información del material correctamente."


        logger.info(f"{user_log_prefix}: Procesamiento de Materiales completado. Resultado general: {status_code_return}")
        return final_response, status_code_return


    except Exception as e:
        # Usa traceback.format_exc() para obtener la traza completa en el log
        error_message = f"Error inesperado de servidor al procesar la solicitud de Materiales: {str(e)}"
        logger.error(f"--- {user_log_prefix} ERROR INESPERADO en submit_request_for_material_logic --- Exception: {e}", exc_info=True)
        folio_para_respuesta = data.get('folio_solicitud', "No asignado") if 'data' in locals() and data else "No asignado"
        return {"error": error_message, "folio_solicitud": folio_para_respuesta}, 500


# *** DEFINICIÓN COMPLETA DE adjust_dates_with_filters_util ***
# ... (Código de adjust_dates_with_filters_util debe estar aquí) ...

# *** DEFINICIÓN COMPLETA DE adjust_dates_api ***
# ... (Código de adjust_dates_api debe estar aquí) ...

# *** DEFINICIÓN COMPLETA DE list_available_properties ***
# ... (Código de list_available_properties debe estar aquí) ...