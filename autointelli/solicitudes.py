# solicitudes.py

from flask import Blueprint, request, jsonify, render_template, url_for
from flask_login import login_required # Importar login_required si se requiere autenticación
from flask_cors import cross_origin # Si necesitas CORS para esta ruta
from notion_client import Client
# from notion_client.errors import APIResponseError # Opcional
import os
from dotenv import load_dotenv # Asegurarse de que load_dotenv se llama en app.py principal
import datetime
import json
import traceback

# --- Configuración de Notion (Específica para esta herramienta si es diferente) ---
# Si el NOTION_TOKEN es el mismo para todas, puedes dejarlo en app.py y pasarlo
# o acceder a os.environ directamente aquí si load_dotenv ya corrió
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID_MATERIALES_DB1 = os.environ.get("DATABASE_ID") # ID DB 1 Materiales
DATABASE_ID_MATERIALES_DB2 = os.environ.get("DATABASE_ID_2") # ID DB 2 Materiales

# Inicializar cliente Notion (solo si las variables están definidas)
if NOTION_TOKEN and DATABASE_ID_MATERIALES_DB1 and DATABASE_ID_MATERIALES_DB2:
    try:
        notion = Client(auth=NOTION_TOKEN)
        print("Cliente de Notion para Solicitudes inicializado.")
    except Exception as e:
        print(f"ERROR al inicializar Notion Client para Solicitudes: {e}")
        notion = None # Marcar como no inicializado
else:
    print("ADVERTENCIA: Variables de entorno Notion para Solicitudes no configuradas. Las rutas no funcionarán.")
    notion = None


# --- Crear el Blueprint ---
# El primer argumento es el nombre del blueprint ('solicitudes')
# El segundo argumento es el nombre del módulo (__name__)
# url_prefix añade un prefijo a todas las rutas registradas en este blueprint
solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/solicitudes')

# --- Definir Rutas DENTRO del Blueprint ---

@solicitudes_bp.route('/') # La ruta COMPLETA será /solicitudes/
@login_required # Requerir login
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def request_for_material_index():
    print("Solicitud GET recibida en /solicitudes/")
    # Renderiza la plantilla específica para esta herramienta
    # La ruta de la plantilla es relativa a la carpeta 'templates' principal
    return render_template('request_for_material.html')

