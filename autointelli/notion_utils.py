# autointelli/notion_utils.py
# Este archivo contiene funciones auxiliares de Notion para Ajustes y Solicitudes.
# NO debe cargar .env ni inicializar el cliente Notion.
# NO debe tener un bloque __main__.

import logging
import requests
# Importar datetime y timedelta específicamente
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback

logger = logging.getLogger("notion_utils")

# --- Constantes (o podrían pasarse como argumentos si fueran configurables) ---
DATE_PROPERTY_NAME = "Date" # Nombre de la propiedad de Fecha para Ajustes
REQUEST_TIMEOUT = 30
NOTION_VERSION = "2022-06-28"
API_BASE_URL = "https://api.notion.com/v1"


# --- Funciones Auxiliares para Ajuste de Horarios (adaptadas) ---

def validate_api_connection_util(notion_client: Client, database_id: str) -> bool:
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para validación.")
        return False
    try:
        notion_client.databases.retrieve(database_id)
        logger.info(f"Conexión a la base de datos {database_id} validada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al validar la conexión a la base de datos {database_id}: {str(e)}", exc_info=True)
        return False

def get_database_properties_util(notion_client: Client, database_id: str) -> Dict[str, Dict]:
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para obtener propiedades.")
        return {}
    try:
        database_info = notion_client.databases.retrieve(database_id)
        properties = database_info.get("properties", {})
        logger.info(f"Propiedades obtenidas de la base de datos {database_id}: {', '.join(properties.keys())}")
        return properties
    except Exception as e:
        logger.error(f"Error al obtener propiedades de la base de datos {database_id}: {str(e)}", exc_info=True)
        return {}

def create_filter_condition_util(property_name: str, property_type: str, value: Any) -> Dict:
     # Esta función es genérica para construir filtros
     if property_type == "select":
         return { "property": property_name, "select": { "equals": value } }
     elif property_type == "multi_select":
         return { "property": property_name, "multi_select": { "contains": value } }
     elif property_type in ["title", "rich_text"]:
         return { "property": property_name, "rich_text": { "contains": value } }
     elif property_type == "number":
         try:
             float_value = float(value)
             return { "property": property_name, "number": { "equals": float_value } }
         except (ValueError, TypeError):
             logger.warning(f"Valor '{value}' no es un número válido para propiedad '{property_name}'.")
             return {}
     elif property_type == "checkbox":
          bool_value = str(value).lower() in ['true', 'yes', 'on', '1']
          return { "property": property_name, "checkbox": { "equals": bool_value } }
     # Añadir otros tipos de propiedades según necesidad
     elif property_type == "url":
          return { "property": property_name, "url": { "contains": value } }
     # El filtro por 'people' requiere el ID del usuario, no el nombre
     # elif property_type == "people":
     #      return { "property": property_name, "people": { "contains": value } } # Esta no es la forma correcta para todos los filtros de people
     elif property_type == "email":
          return { "property": property_name, "email": { "contains": value } }
     elif property_type == "phone_number":
          return { "property": property_name, "phone_number": { "contains": value } }
     elif property_type == "date":
          # Filtrar por fechas requiere un objeto date filter, ej: {"equals": "YYYY-MM-DD"}
          logger.warning("Filtrado por 'date' no completamente implementado en create_filter_condition_util.")
          return {} # No implementado completamente


     else:
         logger.warning(f"Tipo de propiedad no soportado para filtrado en create_filter_condition_util: {property_type}")
         return {}


def get_pages_with_filter_util(notion_client: Client, database_id: str, filters: List[Dict] = None, page_size: int = 100) -> List[Dict]:
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
                filter_arg = { "and": filters }

        if filter_arg is not None:
             query_args["filter"] = filter_arg

        while has_more:
            if start_cursor:
                query_args["start_cursor"] = start_cursor

            response = notion_client.databases.query(**query_args)

            data = response

            results = data.get("results", [])
            all_pages.extend(results)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

            logger.info(f"Obtenidas {len(results)} páginas con filtros de {database_id}. Total acumulado: {len(all_pages)}")

    except Exception as e:
        logger.error(f"Error al obtener páginas de Notion con filtros de {database_id}: {str(e)}", exc_info=True)

    return all_pages

