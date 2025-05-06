import logging
import requests # Aunque get_pages_with_filter_util no usa requests directamente, notion_client lo hace. Mantenerlo por si acaso.
from datetime import datetime, timedelta # Aunque estas utils no los usan directamente, podrían ser útiles aquí.
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback # Aunque estas utils no usan traceback, se mantuvo en el original. Puede que no sea estrictamente necesario aquí, pero no hace daño.

logger = logging.getLogger(__name__)

# --- Funciones Auxiliares Generales ---

def get_database_properties_util(notion_client: Client, database_id: str) -> Dict[str, Dict]:
    """Obtiene el diccionario de propiedades de una base de datos de Notion."""
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para obtener propiedades.")
        return {}
    try:
        database_info = notion_client.databases.retrieve(database_id)
        properties = database_info.get("properties", {})
        # logger.debug(f"Propiedades obtenidas de la base de datos {database_id}: {', '.join(properties.keys())}") # Demasiado verbose, descomentar solo para depuración intensa.
        return properties
    except Exception as e:
        logger.error(f"Error al obtener propiedades de la base de datos {database_id}: {str(e)}", exc_info=True)
        return {}

def create_filter_condition_util(property_name: str, property_type: str, value: Any) -> Dict:
     """Construye una condición de filtro para consultas a la API de Notion."""
     if value is None or (isinstance(value, str) and str(value).strip() == ""):
          # Un valor vacío no genera una condición de filtro "positive match" útil aquí.
          # Para buscar campos vacíos {"is_empty": true} se necesitaría lógica adicional.
          logger.warning(f"Valor nulo o vacío para crear filtro de propiedad '{property_name}'. Omitiendo.")
          return {}

     cleaned_value = str(value).strip()

     # Mapeo de tipos de Notion a condiciones de filtro comunes
     if property_type in ["text", "rich_text", "title", "url", "email", "phone_number"]:
          # Filtro 'contains' es flexible para texto
          return { "property": property_name, property_type if property_type != 'text' else 'rich_text' : { "contains": cleaned_value } } # API usa 'rich_text' para title/text
     elif property_type == "number":
         try:
             float_value = float(cleaned_value)
             return { "property": property_name, "number": { "equals": float_value } } # Coincidencia exacta para números
         except (ValueError, TypeError):
             logger.warning(f"Valor '{value}' no es un número válido para filtro 'equals' en propiedad Number '{property_name}'.")
             return {}
     elif property_type == "select":
         return { "property": property_name, "select": { "equals": cleaned_value } } # Coincidencia exacta para Select
     elif property_type == "checkbox":
         bool_value = cleaned_value.lower() in ['true', 'yes', 'on', '1'] # Intenta convertir a booleano
         return { "property": property_name, "checkbox": { "equals": bool_value } } # Coincidencia exacta para Checkbox
     elif property_type == "multi_select":
          return { "property": property_name, "multi_select": { "contains": cleaned_value } } # Contiene una opción específica en multi-select

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
                # Usar filtro 'and' para combinar múltiples condiciones si hay más de una
                filter_arg = { "and": filters }

        if filter_arg is not None:
             query_args["filter"] = filter_arg
             # logger.debug(f"Filtros aplicados a consulta Notion para {database_id}: {json.dumps(filter_arg, ensure_ascii=False)}") # Demasiado verbose


        while has_more:
            if start_cursor:
                query_args["start_cursor"] = start_cursor

            response = notion_client.databases.query(**query_args)

            # El cliente Python de Notion ya devuelve el diccionario, no necesitas response.json()
            data = response

            results = data.get("results", [])
            all_pages.extend(results)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            # logger.debug(f"Obtenidas {len(results)} páginas con filtros de {database_id}. Total acumulado: {len(all_pages)}") # Demasiado verbose

    except APIResponseError as e:
        logger.error(f"Error API al consultar base de datos {database_id}: Código={e.code if hasattr(e, 'code') else 'N/A'} Mensaje={e.message if hasattr(e, 'message') else str(e)}", exc_info=True)
        notion_response_body = getattr(e, 'response', None)
        # Intenta obtener el cuerpo JSON del error si está disponible en el objeto de respuesta
        if notion_response_body is not None and hasattr(notion_response_body, 'json'):
             try: logger.error(f"Detalles adicionales del error de Notion (Consulta DB {database_id}): {json.dumps(notion_response_body.json(), ensure_ascii=False)}")
             except Exception: pass # No fallar si no se puede parsear el JSON del error

    except Exception as e:
        logger.error(f"Error inesperado al obtener páginas de Notion con filtros de {database_id}: {str(e)}", exc_info=True)

    logger.info(f"Consulta a DB {database_id} completada. Total de páginas encontradas: {len(all_pages)}")
    return all_pages