@solicitudes_bp.route('/submit', methods=['POST']) # La ruta COMPLETA será /solicitudes/submit
@login_required # Requerir login
# @cross_origin() # Descomentar si necesitas CORS específicamente aquí
def submit_request_for_material():
    # --- Lógica de Procesamiento del app.py original ---
    folio_solicitud = None
    status_code = 500
    error_occurred = False
    items_processed_count = 0
    items_failed_count = 0
    first_page1_url = None
    first_page2_url = None

    # Verificar si el cliente Notion se inicializó correctamente
    if notion is None:
         print("ERROR: El cliente de Notion para Solicitudes no está inicializado. No se puede procesar la solicitud.")
         return jsonify({"error": "La integración con Notion para Solicitudes no está configurada correctamente."}), 503 # Service Unavailable

    print("\n--- Recibiendo nueva solicitud de Materiales ---")
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "No se recibieron datos."}), 400
        print("Datos recibidos:", json.dumps(data, indent=2, ensure_ascii=False))

        selected_proveedor = data.get("proveedor")
        torni_items = data.get('torni_items')
        # Generar Folio único si no viene
        # *** CORRECCIÓN: Usar datetime.datetime.now() si no cambiaste el import en este nuevo archivo ***
        # O usar datetime.now() si cambiaste el import a 'from datetime import datetime'
        folio_solicitud = data.get("folio_solicitud", f"EMG-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")
        print(f"--- Procesando Folio de Materiales: {folio_solicitud} ---")

        # --- Propiedades Comunes ---
        common_properties = {}
        # ... (COPIA EXACTA de la lógica de common_properties) ...
        if data.get("nombre_solicitante"): common_properties["Nombre del solicitante"] = {"select": {"name": data["nombre_solicitante"]}}
        if selected_proveedor: common_properties["Proveedor"] = {"select": {"name": selected_proveedor}}
        if data.get("departamento_area"): common_properties["Departamento/Área"] = {"select": {"name": data["departamento_area"]}}
        if data.get("fecha_solicitud"): common_properties["Fecha de solicitud"] = {"date": {"start": data["fecha_solicitud"]}}
        if folio_solicitud: common_properties["Folio de solicitud"] = {"rich_text": [{"type": "text", "text": {"content": folio_solicitud}}]}
        if data.get("Proyecto"): common_properties["Proyecto"] = {"rich_text": [{"type": "text", "text": {"content": data["Proyecto"]}}]}
        if data.get("especificaciones_adicionales"): common_properties["Especificaciones adicionales"] = {"rich_text": [{"type": "text", "text": {"content": data["especificaciones_adicionales"]}}]}

        # --- Lógica Condicional ---
        items_to_process = torni_items if selected_proveedor == 'Torni' and isinstance(torni_items, list) else [data]
        is_torni_mode = selected_proveedor == 'Torni'

        if not items_to_process or (is_torni_mode and len(items_to_process) == 0):
             return jsonify({"error": "No hay items para procesar."}), 400

        for index, item_data in enumerate(items_to_process):
            item_index_str = f"Item {index + 1}" if is_torni_mode else "Item Único"
            print(f"--- Procesando {item_index_str} ---")
            item_properties = common_properties.copy()

            # --- Construir Propiedades COMPLETAS para este item ---
            if is_torni_mode:
                 try: quantity = int(item_data.get("quantity", 0)); item_properties["Cantidad solicitada"] = {"number": quantity if quantity > 0 else 0}
                 except (ValueError, TypeError): item_properties["Cantidad solicitada"] = {"number": 0}
                 item_id = str(item_data.get("id", "")).strip(); item_desc = str(item_data.get("description", "")).strip()
                 if item_id: item_properties["ID de producto"] = {"rich_text": [{"type": "text", "text": {"content": item_id}}]}
                 if item_desc: item_properties["Descripción"] = {"rich_text": [{"type": "text", "text": {"content": item_desc}}]}
            else: # Proveedor estándar
                 if item_data.get("cantidad_solicitada") is not None:
                    try: item_properties["Cantidad solicitada"] = {"number": int(item_data["cantidad_solicitada"])}
                    except (ValueError, TypeError): item_properties["Cantidad solicitada"] = {"number": 0}
                 if item_data.get("tipo_material"): item_properties["Tipo de material"] = {"select": {"name": item_data["tipo_material"]}}
                 if item_data.get("nombre_material"): item_properties["Nombre del material"] = {"select": {"name": item_data["nombre_material"]}}
                 if item_data.get("unidad_medida"): item_properties["Unidad de medida"] = {"select": {"name": item_data["unidad_medida"]}}
                 if item_data.get("largo"): item_properties["Largo (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["largo"])}}]}
                 if item_data.get("ancho"): item_properties["Ancho (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["ancho"])}}]}
                 if item_data.get("alto"): item_properties["Alto (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["alto"])}}]}
                 if item_data.get("diametro"): item_properties["Diametro (dimensión)"] = {"rich_text": [{"type": "text", "text": {"content": str(item_data["diametro"])}}]}


            # --- Crear página en DB 1 ---
            page1_created = False; error1_details = None; page1_url_current = None
            try:
                print(f"  Intentando crear página en DB 1 Materiales ({DATABASE_ID_MATERIALES_DB1})...")
                response1 = notion.pages.create(parent={"database_id": DATABASE_ID_MATERIALES_DB1}, properties=item_properties)
                page1_url_current = response1.get("url")
                if index == 0: first_page1_url = page1_url_current
                print(f"  Página creada en DB 1: {page1_url_current}")
                page1_created = True
            except Exception as e1: error1_details = str(e1); print(f"ERROR en DB 1 Materiales ({item_index_str}): {error1_details}")

            # --- Crear página en DB 2 ---
            page2_created = False; error2_details = None; page2_url_current = None
            try:
                print(f"  Intentando crear página en DB 2 Materiales ({DATABASE_ID_MATERIALES_DB2})...")
                response2 = notion.pages.create(parent={"database_id": DATABASE_ID_MATERIALES_DB2}, properties=item_properties)
                page2_url_current = response2.get("url")
                if index == 0: first_page2_url = page2_url_current
                print(f"  Página creada en DB 2: {page2_url_current}")
                page2_created = True
            except Exception as e2: error2_details = str(e2); print(f"ERROR en DB 2 Materiales ({item_index_str}): {error2_details}")

            # Registrar si hubo algún fallo
            if not page1_created or not page2_created: error_occurred = True; items_failed_count += 1
            else: items_processed_count += 1
        # --- Fin del bucle ---

        # --- Construir Respuesta Final ---
        status_code = 200
        final_response = {}
        if items_processed_count > 0 and not error_occurred:
             final_response["message"] = f"Solicitud Folio '{folio_solicitud}' ({items_processed_count} item(s)) registrada en ambas DBs."
             final_response["notion_url"] = first_page1_url
             final_response["notion_url_db2"] = first_page2_url
        elif items_processed_count > 0 and error_occurred:
             final_response["warning"] = f"Folio '{folio_solicitud}' procesado parcialmente: {items_processed_count} OK, {items_failed_count} fallaron. Ver logs."
             final_response["notion_url"] = first_page1_url # Podría ser null si falló el primero
             status_code = 207 # Partial Content
        else:
             final_response["error"] = f"Error al procesar Folio '{folio_solicitud}'. Ningún item registrado. Ver logs."
             status_code = 500

        print(f"--- Procesamiento de Materiales completado para Folio {folio_solicitud}. Resultado: {final_response} ---")
        return jsonify(final_response), status_code

    # --- Manejo de Errores Generales ---
    except Exception as e:
        error_message = str(e)
        print(f"\n--- ERROR INESPERADO en submit_request_for_material (Folio: {folio_solicitud or 'NO ASIGNADO'}) ---")
        print(traceback.format_exc())
        print(f"--- FIN ERROR ---")
        return jsonify({"error": "Error inesperado al procesar la solicitud de Materiales.", "details": error_message}), 500
    # --- FIN DEL CÓDIGO COPIADO ---

# --- Puedes añadir más rutas relacionadas con solicitudes de materiales aquí ---
# @solicitudes_bp.route('/some-other-route')
# def some_other_function():
#    pass