def update_page_util(notion_client: Client, page_id: str, new_start: datetime, new_end: Optional[datetime]) -> Tuple[int, Dict]:
    if not notion_client or not page_id:
         logger.error("Cliente de Notion o Page ID faltante para actualizar página.")
         return 500, {"error": "Cliente de Notion o Page ID faltante"}

    date_value = { "start": new_start.isoformat() }
    if new_end:
        date_value["end"] = new_end.isoformat()

    payload = {
        "properties": {
            DATE_PROPERTY_NAME: {
                "date": date_value
            }
        }
    }

    try:
        response = notion_client.pages.update(page_id=page_id, properties=payload["properties"])
        logger.info(f"Página {page_id} actualizada correctamente")
        return 200, response
    except APIResponseError as e:
        logger.error(f"Error API al actualizar página {page_id}: {e.code} - {e.message}", exc_info=True)
        return e.status, {"error": e.message, "code": e.code, "notion_message": e.message} # Incluir mensaje de Notion API
    except Exception as e:
        logger.error(f"Error inesperado al actualizar página {page_id}: {str(e)}", exc_info=True)
        return 500, {"error": str(e)}
    
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
        "properties": properties_to_update # El payload directo es el diccionario de propiedades
    }

    try:
        logger.info(f"Attempting to update properties for page {page_id}: {properties_to_update}")
        # Usa el cliente Notion para actualizar
        response = notion_client.pages.update(page_id=page_id, properties=payload["properties"])
        logger.info(f"Página {page_id} actualizada correctamente")
        # El cliente Notion no devuelve status_code directamente, asumimos 200 si no lanza excepción
        return 200, response
    except APIResponseError as e:
        logger.error(f"Error API al actualizar página {page_id}: {e.code} - {e.message}", exc_info=True)
        # Incluir el código y mensaje de la API en la respuesta de error
        return e.status, {"error": f"Notion API Error: {e.message}", "code": e.code, "notion_message": e.message}
    except Exception as e:
        logger.error(f"Error inesperado al actualizar página {page_id}: {str(e)}", exc_info=True)
        return 500, {"error": f"Error interno: {str(e)}"} # Error genérico del servidor


