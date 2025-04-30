# autointelli/notion_utils.py
# Este archivo contiene funciones auxiliares de Notion para Ajustes y Solicitudes.
# NO debe cargar .env ni inicializar el cliente Notion.
# NO debe tener un bloque __main__.

import logging
import requests # Si las funciones de ajuste usan requests directamente
from notion_client import Client # Si las funciones de ajuste usan el cliente Notion
from notion_client.errors import APIResponseError # Manejo de errores específicos
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback # Para logs detallados

logger = logging.getLogger("notion_utils")

# --- Funciones para Ajuste de Horarios (adaptadas de tu ajustes.py) ---

# Asumimos que DATE_PROPERTY_NAME y REQUEST_TIMEOUT son constantes o se pasan
# Si DATE_PROPERTY_NAME fuera configurable por env var, DEBERÍA leerse en app.py
# y pasarse a las funciones que lo necesitan.
# Para simplificar, la definimos aquí como constante, PERO si la quieres en env var, cámbiala.
DATE_PROPERTY_NAME = "Date"
REQUEST_TIMEOUT = 30
NOTION_VERSION = "2022-06-28" # También podría ser una constante aquí o pasada
API_BASE_URL = "https://api.notion.com/v1" # Constante aquí o pasada


# Adaptar las funciones para que acepten notion_client y database_id como argumentos
def validate_api_connection_util(notion_client: Client, database_id: str) -> bool:
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para validación.")
        return False
    try:
        # Puedes usar el cliente Notion:
        notion_client.databases.retrieve(database_id)
        logger.info(f"Conexión a la base de datos {database_id} validada correctamente")
        return True
    except Exception as e: # Capturar excepciones del cliente Notion
        logger.error(f"Error al validar la conexión a la base de datos {database_id}: {str(e)}", exc_info=True)
        return False

def get_database_properties_util(notion_client: Client, database_id: str) -> Dict[str, Dict]:
    if not notion_client or not database_id:
        logger.error("Cliente de Notion o Database ID faltante para obtener propiedades.")
        return {}
    try:
        # Usa el cliente Notion:
        database_info = notion_client.databases.retrieve(database_id)
        properties = database_info.get("properties", {})
        logger.info(f"Propiedades obtenidas de la base de datos {database_id}: {', '.join(properties.keys())}")
        return properties
    except Exception as e:
        logger.error(f"Error al obtener propiedades de la base de datos {database_id}: {str(e)}", exc_info=True)
        return {}

