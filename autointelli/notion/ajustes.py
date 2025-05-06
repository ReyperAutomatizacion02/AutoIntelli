import logging
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import APIResponseError
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback # Para el error general

# Importar funciones auxiliares y constantes
from .utils import update_notion_page_properties, get_pages_with_filter_util, get_database_properties_util, create_filter_condition_util # build_filter_from_properties_util las usa
from .constants import DATE_PROPERTY_NAME # Necesita la constante para el nombre de la propiedad de Fecha

from .utils import (
    update_notion_page_properties, # Si se usa aquí
    get_pages_with_filter_util,   # Si se usa aquí
    get_database_properties_util, # Si se usa aquí
    create_filter_condition_util, # Si se usa aquí
    build_filter_from_properties_util # <<< Importación CORRECTA para ajustes.py
)

from .constants import DATE_PROPERTY_NAME

logger = logging.getLogger(__name__)

# --- Funciones Auxiliares para Ajuste de Horarios ---

def update_page_util(notion_client: Client, page_id: str, new_start: datetime, new_end: Optional[datetime]) -> Tuple[int, Dict]:
    """
    Actualiza la propiedad de Fecha (Date) de una página específica utilizando
    update_notion_page_properties.
    """
    # Construye el payload para la propiedad Date. NOTA: Requiere que DATE_PROPERTY_NAME esté definido.
    properties_to_update = {
        DATE_PROPERTY_NAME: {"date": {"start": new_start.isoformat(), "end": new_end.isoformat() if new_end else None}}
    }
    logger.info(f"Intentando actualizar fecha en página {page_id} a Start: {new_start.isoformat()} End: {new_end.isoformat() if new_end else 'None'}")
    # Reutiliza la función general de actualización
    return update_notion_page_properties(notion_client, page_id, properties_to_update)