def adjust_dates_with_filters_util(
    notion_client: Client,
    database_id: str,
    hours: int,
    start_date: datetime, # Espera un objeto datetime
    filters: List[Dict[str, Any]] = None
) -> str:
    if not notion_client or not database_id:
         return "Error: La integración con Notion no está configurada correctamente."

    if not validate_api_connection_util(notion_client, database_id):
        return f"Error: No se pudo conectar a la base de datos de Notion ({database_id}). Verifica la conexión y credenciales."

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
                  # Intenta obtener el tipo de filtro, manejando posibles estructuras diferentes
                  filter_type_key = next((k for k in f.keys() if k != 'property'), 'condición desconocida')
                  filter_type = filter_type_key.replace('_', ' ') # Convertir guiones bajos a espacios para legibilidad
                  filter_value = 'valor desconocido'
                  # Intenta obtener el valor del filtro, manejando posibles estructuras diferentes
                  if isinstance(f.get(filter_type_key), dict):
                      filter_value = f[filter_type_key].get('equals') or f[filter_type_key].get('contains') or str(f[filter_type_key])[:50]
                  else:
                      filter_value = str(f.get(filter_type_key, 'valor desconocido'))[:50]

                  filter_desc_parts.append(f"{prop_name} {filter_type} '{filter_value}'")
             filter_description = ", ".join(filter_desc_parts)
        except Exception:
             filter_description = "detalles no disponibles (error al parsear filtros)"


    logger.info(f"Iniciando ajuste de fechas en {database_id}: {hours} horas a partir de {start_date.isoformat()}. Filtros: {filter_description}. Total de páginas a procesar: {total_pages}")

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
            start_date_notion_str = date_info["start"]
            if start_date_notion_str.endswith('Z'):
                 start_date_notion = datetime.fromisoformat(start_date_notion_str.replace('Z', '+00:00'))
            else:
                 start_date_notion = datetime.fromisoformat(start_date_notion_str).replace(tzinfo=None)


            end_date_notion = None
            if date_info.get("end"):
                 end_date_notion_str = date_info["end"]
                 if end_date_notion_str.endswith('Z'):
                      end_date_notion = datetime.fromisoformat(end_date_notion_str.replace('Z', '+00:00'))
                 else:
                      end_date_notion = datetime.fromisoformat(end_date_notion_str).replace(tzinfo=None)


            if start_date_notion >= start_date:
                new_start = start_date_notion + timedelta(hours=hours)
                new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None

                status_code, update_response = update_page_util(notion_client, page_id, new_start, new_end)

                if 200 <= status_code < 300:
                    updated_pages += 1
                else:
                    failed_updates += 1
                    logger.error(f"Fallo al actualizar página {page_id}: Estado={status_code}, Respuesta={update_response.get('error', 'Desconocido')}. Notion Msg: {update_response.get('notion_message', 'N/A')}")
            else:
                logger.info(f"Página {page_id} con fecha {start_date_notion.isoformat()} anterior a filtro {start_date.isoformat()}, omitiendo")
                skipped_pages += 1

        except (ValueError, TypeError) as e:
            logger.error(f"Error al procesar o parsear fecha de página {page_id}: {str(e)}", exc_info=True)
            failed_updates += 1
        except Exception as e:
             logger.error(f"Error inesperado al procesar página {page_id}: {str(e)}", exc_info=True)
             failed_updates += 1


    logger.info(f"Proceso completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")

    resumen = (
        f"Operación completada: Se actualizaron {updated_pages} registros.\n"
        f"Filtros aplicados: {filter_description}\n"
        f"Total de registros filtrados: {total_pages}\n"
        f"Registros actualizados: {updated_pages}\n"
        f"Registros omitidos: {skipped_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: {hours} horas a partir del {start_date.strftime('%Y-%m-%d')}"
    )

    if failed_updates > 0:
         resumen += f"\n¡ADVERTENCIA! Hubo {failed_updates} actualizaciones fallidas. Revisa los logs para más detalles."

    return resumen

def build_filter_from_properties_util(notion_client: Client, database_id: str, property_filters: Dict[str, Any]) -> List[Dict]:
    if not property_filters:
        return []
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para construir filtros.")
        return []

    filters = []
    db_properties = get_database_properties_util(notion_client, database_id)

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos '{database_id}', omitiendo filtro")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")

        filter_condition = create_filter_condition_util(prop_name, prop_type, prop_value)

        if filter_condition:
            filters.append(filter_condition)
        else:
             logger.warning(f"No se pudo crear condición de filtro para '{prop_name}' con valor '{prop_value}' (tipo: {prop_type}).")

    return filters

# Función principal llamada desde la ruta /ajustes/run
def adjust_dates_api(
    notion_client: Client,
    database_id: str,
    hours: int,
    start_date_str: str,
    property_filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    if not notion_client or not database_id:
         return {
            "success": False,
            "error": "Cliente de Notion no inicializado para Ajustes."
        }
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        filters = build_filter_from_properties_util(notion_client, database_id, property_filters) if property_filters else None
        result_message = adjust_dates_with_filters_util(notion_client, database_id, hours, start_date, filters)

        return {
            "success": True,
            "message": result_message,
            "status_code": 200
        }

    except ValueError as e:
        error_msg = f"Formato de fecha inválido o error en conversión: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 400
        }
    except Exception as e:
        error_msg = f"Error al ajustar fechas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "status_code": 500
        }

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
            property_list.append({
                "name": name,
                "type": prop_type
            })
        return property_list
    except Exception as e:
        logger.error(f"Error al listar propiedades de la base de datos {database_id}: {e}", exc_info=True)
        return []