# Esta función auxiliar puede seguir siendo genérica
def create_filter_condition_util(property_name: str, property_type: str, value: Any) -> Dict:
     # ... código copiado de ajustes.py para create_filter_condition ...
     if property_type == "select":
         return { "property": property_name, "select": { "equals": value } }
     elif property_type == "multi_select":
         return { "property": property_name, "multi_select": { "contains": value } }
     elif property_type in ["title", "rich_text"]:
         return { "property": property_name, "rich_text": { "contains": value } }
     elif property_type == "number":
         try:
             # Asegurarse de que el valor sea numérico si el tipo es 'number'
             float_value = float(value)
             return { "property": property_name, "number": { "equals": float_value } }
         except (ValueError, TypeError):
             logger.warning(f"Valor '{value}' no es un número válido para propiedad '{property_name}'.")
             return {} # Retorna filtro vacío si el valor no es convertible a número
     elif property_type == "checkbox":
          # Convertir valor a booleano si es necesario, o asumir True/False
          bool_value = str(value).lower() in ['true', 'yes', 'on', '1']
          return { "property": property_name, "checkbox": { "equals": bool_value } }
     elif property_type == "people":
          # Asumir que 'value' es el ID del usuario o un nombre a buscar
          logger.warning("Filtrado por 'people' no completamente implementado en create_filter_condition_util.")
          # return { "property": property_name, "people": { "contains": value } } # Not standard Notion API filter structure by value
          # Filtering people by ID is more complex query filter, skipping for simple equality/contains text for now
          return {}
     elif property_type == "formula":
          # Las fórmulas no se pueden filtrar directamente, pero puedes filtrar por el TIPO de resultado
          # Asumiremos que intentan filtrar por el texto del resultado (si es rich_text)
          return { "property": property_name, "rich_text": { "contains": value } }

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
        while has_more:
            # >>> PREPARAR LOS ARGUMENTOS PARA LA LLAMADA A query - ESTA ES LA TERCERA VERSIÓN <<<
            query_args = {
                "database_id": database_id,
                "page_size": page_size,
            }

            # --- CORRECCIÓN: Solo añadir 'filter' si hay filtros ---
            # Construye el dict de filtro, o deja filter_arg como None
            filter_arg = None
            if filters and len(filters) > 0:
                if len(filters) == 1:
                    filter_arg = filters[0] # Pasa el dict de un solo filtro
                else:
                    filter_arg = { "and": filters } # Pasa el dict con la lógica 'and'

            # *** Solo añade la clave 'filter' a query_args si filter_arg NO es None ***
            if filter_arg is not None:
                 query_args["filter"] = filter_arg

            # --- FIN CORRECCIÓN ---


            # Agregar start_cursor si existe
            if start_cursor:
                query_args["start_cursor"] = start_cursor

            # Usa el cliente Notion para consultar
            # Pasar el diccionario de argumentos usando **
            # Si filter_arg es None, la clave "filter" no estará en query_args, y no se pasará.
            response = notion_client.databases.query(**query_args) # <<< Pasar los argumentos usando **

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
            DATE_PROPERTY_NAME: { # Usa la constante DATE_PROPERTY_NAME
                "date": date_value
            }
        }
    }

    try:
        # Usa el cliente Notion para actualizar
        response = notion_client.pages.update(page_id=page_id, properties=payload["properties"])
        logger.info(f"Página {page_id} actualizada correctamente")
        # El cliente Notion no devuelve status_code directamente, asumimos 200 si no lanza excepción
        return 200, response
    except APIResponseError as e:
        logger.error(f"Error API al actualizar página {page_id}: {e.code} - {e.message}", exc_info=True)
        return e.status, {"error": e.message, "code": e.code} # APIResponseError tiene .status
    except Exception as e:
        logger.error(f"Error inesperado al actualizar página {page_id}: {str(e)}", exc_info=True)
        return 500, {"error": str(e)}


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
        # Simplificado para descripción
        try:
             filter_desc_parts = []
             for f in filters:
                  prop_name = f.get("property", "desconocido")
                  filter_type = list(f.keys() - {'property'})[0] if len(list(f.keys() - {'property'})) > 0 else 'condición desconocida'
                  filter_value = f[filter_type].get('equals') or f[filter_type].get('contains') or 'valor desconocido'
                  filter_desc_parts.append(f"{prop_name} {filter_type} '{filter_value}'")
             filter_description = ", ".join(filter_desc_parts)
        except Exception:
             filter_description = "detalles no disponibles"


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
            # Parsea la fecha de Notion. Si no tiene zona horaria, .replace(tzinfo=None)
            # Si tiene zona horaria y quieres operar en UTC, conviértela a UTC
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


            # Compara solo las fechas si la fecha de inicio de filtro es solo YYYY-MM-DD
            # O compara datetime si tu start_date tiene hora y Notion también
            # Aquí comparamos datetime completos
            if start_date_notion >= start_date:
                new_start = start_date_notion + timedelta(hours=hours)
                new_end = end_date_notion + timedelta(hours=hours) if end_date_notion else None

                status_code, update_response = update_page_util(notion_client, page_id, new_start, new_end)

                if 200 <= status_code < 300:
                    updated_pages += 1
                else:
                    failed_updates += 1
                    logger.error(f"Fallo al actualizar página {page_id}: Estado={status_code}, Respuesta={update_response}")
            else:
                logger.info(f"Página {page_id} con fecha {start_date_notion.isoformat()} anterior a filtro {start_date.isoformat()}, omitiendo")
                skipped_pages += 1

        except (ValueError, TypeError) as e:
            logger.error(f"Error al procesar o parsear fecha de página {page_id}: {str(e)}", exc_info=True)
            failed_updates += 1
        except Exception as e: # Captura cualquier otro error durante el procesamiento de una página
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

    # Si hubo fallos, podrías añadirlo al resumen
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
    db_properties = get_database_properties_util(notion_client, database_id) # Usa la función auxiliar

    for prop_name, prop_value in property_filters.items():
        if prop_name not in db_properties:
            logger.warning(f"Propiedad '{prop_name}' no encontrada en la base de datos '{database_id}', omitiendo filtro")
            continue

        prop_info = db_properties[prop_name]
        prop_type = prop_info.get("type")

        # create_filter_condition_util debe existir aquí
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
        # Asumimos que start_date_str viene en formato 'YYYY-MM-DD' del form
        # Si Notion usa UTC, es más seguro comparar con un datetime consciente de TZ o UTC.
        # Parseamos como local naive y luego podríamos convertir si fuera necesario.
        # Para comparaciones >=, un simple parseo de fecha suele ser suficiente.
        # Usar datetime.strptime para manejar solo YYYY-MM-DD
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        # Si quieres que sea consciente de zona horaria, tendrías que añadirla aquí
        # Ej: from pytz import timezone; start_date = timezone('UTC').localize(start_date)

        filters = build_filter_from_properties_util(notion_client, database_id, property_filters) if property_filters else None
        result_message = adjust_dates_with_filters_util(notion_client, database_id, hours, start_date, filters)

        # La función interna devuelve un string de resumen, no un dict success/error
        # Asumimos éxito si llegó hasta aquí sin lanzar excepción fatal
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


