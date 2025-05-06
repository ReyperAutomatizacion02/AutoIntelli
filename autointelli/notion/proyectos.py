import logging
from notion_client import Client
from typing import Optional, Dict, List, Tuple, Any, Union
import json
import traceback # Por si el error es capturado al final

# Importar funciones auxiliares y constantes
from .utils import get_database_properties_util, create_filter_condition_util, get_pages_with_filter_util
from .constants import NOTION_PROP_PROYECTO_BUSQUEDA_ID # Necesita la constante para el nombre de la propiedad de búsqueda

logger = logging.getLogger(__name__)

# *** FUNCIÓN find_project_page_by_property_value (para buscar proyectos) ***
def find_project_page_by_property_value(
    notion_client: Client,
    database_id_proyectos: str, # ID de la BD de Proyectos
    property_name: str,        # Nombre de la propiedad en la BD de Proyectos para buscar (ej. "ID del proyecto")
    property_value: Any        # Valor a buscar en esa propiedad
) -> Optional[str]:
    """
    Busca una página en la base de datos de Proyectos por el valor exacto (para Select/Number)
    o que contenga (para Rich Text/Title) de una propiedad específica.
    Devuelve el page_id de la primera página encontrada si hay coincidencias, None en caso contrario.
    """
    # Validaciones básicas de entrada
    if not notion_client or not database_id_proyectos or not property_name or property_value is None or (isinstance(property_value, str) and str(property_value).strip() == ""):
        logger.warning(f"find_project_page_by_property_value: Datos insuficientes. DB ID Proyectos: '{database_id_proyectos}', Prop Nombre: '{property_name}', Prop Valor: '{property_value}'")
        return None

    try:
        # 1. Obtener las propiedades de la BD de Proyectos para saber el tipo de la propiedad de búsqueda.
        db_proyectos_properties = get_database_properties_util(notion_client, database_id_proyectos)

        if property_name not in db_proyectos_properties:
            logger.warning(f"find_project_page_by_property_value: Propiedad de búsqueda '{property_name}' no encontrada en la base de datos de Proyectos '{database_id_proyectos}'. No se puede buscar el proyecto.")
            return None

        prop_info = db_proyectos_properties[property_name]
        prop_type = prop_info.get("type")

        # 2. Crear una condición de filtro API Notion usando el tipo y valor.
        # Intentamos usar 'equals' para tipos que idealmente tienen valores únicos (Select, Number).
        # Usamos 'contains' para texto/título por flexibilidad, aunque podría encontrar coincidencias parciales.
        filter_condition = {}
        cleaned_value = str(property_value).strip() # Limpiar espacios

        if prop_type == "select":
             # Busca una opción de select que coincida EXACTAMENTE con el valor
             filter_condition = { "property": property_name, "select": { "equals": cleaned_value } }
        elif prop_type == "number":
             try:
                 float_value = float(cleaned_value)
                 # Busca un número que coincida EXACTAMENTE
                 filter_condition = { "property": property_name, "number": { "equals": float_value } }
             except (ValueError, TypeError):
                  # Si el valor no se puede convertir a número, no se puede filtrar por Number
                  logger.warning(f"find_project_page_by_property_value: Valor '{cleaned_value}' no es un número válido para buscar en propiedad Number '{property_name}'.")
                  return None
        elif prop_type in ["rich_text", "title", "url", "email", "phone_number"]:
             # Busca texto que CONTENGA el valor
             # NOTA: La API de Notion usa 'rich_text' como clave para la condición, incluso si el tipo real es 'title'.
             filter_condition = { "property": property_name, prop_type if prop_type != 'text' else 'rich_text': { "contains": cleaned_value } }
        # Puedes añadir más tipos si necesitas buscar proyectos por otras propiedades (ej. Checkbox, etc.)
        # elif prop_type == "checkbox":
        #     bool_value = cleaned_value.lower() in ['true', 'yes', 'on', '1']
        #     filter_condition = { "property": property_name, "checkbox": { "equals": bool_value } }


        # 3. Validar que se pudo construir una condición de filtro
        if not filter_condition:
            logger.warning(f"find_project_page_by_property_value: No se pudo crear condición de filtro válida. Prop: '{property_name}', Tipo: '{prop_type}', Valor: '{property_value}'")
            return None

        logger.info(f"find_project_page_by_property_value: Realizando búsqueda de página de proyecto en DB '{database_id_proyectos}' con filtro: {json.dumps(filter_condition, ensure_ascii=False)}")

        # 4. Ejecutar la consulta a Notion. Limitamos a 2 resultados para detectar posibles duplicados.
        # get_pages_with_filter_util ya maneja la paginación interna si hay más de 100 (aunque limitamos aquí a 2).
        found_pages = get_pages_with_filter_util(
            notion_client,
            database_id_proyectos,
            filters=[filter_condition],
            page_size=2 # Solo necesitamos 1 o 2 para ver si hay múltiples coincidencias
        )

        # 5. Procesar los resultados
        if found_pages:
            if len(found_pages) > 1:
                 logger.warning(f"find_project_page_by_property_value: Múltiples páginas encontradas en DB Proyectos para filtro '{property_name}'='{property_value}'. Usando la primera encontrada.")

            project_page_id = found_pages[0].get("id")
            if project_page_id:
                logger.info(f"find_project_page_by_property_value: Página de proyecto encontrada con ID={project_page_id} para valor '{property_value}'.")
                return project_page_id
            else:
                logger.warning(f"find_project_page_by_property_value: Página encontrada para filtro '{property_name}'='{property_value}', pero el objeto de página retornado por Notion no tiene un ID válido. Omitiendo.")
                return None
        else:
            # No se encontraron páginas con el filtro
            logger.warning(f"find_project_page_by_property_value: No se encontró ninguna página en DB Proyectos con filtro '{property_name}'='{property_value}'.")
            return None

    except Exception as e:
        # Captura cualquier error inesperado durante el proceso de búsqueda
        logger.error(f"find_project_page_by_property_value: Error inesperado al buscar página de proyecto para valor '{property_value}': {e}", exc_info=True)
        return None