# --- Lógica para Solicitudes de Materiales ---

# Función principal llamada desde la ruta /solicitudes/submit
# Devuelve (respuesta_dict, status_code)
def submit_request_for_material_logic(
        notion_client: Client,
        database_id_db1: str,
        database_id_db2: str,
        data: Dict,
        user_id: Optional[int] = None
    ) -> Tuple[Dict, int]:

    logger.info(f"[User ID: {user_id}] Iniciando procesamiento de solicitud de material...")
    """
    Procesa la solicitud de material y crea páginas en Notion.
    Acepta el cliente Notion, IDs de DB y los datos del formulario.
    """
    folio_solicitud = None
    items_processed_count = 0
    items_failed_count = 0
    first_page1_url = None
    first_page2_url = None

    if not notion_client or not database_id_db1 or not database_id_db2:
         error_msg = "La integración con Notion para Solicitudes no está configurada correctamente (IDs o cliente)."
         logger.error(f"[User ID: {user_id}] {error_msg}")
         return {"error": error_msg}, 503 # Service Unavailable

    if not data:
        logger.warning(f"[User ID: {user_id}] No se recibieron datos en submit_request_for_material_logic.")
        return {"error": "No se recibieron datos."}, 400

    try:
        selected_proveedor = data.get("proveedor")
        # No recolectamos torni_items aquí, los procesamos directamente si es modo Torni


        # Generar Folio único si no viene
        # Usar datetime.datetime.now() si solo importaste datetime, o datetime.now() si importaste from datetime import datetime
        # Aquí se importó 'from datetime import datetime, timedelta', entonces se usa datetime.now()
        folio_solicitud = data.get("folio_solicitud", f"EMG-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")
        logger.info(f"[User ID: {user_id}] Procesando Folio de Materiales: {folio_solicitud}")
        # logger.debug(f"[User ID: {user_id}] Datos recibidos completos: {json.dumps(data, ensure_ascii=False, indent=2)}") # Descomentar para depurar datos crudos


        # --- Propiedades Comunes (siempre se aplican a cada página creada) ---
        common_properties = {}
        # Asegúrate de que las keys del dict coincidan exactamente con los nombres de las propiedades en Notion
        # Usar .get() con valor por defecto None para evitar KeyError si la clave no existe
        if data.get("nombre_solicitante"): common_properties["Nombre del solicitante"] = {"select": {"name": data["nombre_solicitante"]}}
        if selected_proveedor: common_properties["Proveedor"] = {"select": {"name": selected_proveedor}}
        if data.get("departamento_area"): common_properties["Departamento/Área"] = {"select": {"name": data["departamento_area"]}}
        if data.get("fecha_solicitud"):
             try:
                 # Intenta parsear y formatear la fecha, Notion espera ISO 8601 (ej: "2023-10-27" o "2023-10-27T10:00:00Z")
                 # Si el frontend envía 'YYYY-MM-DD', esto debería funcionar.
                 # Si necesitas hora o zona horaria, ajusta el parseo y formato
                 common_properties["Fecha de solicitud"] = {"date": {"start": data["fecha_solicitud"]}}
             except Exception as e: # Capturar cualquier error de formato de fecha
                 logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: Error al procesar fecha de solicitud '{data['fecha_solicitud']}': {e}")
                 # No añadir la propiedad si el formato es inválido
                 pass
        if folio_solicitud: common_properties["Folio de solicitud"] = {"rich_text": [{"type": "text", "text": {"content": folio_solicitud}}]}
        if data.get("Proyecto"): common_properties["Proyecto"] = {"rich_text": [{"type": "text", "text": {"content": data["Proyecto"]}}]}
        if data.get("especificaciones_adicionales"): common_properties["Especificaciones adicionales"] = {"rich_text": [{"type": "text", "text": {"content": data["especificaciones_adicionales"]}}]}


        # --- Determinar la lista final de items a procesar ---
        items_to_process_list = []
        is_torni_mode = selected_proveedor == 'Torni'

        if is_torni_mode:
             # En modo Torni, esperamos una lista en data['torni_items']
             torni_items_list_from_data = data.get('torni_items', []) # Default a lista vacía si no existe

             if not isinstance(torni_items_list_from_data, list):
                  logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: Se esperaba una lista para 'torni_items', pero se recibió {type(torni_items_list_from_data)}.")
                  # Podríamos devolver un error 400 aquí si data.get('torni_items') no es una lista
                  # return {"error": "Datos de productos Torni inválidos recibidos."}, 400
                  # Por ahora, continuamos con una lista vacía, lo cual resultará en 0 items procesados

             items_to_process_list = torni_items_list_from_data # Asignar la lista obtenida

        else: # Proveedor estándar
             # En modo estándar, procesamos el objeto 'data' completo como un solo item
             # La estructura esperada es que 'data' contenga directamente los campos estándar
             items_to_process_list = [data] # Crear una lista con un solo elemento (el diccionario data)


        if not items_to_process_list:
             logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: No hay items para procesar después de determinar la lista.")
             # Devolver 400 si la lista de items a procesar está vacía
             return {"error": "No hay items válidos para procesar. Asegúrate de llenar al menos un item."}, 400


        logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: Items a procesar ({'Torni' if is_torni_mode else 'Estándar'}): {len(items_to_process_list)}")

        items_processed_count = 0
        items_failed_count = 0
        # No necesitas la bandera error_occurred

        # --- Iterar sobre la lista FINAL de items a procesar ---
        for index, item_data in enumerate(items_to_process_list):
            item_index_str = f"Item {index + 1}"
            logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: --- Procesando {item_index_str} ---")
            item_properties = common_properties.copy(); # Copiar propiedades comunes para cada item

            # --- Construir Propiedades ESPECÍFICAS para este item ---
            if is_torni_mode:
                 # En modo Torni, item_data DEBE ser un objeto {quantity, id, description} de la lista torni_items
                 quantity = item_data.get("quantity")
                 item_id = item_data.get("id")
                 item_desc = item_data.get("description")

                 # Validación básica de los campos Torni dentro del backend (aunque el frontend debería validar)
                 if quantity is None or item_id is None or item_desc is None or str(item_id).strip() == "" or str(item_desc).strip() == "":
                      logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Item Torni incompleto o inválido recibido: {item_data}. Saltando.")
                      items_failed_count += 1 # Contar como fallo si está incompleto/inválido
                      continue # Saltar este item

                 try: item_properties["Cantidad solicitada"] = {"number": int(quantity)}
                 except (ValueError, TypeError):
                      logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Cantidad Torni inválida: {quantity}. Asignando 0.")
                      item_properties["Cantidad solicitada"] = {"number": 0} # Asignar 0 si inválido

                 # Asegúrate de que los nombres de propiedad "ID de producto" y "Descripción" coinciden con tu DB de Notion
                 item_properties["ID de producto"] = {"rich_text": [{"type": "text", "text": {"content": str(item_id).strip()}}]}
                 item_properties["Descripción"] = {"rich_text": [{"type": "text", "text": {"content": str(item_desc).strip()}}]}

                 # Si hay otras propiedades específicas de Torni en tu DB y en el JSON, agrégalas aquí
                 # Ej: if item_data.get("campo_extra"): item_properties["Nombre Campo Extra Notion"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["campo_extra"]).strip()}}]}


            else: # Proveedor estándar (item_data es el diccionario 'data' completo)
                 # Obtener campos estándar del diccionario data
                 quantity = item_data.get("cantidad_solicitada")
                 tipo_material = item_data.get("tipo_material")
                 nombre_material = item_data.get("nombre_material")
                 unidad_medida = item_data.get("unidad_medida")
                 largo = item_data.get("largo")
                 ancho = item_data.get("ancho")
                 alto = item_data.get("alto")
                 diametro = item_data.get("diametro")

                 # Validación básica de los campos estándar (aunque el frontend debería validar)
                 # Si la cantidad es NONE o inválida, o si los campos obligatorios no están presentes/válidos
                 # Para simplificar, solo validaremos cantidad aquí
                 if quantity is None or (isinstance(quantity, (int, float)) and quantity <= 0) or (isinstance(quantity, str) and not quantity.strip()) or (isinstance(quantity, str) and quantity.strip() and (float(quantity.strip()) <= 0 or isinstance(float(quantity.strip()), str))): # Validación más robusta para cantidad
                     logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Cantidad estándar faltante o inválida: {quantity}. Saltando.")
                     items_failed_count += 1
                     continue # Saltar este item

                 try: item_properties["Cantidad solicitada"] = {"number": int(quantity)}
                 except (ValueError, TypeError):
                      logger.warning(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Cantidad estándar no numérica: {quantity}. Asignando 0.")
                      item_properties["Cantidad solicitada"] = {"number": 0}


                 # Asegúrate de que los nombres de propiedad coinciden con tu DB de Notion
                 if tipo_material: item_properties["Tipo de material"] = {"select": {"name": tipo_material}}
                 if nombre_material: item_properties["Nombre del material"] = {"select": {"name": nombre_material}}
                 if unidad_medida: item_properties["Unidad de medida"] = {"select": {"name": unidad_medida}}
                 # Convertir dimensiones a string solo si existen y no son "N/A" (insensible a mayúsculas)
                 if largo is not None and str(largo).strip().upper() != 'N/A': item_properties["Largo (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(largo).strip()}}]}
                 if ancho is not None and str(ancho).strip().upper() != 'N/A': item_properties["Ancho (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(ancho).strip()}}]}
                 if alto is not None and str(alto).strip().upper() != 'N/A': item_properties["Alto (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(alto).strip()}}]}
                 if diametro is not None and str(diametro).strip().upper() != 'N/A': item_properties["Diametro (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(diametro).strip()}}]}

                 # Si hay otras propiedades estándar en tu DB y en el JSON, agrégalas aquí
                 # Ej: if item_data.get("otro_campo"): item_properties["Otro Campo Notion"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["otro_campo"]).strip()}}]}


            # --- LOG DE PROPIEDADES ANTES DE CREAR ---
            # logger.debug(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Propiedades para enviar a Notion: {item_properties}")


            # --- Crear página en DB 1 ---
            page1_created = False; page1_url_current = None; error1_info = {}
            try:
                logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Intentando crear página en DB 1 Materiales ({database_id_db1})...")
                response1 = notion_client.pages.create(parent={"database_id": database_id_db1}, properties=item_properties)
                page1_url_current = response1.get("url")
                if index == 0: first_page1_url = page1_url_current # Guardar URL del primer item exitoso
                logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Página creada en DB 1: {page1_url_current}")
                page1_created = True
            except APIResponseError as e1:
                 logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - ERROR API en DB 1 Materiales: {e1.code} - {e1.message}", exc_info=True)
                 error1_info = {"code": e1.code, "message": e1.message}
            except Exception as e1:
                 logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - ERROR inesperado en DB 1 Materiales: {e1}", exc_info=True)
                 error1_info = {"message": str(e1)}


            # --- Crear página en DB 2 ---
            page2_created = False; page2_url_current = None; error2_info = {}
            try:
                logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Intentando crear página en DB 2 Materiales ({database_id_db2})...")
                response2 = notion_client.pages.create(parent={"database_id": database_id_db2}, properties=item_properties)
                # Solo guarda la URL del primer item exitoso si DB1 también tuvo éxito
                if index == 0 and page1_created: first_page2_url = page2_url_current
                # Si DB1 falló para el primer item, pero DB2 tuvo éxito, podrías querer guardar esta URL en su lugar?
                # Depende de lo que quieras mostrar como "primera URL" en caso de fallo parcial.
                # Mantengamos la URL del primer item que tuvo éxito en AMBAS DBs.
                if index == 0 and page1_created and page2_created: first_page2_url = response2.get("url")

                logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - Página creada en DB 2: {response2.get('url')}")
                page2_created = True
            except APIResponseError as e2:
                 logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - ERROR API en DB 2 Materiales: {e2.code} - {e2.message}", exc_info=True)
                 error2_info = {"code": e2.code, "message": e2.message}
            except Exception as e2:
                 logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} - ERROR inesperado en DB 2 Materiales: {e2}", exc_info=True)
                 error2_info = {"message": str(e2)}


            # Contar items procesados/fallidos SI AMBAS DBs tuvieron éxito para este item
            if page1_created and page2_created:
                items_processed_count += 1
                logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} procesado con éxito en ambas DBs.")
            else:
                 items_failed_count += 1
                 # Loggear los errores si ocurrieron para este item
                 error_details = {
                     "item_index": index + 1,
                     "item_data_sent": item_data, # Loggear los datos que se intentaron enviar
                     "db1_success": page1_created,
                     "db1_error": error1_info,
                     "db2_success": page2_created,
                     "db2_error": error2_info
                 }
                 logger.error(f"[User ID: {user_id}] Folio {folio_solicitud}: {item_index_str} falló al procesar. Detalles: {json.dumps(error_details, ensure_ascii=False)}")


        # --- Fin del bucle for ---


        # --- Construir Respuesta Final ---
        final_response = {"folio_solicitud": folio_solicitud}
        # El status code general refleja el resultado global de la solicitud
        status_code = 200 # Default éxito


        if items_processed_count > 0 and items_failed_count == 0:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count} item(s)) registrada con éxito en ambas DBs."
             final_response["notion_url"] = first_page1_url
             final_response["notion_url_db2"] = first_page2_url
             status_code = 200

        elif items_processed_count > 0 and items_failed_count > 0:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count} item(s) OK, {items_failed_count} fallaron. Ver logs del servidor para detalles de los fallos."
             final_response["notion_url"] = first_page1_url # URL del primer item (si existió y tuvo éxito total)
             final_response["notion_url_db2"] = first_page2_url # URL del primer item (si existió y tuvo éxito total)
             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             status_code = 207 # Partial Content

        else: # items_processed_count == 0 (Todos fallaron o no había items válidos)
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado con éxito. {items_failed_count} item(s) fallaron. Ver logs del servidor para detalles."
             final_response["failed_count"] = items_failed_count
             final_response["processed_count"] = items_processed_count
             status_code = 500 # Internal Server Error si falla todo, o 400 si no había items válidos para empezar


        logger.info(f"[User ID: {user_id}] Folio {folio_solicitud}: Procesamiento de Materiales completado. Resultado general: {status_code}")
        # Devuelve la respuesta final y el código de estado HTTP
        return final_response, status_code

    except Exception as e:
        error_message = f"Error inesperado al procesar la solicitud de Materiales: {str(e)}"
        logger.error(f"--- [User ID: {user_id}] ERROR INESPERADO en submit_request_for_material_logic (Folio: {folio_solicitud or 'NO ASIGNADO'}) ---", exc_info=True)
        # Si ocurre una excepción *antes* de poder contar items, devuelve un error 500
        return {"error": error_message, "folio_solicitud": folio_solicitud}, 500

# ... (resto de funciones auxiliares) ...