def update_notion_page_properties(notion_client: Client, page_id: str, properties_to_update: Dict) -> Tuple[int, Dict]:
    if not notion_client or not page_id or not properties_to_update:
         logger.error("Cliente de Notion, Page ID o propiedades a actualizar faltantes.")
         return 400, {"error": "Request inválido. Faltan parámetros necesarios."}

    try:
        # logger.debug(f"Intentando actualizar propiedades para página {page_id}: {properties_to_update}") # Muy verbose, descomentar con cuidado.
        response = notion_client.pages.update(page_id=page_id, properties=properties_to_update)
        logger.info(f"Página {page_id} actualizada correctamente.")
        # En caso de éxito, el cliente Notion no devuelve un status_code directo en el objeto response,
        # pero la actualización fue exitosa, que corresponde a un 2xx. Asumimos 200.
        return 200, response
    except APIResponseError as e:
        # La excepción APIResponseError contiene el código de estado HTTP en e.status
        logger.error(f"Error API al actualizar página {page_id}: Código={e.code if hasattr(e, 'code') else 'N/A'} Mensaje={e.message if hasattr(e, 'message') else str(e)} Estado HTTP={e.status if hasattr(e, 'status') else 'N/A'}", exc_info=True)
        notion_response_body = getattr(e, 'response', None)
        notion_error_details = None
        if notion_response_body is not None and hasattr(notion_response_body, 'json'):
             try: notion_error_details = notion_response_body.json()
             except Exception: pass

        # Retorna el status code de la API de Notion y un diccionario de error
        return e.status if hasattr(e, 'status') and e.status is not None else 500, { # Fallback a 500 si status no está disponible
            "error": f"Notion API Error: {e.message if hasattr(e, 'message') else str(e)}",
            "code": e.code if hasattr(e, 'code') else 'N/A',
            "notion_error_details": notion_error_details
        }
    except Exception as e:
        # Captura otros errores inesperados durante el proceso de actualización
        logger.error(f"Error inesperado al actualizar página {page_id}: {str(e)}", exc_info=True)
        return 500, {"error": f"Error interno del servidor: {str(e)}"}
    
def list_available_properties(notion_client: Client, database_id: str) -> List[Dict[str, str]]:
    """
    Lista las propiedades disponibles (nombre, tipo, id) de una base de datos dada.
    Útil para que el frontend conozca los campos disponibles para filtros o visualización.
    """
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para listar propiedades.")
        return []
    try:
        properties = get_database_properties_util(notion_client, database_id)
        property_list = []
        for name, info in properties.items():
            prop_type = info.get("type", "unknown")
            prop_id = info.get("id", name) # Usar el ID interno si está disponible, sino el nombre
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
    

def build_filter_from_properties_util(notion_client: Client, database_id: str, property_filters: Dict[str, Any]) -> List[Dict]:

    if not property_filters:
        logger.info("No se proporcionaron filtros de propiedades, build_filter_from_properties_util retorna lista vacía.")
        return []
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para construir filtros.")
        return []

    filters = []
    db_properties = get_database_properties_util(notion_client, database_id)

    if not db_properties:
         logger.error(f"No se pudieron obtener las propiedades de la base de datos '{database_id}'. No se construirán filtros.")
         return []

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' proporcionada para filtro no encontrada en la base de datos '{database_id}'. Omitiendo filtro para esta propiedad.")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type") # Obtiene el tipo de propiedad desde Notion

        # Usa la función auxiliar para crear la condición de filtro específica para el tipo
        filter_condition = create_filter_condition_util(prop_name, prop_type, prop_value)

        if filter_condition:
            filters.append(filter_condition)
        else:
             # La función create_filter_condition_util ya loguea warnings por valores inválidos o tipos no soportados
             pass
    # logger.debug(f"Filtros construidos final: {json.dumps(filters, ensure_ascii=False)}") # Muy verbose
    return filters