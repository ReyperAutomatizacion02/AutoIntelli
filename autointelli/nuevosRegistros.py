# autointelli/nuevosRegistros.py
# Este archivo solo contiene funciones auxiliares de Notion.
# NO debe cargar .env ni inicializar el cliente Notion.
# NO debe tener un bloque __main__.

import logging
# No importar notion_client ni os ni dotenv aquí globalmente.
# from notion_client import Client # No inicializar aquí
# import os # No leer variables de entorno aquí

logger = logging.getLogger("nuevos_registros_notion")

def crear_proyecto(notion_client, database_id_proyectos, nombre_proyecto):
    """
    Crea una nueva página de proyecto en la base de datos de Proyectos
    usando un cliente de Notion proporcionado.
    """
    if not notion_client or not database_id_proyectos or not nombre_proyecto:
        logger.error("Faltan argumentos para crear_proyecto.")
        return None

    try:
        response = notion_client.pages.create(
            parent={"database_id": database_id_proyectos},
            properties={
                "ID del proyecto": {"title": [{"text": {"content": nombre_proyecto}}]},
                # ... (añade más propiedades aquí si tu base de datos de Proyectos tiene más campos)
                # Asegúrate de que las keys coincidan exactamente con los nombres de las propiedades en Notion
            }
        )
        logger.info(f"Proyecto '{nombre_proyecto}' creado en Notion con ID: {response['id']}")
        return response['id']
    except Exception as e:
        logger.error(f"Error al crear el proyecto '{nombre_proyecto}': {e}", exc_info=True)
        return None

def crear_partidas(notion_client, database_id_partidas, num_partidas, proyecto_id):
    """
    Crea múltiples páginas de partida en la base de datos de Partidas
    usando un cliente de Notion proporcionado y las relaciona con el proyecto.
    """
    if not notion_client or not database_id_partidas or not proyecto_id or not isinstance(num_partidas, int) or num_partidas <= 0:
         logger.error("Faltan argumentos válidos para crear_partidas.")
         return []

    partidas_ids = []
    proyecto_nombre = "Proyecto Desconocido" # Valor por defecto

    try:
        proyecto_page = notion_client.pages.retrieve(proyecto_id)
        title_prop = proyecto_page.get('properties', {}).get('ID del proyecto', {})
        if title_prop.get('type') == 'title' and title_prop.get('title'):
             proyecto_nombre = title_prop['title'][0].get('plain_text', 'Proyecto sin Nombre')
        else:
             logger.warning(f"No se encontró la propiedad Title 'ID del proyecto' o estaba vacía para el proyecto ID '{proyecto_id}'.")

    except Exception as e:
        logger.error(f"Error al obtener el nombre del proyecto con ID '{proyecto_id}': {e}", exc_info=True)


    for i in range(num_partidas):
        partida_conteo = f"{i:02d}.00"
        nombre_partida = f"{proyecto_nombre}-{partida_conteo}"

        try:
            response = notion_client.pages.create(
                parent={"database_id": database_id_partidas},
                properties={
                    "ID de partida": {"title": [{"text": {"content": nombre_partida}}]},
                    "Proyectos": {
                        "relation": [
                            {"id": proyecto_id}
                        ]
                    },
                    # ... otras propiedades ...
                }
            )
            partidas_ids.append(response['id'])
            logger.info(f"Partida '{nombre_partida}' creada con ID: {response['id']}")
        except Exception as e:
            logger.error(f"Error al crear la partida '{nombre_partida}': {e}", exc_info=True)

    logger.info(f"Proceso crear_partidas completado para proyecto ID {proyecto_id}: {len(partidas_ids)} creadas.")
    return partidas_ids