# --- Lógica para Solicitudes de Materiales (adaptada de tu solicitudes.py) ---

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
    folio_solicitud = None # Inicializar
    items_processed_count = 0
    items_failed_count = 0
    first_page1_url = None
    first_page2_url = None
    error_occurred = False # Bandera para fallos parciales

    if not notion_client or not database_id_db1 or not database_id_db2:
         error_msg = "La integración con Notion para Solicitudes no está configurada correctamente (IDs o cliente)."
         logger.error(error_msg)
         return {"error": error_msg}, 503 # Service Unavailable

    if not data:
        logger.warning("No se recibieron datos en submit_request_for_material_logic.")
        return {"error": "No se recibieron datos."}, 400

    try:
        selected_proveedor = data.get("proveedor")
        torni_items = data.get('torni_items')

        # Generar Folio único si no viene
        folio_solicitud = data.get("folio_solicitud", f"EMG-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}") # <<< CAMBIO CORRECTO
        logger.info(f"Procesando Folio de Materiales: {folio_solicitud}")

        # Propiedades Comunes
        common_properties = {}
        if data.get("nombre_solicitante"): common_properties["Nombre del solicitante"] = {"select": {"name": data["nombre_solicitante"]}}
        if selected_proveedor: common_properties["Proveedor"] = {"select": {"name": selected_proveedor}}
        if data.get("departamento_area"): common_properties["Departamento/Área"] = {"select": {"name": data["departamento_area"]}}
        if data.get("fecha_solicitud"):
             try:
                 datetime.fromisoformat(data["fecha_solicitud"].replace('Z', '+00:00'))
                 common_properties["Fecha de solicitud"] = {"date": {"start": data["fecha_solicitud"]}}
             except ValueError:
                 logger.warning(f"Formato de fecha inválido para fecha_solicitud: {data['fecha_solicitud']}")
                 pass
        if folio_solicitud: common_properties["Folio de solicitud"] = {"rich_text": [{"type": "text", "text": {"content": folio_solicitud}}]}
        if data.get("Proyecto"): common_properties["Proyecto"] = {"rich_text": [{"type": "text", "text": {"content": data["Proyecto"]}}]}
        if data.get("especificaciones_adicionales"): common_properties["Especificaciones adicionales"] = {"rich_text": [{"type": "text", "text": {"content": data["especificaciones_adicionales"]}}]}

        # Lógica Condicional para items
        items_to_process = []
        is_torni_mode = selected_proveedor == 'Torni' and isinstance(torni_items, list)
        if is_torni_mode:
             items_to_process = torni_items
        elif data:
             items_to_process = [data]

        if not items_to_process:
             logger.warning(f"No hay items para procesar para el folio {folio_solicitud}.")
             return {"error": "No hay items para procesar."}, 400

        logger.info(f"Items a procesar para folio {folio_solicitud}: {len(items_to_process)}")

        for index, item_data in enumerate(items_to_process):
            item_index_str = f"Item {index + 1}" if is_torni_mode else "Item Único"
            logger.info(f"--- Procesando {item_index_str} para folio {folio_solicitud} ---")
            item_properties = common_properties.copy()

            # Construir Propiedades COMPLETAS para este item
            if is_torni_mode:
                 quantity = item_data.get("quantity")
                 if quantity is not None:
                    try: item_properties["Cantidad solicitada"] = {"number": int(quantity)}
                    except (ValueError, TypeError):
                         logger.warning(f"Cantidad inválida para {item_index_str}: {quantity}. Estableciendo en 0.")
                         item_properties["Cantidad solicitada"] = {"number": 0}
                 else: item_properties["Cantidad solicitada"] = {"number": 0} # Default a 0 si no hay cantidad

                 item_id = str(item_data.get("id", "")).strip();
                 item_desc = str(item_data.get("description", "")).strip()
                 if item_id: item_properties["ID de producto"] = {"rich_text": [{"type": "text", "text": {"content": item_id}}]}
                 if item_desc: item_properties["Descripción"] = {"rich_text": [{"type": "text", "text": {"content": item_desc}}]}
            else: # Proveedor estándar
                 quantity = item_data.get("cantidad_solicitada")
                 if quantity is not None:
                    try: item_properties["Cantidad solicitada"] = {"number": int(quantity)}
                    except (ValueError, TypeError):
                         logger.warning(f"Cantidad inválida para {item_index_str}: {quantity}. Estableciendo en 0.")
                         item_properties["Cantidad solicitada"] = {"number": 0}
                 else: item_properties["Cantidad solicitada"] = {"number": 0} # Default a 0 si no hay cantidad

                 if item_data.get("tipo_material"): item_properties["Tipo de material"] = {"select": {"name": item_data["tipo_material"]}}
                 if item_data.get("nombre_material"): item_properties["Nombre del material"] = {"select": {"name": item_data["nombre_material"]}}
                 if item_data.get("unidad_medida"): item_properties["Unidad de medida"] = {"select": {"name": item_data["unidad_medida"]}}
                 if item_data.get("largo") is not None: item_properties["Largo (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["largo"])}}]}
                 if item_data.get("ancho") is not None: item_properties["Ancho (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["ancho"])}}]}
                 if item_data.get("alto") is not None: item_properties["Alto (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["alto"])}}]}
                 if item_data.get("diametro") is not None: item_properties["Diametro (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["diametro"])}}]}


            # Crear página en DB 1
            page1_created = False; error1_details = None; page1_url_current = None
            try:
                response1 = notion_client.pages.create(parent={"database_id": database_id_db1}, properties=item_properties)
                page1_url_current = response1.get("url")
                if index == 0: first_page1_url = page1_url_current
                logger.info(f"Página creada en DB 1 para {item_index_str}: {page1_url_current}")
                page1_created = True
            except APIResponseError as e1: error1_details = f"Notion API Error ({e1.code}): {e1.message}"; logger.error(f"ERROR API en DB 1 Materiales ({item_index_str}): {error1_details}", exc_info=True)
            except Exception as e1: error1_details = str(e1); logger.error(f"ERROR en DB 1 Materiales ({item_index_str}): {error1_details}", exc_info=True)

            # Crear página en DB 2
            page2_created = False; error2_details = None; page2_url_current = None
            try:
                response2 = notion_client.pages.create(parent={"database_id": database_id_db2}, properties=item_properties)
                page2_url_current = response2.get("url")
                if index == 0: first_page2_url = page2_url_current
                logger.info(f"Página creada en DB 2 para {item_index_str}: {page2_url_current}")
                page2_created = True
            except APIResponseError as e2: error2_details = f"Notion API Error ({e2.code}): {e2.message}"; logger.error(f"ERROR API en DB 2 Materiales ({item_index_str}): {error2_details}", exc_info=True)
            except Exception as e2: error2_details = str(e2); logger.error(f"ERROR en DB 2 Materiales ({item_index_str}): {error2_details}", exc_info=True)

            # Registrar si hubo algún fallo
            if not page1_created or not page2_created:
                 error_occurred = True
                 items_failed_count += 1
                 logger.error(f"Fallo al procesar {item_index_str}. DB1 OK: {page1_created}, DB2 OK: {page2_created}. Errores: DB1='{error1_details}', DB2='{error2_details}'")
            else:
                items_processed_count += 1
                logger.info(f"{item_index_str} procesado con éxito en ambas DBs.")

        # --- Fin del bucle ---

        # --- Construir Respuesta Final ---
        final_response = {"folio_solicitud": folio_solicitud}
        status_code = 200

        if items_processed_count > 0 and items_failed_count == 0:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count} item(s)) registrada con éxito en ambas DBs."
             final_response["notion_url"] = first_page1_url
             final_response["notion_url_db2"] = first_page2_url
             status_code = 200
        elif items_processed_count > 0 and items_failed_count > 0:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count} item(s) OK, {items_failed_count} fallaron. Ver logs."
             final_response["notion_url"] = first_page1_url
             final_response["notion_url_db2"] = first_page2_url
             status_code = 207 # Partial Content
        else: # items_processed_count == 0
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado. {items_failed_count} item(s) fallaron. Ver logs."
             status_code = 500 # Internal Server Error

        logger.info(f"Procesamiento de Materiales completado para Folio {folio_solicitud}. Resultado: {status_code}")
        return final_response, status_code

    except Exception as e:
        error_message = str(e)
        logger.error(f"--- ERROR INESPERADO en submit_request_for_material_logic (Folio: {folio_solicitud or 'NO ASIGNADO'}) ---", exc_info=True)
        return {"error": "Error inesperado al procesar la solicitud de Materiales.", "details": error_message, "folio_solicitud": folio_solicitud}, 500