def adjust_dates_with_filters_util(
    notion_client: Client,
    database_id: str, # Este es el ID de la base de datos donde se ajustan fechas (Ajustes/Proyectos)
    hours: int,
    start_date: datetime, # Fecha límite (solo se ajustan fechas iguales o posteriores)
    filters: List[Dict[str, Any]] = None # Lista de objetos filtro API Notion
) -> str:
    
    if not notion_client or not database_id:
         # Este caso ya debería estar cubierto por el llamador (adjust_dates_api), pero es un buen fallback.
         return "Error interno: Cliente de Notion no inicializado o Database ID faltante para ajuste."

    all_filters = []
    if filters:
         all_filters.extend(filters)

    pages = get_pages_with_filter_util(notion_client, database_id, all_filters)
    total_pages = len(pages)
    updated_pages = 0
    failed_updates = 0
    skipped_pages = 0 # Páginas encontradas por filtro, pero omitidas por lógica interna (ej. fecha anterior)

    # Intenta construir una descripción legible de los filtros para el log y el resumen.
    filter_description = "ninguno"
    if all_filters and len(all_filters) > 0:
        try:
             filter_desc_parts = []
             for f in all_filters:
                  prop_name = f.get("property", "desconocido")
                  # Intenta encontrar la condición específica dentro del filtro (equals, contains, on_or_after, etc.)
                  filter_condition_desc = "condición compleja"
                  for key, val in f.items():
                      if key not in ['property', 'and', 'or', 'not']: # Ignorar operadores lógicos y la key 'property'
                           if isinstance(val, dict) and len(val) == 1:
                                condition_type = list(val.keys())[0] # Ej: 'equals', 'contains', 'on_or_after'
                                condition_value = val[condition_type] # El valor de la condición
                                filter_value_text = 'vacío' if condition_type == 'is_empty' else str(condition_value)[:50] # Limitar tamaño del valor
                                filter_condition_desc = f"{condition_type.replace('_', ' ')} '{filter_value_text}'"
                                break # Encontrada la condición, salir del bucle interno
                           elif isinstance(val, (str, int, float, bool)):
                                # Si el valor está directamente asociado a la propiedad (menos común para filtrado complejo)
                                filter_condition_desc = f"directo '{str(val)[:50]}'"
                                break
                  filter_desc_parts.append(f"{prop_name} {filter_condition_desc}")
             filter_description = ", ".join(filter_desc_parts)
        except Exception:
             # Si falla el parsing, usar una descripción genérica
             filter_description = f"detalles no disponibles (error al parsear: {len(all_filters)} filtros)"

    logger.info(f"Iniciando ajuste de fechas en {database_id}: {hours} horas a partir del {start_date.date().isoformat()}. Filtros: [{filter_description}]. Total de páginas encontradas para revisión: {total_pages}")


    if total_pages == 0:
        # Si no se encontraron páginas con los filtros iniciales
        resumen = f"Operación completada: No se encontraron registros que coincidieran con los filtros. Filtros: [{filter_description}]."
        logger.info(f"Ajuste de fechas completado con 0 páginas encontradas.")
        return resumen

    # Procesar cada página encontrada
    for page in pages:
        properties = page.get("properties", {})
        page_id = page.get("id")

        if not page_id:
            logger.warning("Página sin ID encontrada en los resultados de la consulta, omitiendo.")
            skipped_pages += 1
            continue

        # Extraer la propiedad de fecha por el nombre definido
        date_property_data = properties.get(DATE_PROPERTY_NAME, {})
        date_property_value = date_property_data.get("date") # Esto debería ser {"start": ..., "end": ...} o None

        if date_property_value and "start" in date_property_value and date_property_value["start"] is not None:
            try:
                # Parsear la fecha de inicio desde el string ISO 8601 de Notion
                start_date_notion_str = date_property_value["start"]
                # Manejar correctamente el formato ISO, incluyendo posibles zonas horarias o 'Z'
                start_date_notion = datetime.fromisoformat(
                    start_date_notion_str.replace('Z', '+00:00') if start_date_notion_str and start_date_notion_str.endswith('Z') else start_date_notion_str
                )
                # Opcional: Convertir a UTC si todas las fechas de Notion están en UTC y quieres operar en un solo huso
                # start_date_notion = start_date_notion.astimezone(timezone.utc) if start_date_notion.tzinfo else start_date_notion.replace(tzinfo=timezone.utc)
                # Para simplificar y si las fechas en Notion no son sensibles a la zona horaria, puedes remover la info de zona:
                start_date_notion_naive = start_date_notion.replace(tzinfo=None)


                # Verificar si la fecha de inicio de la página es posterior o igual a la fecha de filtro 'start_date'
                # Usamos la fecha pura para la comparación si start_date viene como AAAA-MM-DD
                if start_date_notion_naive.date() >= start_date.date():
                    # Calcular las nuevas fechas
                    new_start_naive = start_date_notion_naive + timedelta(hours=hours)

                    new_end_naive = None
                    if date_property_value.get("end"):
                         end_date_notion_str = date_property_value["end"]
                         end_date_notion = datetime.fromisoformat(
                             end_date_notion_str.replace('Z', '+00:00') if end_date_notion_str and end_date_notion_str.endswith('Z') else end_date_notion_str
                         )
                         end_date_notion_naive = end_date_notion.replace(tzinfo=None)
                         new_end_naive = end_date_notion_naive + timedelta(hours=hours)

                    # Preparar el payload para la actualización de fecha. Notion espera ISO 8601.
                    # Es mejor enviar de vuelta strings ISO sin tzinfo si los originales no tenían o se limpiaron.
                    # Opcional: Añadir '.isoformat()' con timezone si estás manejando zonas horarias explícitamente.
                    properties_to_update = {
                         DATE_PROPERTY_NAME: {
                             "date": {
                                 "start": new_start_naive.isoformat(),
                                 "end": new_end_naive.isoformat() if new_end_naive else None
                             }
                          }
                    }

                    # Realizar la actualización de la página
                    status_code, update_response = update_notion_page_properties(notion_client, page_id, properties_to_update)

                    if 200 <= status_code < 300:
                        updated_pages += 1
                    else:
                        failed_updates += 1
                        # Loguea detalles del error de Notion si están disponibles
                        notion_error_msg = update_response.get('notion_error_details', {}).get('message', update_response.get('error', 'Desconocido'))
                        logger.error(f"Fallo al actualizar fecha en página {page_id}: Estado={status_code}, Mensaje interno={update_response.get('error', 'N/A')}. Msg Notion: {notion_error_msg}")
                else:
                    logger.info(f"Página {page_id} con fecha de inicio ({start_date_notion_naive.date().isoformat()}) anterior al filtro ({start_date.date().isoformat()}), omitiendo ajuste.")
                    skipped_pages += 1

            except (ValueError, TypeError) as e:
                logger.error(f"Error al procesar o parsear fecha de página {page_id} ('{start_date_notion_str}'): {str(e)}", exc_info=True)
                failed_updates += 1
            except Exception as e:
                 logger.error(f"Error inesperado al procesar página {page_id} durante el ajuste: {str(e)}", exc_info=True)
                 failed_updates += 1
        else:
             # La página no tiene la propiedad de fecha, no tiene un valor válido o 'start' es None.
             logger.info(f"Página {page_id} sin propiedad '{DATE_PROPERTY_NAME}' válida con fecha de inicio, omitiendo.")
             skipped_pages += 1


    logger.info(f"Proceso de ajuste de fechas completado: {updated_pages} páginas actualizadas, {failed_updates} fallidas, {skipped_pages} omitidas")

    # Construir el mensaje resumen para la respuesta al usuario/API
    resumen = (
        f"Resumen del Ajuste de Fechas:\n"
        f"Filtros aplicados: [{filter_description}]\n"
        f"Fecha límite de inicio (inclusive): {start_date.date().isoformat()}\n"
        f"Total de registros encontrados para revisión: {total_pages}\n"
        f"Registros con fecha anterior omitidos: {skipped_pages} (solo se ajustan fechas iguales o posteriores a {start_date.date().isoformat()})\n"
        f"Registros actualizados con éxito: {updated_pages}\n"
        f"Actualizaciones fallidas: {failed_updates}\n"
        f"Ajuste aplicado: +{hours} horas" if hours >= 0 else f"Ajuste aplicado: {hours} horas"
    )

    if failed_updates > 0:
         resumen += "\n\n¡ADVERTENCIA! Hubo actualizaciones fallidas. Consulta los logs del servidor para obtener más detalles específicos sobre los errores por página."

    return resumen

# *** FUNCIÓN adjust_dates_api (llamada desde ajustes.py) ***
def adjust_dates_api(
    notion_client: Client,
    database_id: str, # Este es el ID de la base de datos de Ajustes/Proyectos (donde se ajustan fechas)
    hours: int,
    start_date_str: str, # Fecha límite en formato AAAA-MM-DD
    property_filters: Dict[str, Any] = None # Diccionario de {nombre_propiedad: valor_filtro}
) -> Tuple[Dict, int]: # Retorna (respuesta_dict, status_code HTTP)
    """
    Lógica principal para la ruta de ajuste de fechas.
    Valida entrada, construye filtros y llama a adjust_dates_with_filters_util.
    Retorna una respuesta JSON y un código de estado HTTP.
    """
    if not notion_client or not database_id:
         error_msg = "Cliente de Notion no inicializado o Database ID faltante para Ajustes. Problema de configuración del servidor."
         logger.error(error_msg)
         return {
            "success": False,
            "error": error_msg,
            "status_code": 503 # Service Unavailable
        }, 503

    try:
        # 1. Validar y convertir la fecha de string a objeto datetime (solo fecha, sin hora, para comparación)
        # El formato esperado es AAAA-MM-DD
        start_date_filter_dt = datetime.strptime(start_date_str, '%Y-%m-%d')

        # 2. Construir los filtros para la consulta a Notion
        # build_filter_from_properties_util maneja la obtención de tipos y la creación de condiciones
        filters = build_filter_from_properties_util(notion_client, database_id, property_filters) if property_filters else []

        # NOTA IMPORTANTE: adjust_dates_with_filters_util implementa la lógica de *revisar* que la fecha
        # de cada página encontrada sea >= start_date_filter_dt *antes* de ajustarla.
        # build_filter_from_properties_util puede incluir un filtro 'on_or_after' si el frontend lo manda,
        # pero la función de ajuste principal tiene la verificación final por seguridad.

        # 3. Llamar a la función auxiliar que realiza la búsqueda y el ajuste de fechas
        result_message = adjust_dates_with_filters_util(notion_client, database_id, hours, start_date_filter_dt, filters)

        # 4. Determinar el status code de la respuesta API basado en el mensaje resumen
        status_code_return = 200 # Default: Éxito total o parcial sin errores en la API de Notion
        # Si el mensaje incluye la advertencia de fallos, indicamos Partial Content
        if "¡ADVERTENCIA!" in result_message or "fallidas:" in result_message:
             status_code_return = 207 # Partial Content (Multi-Status)

        # 5. Retornar la respuesta JSON y el status code HTTP
        return {
            "success": True,
            "message": result_message,
            "status_code": status_code_return
        }, status_code_return


    except ValueError as e:
        # Error si el formato de fecha de entrada no es AAAA-MM-DD
        error_msg = f"Formato de fecha inválido recibido: '{start_date_str}'. Asegúrate de usar el formato AAAA-MM-DD. Detalle: {str(e)}"
        logger.error(f"Error en entrada de fecha para Ajustes: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "status_code": 400 # Bad Request
        }, 400

    except Exception as e:
        # Captura cualquier otro error inesperado durante el procesamiento de la lógica
        error_msg = f"Error inesperado del servidor al procesar el ajuste de fechas: {str(e)}"
        full_trace = traceback.format_exc() # Captura el traceback completo
        logger.error(f"--- ERROR INESPERADO en adjust_dates_api --- Exception: {e}\n{full_trace}")
        return {
            "success": False,
            "error": error_msg,
            "status_code": 500, # Internal Server Error
            "trace": full_trace # Opcional: incluir traceback en la respuesta si es para depuración interna
        }, 500