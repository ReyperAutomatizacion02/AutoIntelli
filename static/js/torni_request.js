// static/js/torni_request.js

// Este script asume que las siguientes variables globales se definen en la plantilla HTML
// antes de que este script se cargue, usando url_for:
// const TORNI_MASTERLIST_URL = "{{ url_for('static', filename='data/torni_items_masterlist.json') }}";


document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a elementos DOM ---
    // Asegúrate de que estos IDs/clases coinciden con tu plantilla HTML (torni_request_form.html)
    const materialForm = document.getElementById('torni-accessories-form'); // ID del formulario Torni
    const responseMessageDiv = document.getElementById('response-message'); // Div para feedback AJAX

    // Campos comunes (estos sí están en el formulario Torni)
    const nombreSolicitanteInput = document.getElementById('nombre_solicitante');
    const departamentoAreaSelect = document.getElementById('departamento_area');
    const fechaInput = document.getElementById('fecha_solicitud');
    const proyectoInput = document.getElementById('proyecto'); // Asumo ID 'proyecto' y name 'Proyecto' (OJO mayúscula?)
    const especificacionesAdicionalesInput = document.getElementById('especificaciones_adicionales');
    const folioDisplayValue = document.getElementById('folio-display-value');
    const folioInputHidden = document.getElementById('folio_solicitud');
    // No necesitamos referencia directa al select #proveedor si está deshabilitado,
    // pero sí al input hidden si lo usas para enviar el valor
    const proveedorInputHidden = document.querySelector('#torni-accessories-form input[name="proveedor"]'); // Para obtener el valor oculto "Torni"


    // Referencias a elementos de Torni
    const torniTableContainer = document.getElementById('torni-table-container');
    const torniTableBody = document.getElementById('torni-items-tbody'); // Body de la tabla donde se añaden filas
    const addTorniItemBtn = document.getElementById('add-torni-item-btn'); // Botón para añadir fila Torni


    // --- Variables Globales del Script ---
    let torniMasterList = []; // Para lista maestra de items Torni (cargado de JSON)
    let currentFolio = null;


    // --- ** DEFINICIÓN DE FUNCIONES ** ---

    // --- Funciones de Folio ---
    function generateFolio() {
        const timestamp = Date.now();
        const randomPart = Math.random().toString(36).substring(2, 8).toUpperCase();
        return `MAT-${timestamp}-${randomPart}`;
    }

    function updateFolioDisplay(folio) {
        if (folioDisplayValue) folioDisplayValue.textContent = folio;
        if (folioInputHidden) folioInputHidden.value = folio;
    }

    // --- Lógica Tabla Torni (con Awesomplete) ---
    // Esta función maneja la adición de filas Torni y la inicialización de Awesomplete para cada fila
    function addTorniRow() {
        if (!torniTableBody) { console.error("Elemento #torni-items-tbody no encontrado."); return; }
        console.log("Intentando añadir fila Torni...");
        const rowId = Date.now() + Math.random().toString(36).substring(2, 5); // ID simple para la fila
        const newRow = torniTableBody.insertRow();
        newRow.setAttribute('data-row-id', rowId);

        newRow.innerHTML = `
            <td><input type="number" class="torni-qty" name="quantity" min="1" value="1" required></td>
            <td><input type="text" class="torni-id" name="id" readonly></td> {# ID será llenado por Awesomplete #}
            <td><input type="text" class="torni-desc" name="description" placeholder="Escribe para buscar..." required autocomplete="off"></td> {# Campo para búsqueda #}
            <td><button type="button" class="delete-row-btn">X</button></td>
        `;

        // Referencias a los inputs en la fila recién creada
        const qtyInput = newRow.querySelector('.torni-qty');
        const descInput = newRow.querySelector('.torni-desc');
        const idInput = newRow.querySelector('.torni-id');
        const deleteBtn = newRow.querySelector('.delete-row-btn');

        // Añadir listener para el botón de eliminar de ESTA fila
        if (deleteBtn) { deleteBtn.addEventListener('click', deleteTorniRow); }


        // --- Inicializar Awesomplete para la nueva fila ---
        if (descInput && typeof Awesomplete !== 'undefined' && torniMasterList.length > 0) {
             console.log("Inicializando Awesomplete para nueva fila...");

             const awesompleteInstance = new Awesomplete(descInput, {
                 list: torniMasterList, // Pasar el ARRAY COMPLETO de objetos {id, description}
                 data: function (item, input) { // `item` es un objeto de torniMasterList {id, description}
                     //console.log("Awesomplete 'data' function - input item:", item);
                     let html = item.description.replace(new RegExp(Awesomplete.$.regExpEscape(input.trim()), "gi"), "<mark>$&</mark>");
                     // Retornamos un nuevo objeto para Awesomplete, incluyendo el ID y el objeto original
                     return { label: html, value: item.description, original: item, id: item.id };
                 },
                 item: function (data, input) { // Recibe el objeto que retornó tu función 'data': {label, value, original, id}
                      // Aquí data.label ya puede contener HTML si lo formateaste en la función data
                      return Awesomplete.ITEM(data.label, input);
                 },
                 replace: function(suggestion) { // Recibe el objeto {label, value, original, id}
                     //console.log("Awesomplete 'replace' function - suggestion:", suggestion);
                     // Cuando el usuario selecciona, poner el valor (descripción) en el input
                     this.input.value = suggestion.value;
                 },
                 minChars: 1, maxItems: 10, autoFirst: true,
                 filter: function(item, input) { // Filtra la lista. `item` es el objeto retornado por la función 'data'
                    // item aquí es {label, value, original, id}
                    // Queremos filtrar basándonos en la descripción (la propiedad 'value')
                    return item.value.trim().toLowerCase().includes(input.trim().toLowerCase());
                 }
             });

             // --- Listener para cuando se SELECCIONA un item ---
             descInput.addEventListener('awesomplete-selectcomplete', function(event) {
                // Este evento se dispara cuando el usuario selecciona una sugerencia
                // event.text es el objeto que retornó tu función 'data': {label, value, original, id}
                console.log("--- Awesomplete Selección Completa (DEBUG) ---");
                console.log("Contenido completo de event.text:", event.text); // Loguea el objeto recibido

                // Intentar obtener el ID directamente de event.text.id (debería estar allí por la función data)
                // Si event.text.id existe, úsalo. Si no, será undefined.
                let selectedItemId = event.text.id; // Intentamos obtener el ID de la propiedad 'id' que añadimos en data

                console.log("ID obtenido inicialmente de event.text.id:", selectedItemId); // Log de verificación


                // --- SI event.text.id NO TIENE EL ID, BUSCAR EN LA LISTA MAESTRA ---
                // Verifica si selectedItemId es falsy (undefined, null, '')
                // ESTA LÓGICA ES EL FALLBACK. Si event.text.id no viene, busca en la lista maestra.
                if (!selectedItemId) {
                    console.log("ID no encontrado directamente en event.text. Buscando en lista maestra...");
                    // El valor seleccionado por Awesomplete (la descripción)
                    const selectedValueFromAwesomplete = event.text.value;
                    // Limpiar y normalizar el valor seleccionado (quitar espacios, mayúsculas, posibles saltos de línea)
                    // >>> CORRECCIÓN FINAL DEL TIPOGRÁFICO <<<
                    const normalizedSelectedValue = selectedValueFromAwesomplete.trim().toLowerCase().replace(/[\r\n]/g, '');


                    // Buscar el objeto original en la lista maestra (torniMasterList)
                    // Asegúrate de que la comparación en find() también normaliza la descripción del item maestro
                    const selectedItemData = torniMasterList.find(item => {
                        if (item && typeof item.description === 'string') {
                            const normalizedItemDescription = item.description.trim().toLowerCase().replace(/[\r\n]/g, '');
                            //console.log(`Comparando búsqueda: "${normalizedSelectedValue}" con item "${item.id}": "${normalizedItemDescription}" -> ${normalizedSelectedValue === normalizedItemDescription}`); // Log detallado si es necesario
                            return normalizedItemDescription === normalizedSelectedValue;
                        }
                        return false;
                    });

                    console.log("Objeto original encontrado en lista maestra:", selectedItemData); // LOGUEA ESTO

                    // Si se encontró el objeto en la lista maestra, usar su ID
                    if (selectedItemData && selectedItemData.id) {
                        selectedItemId = selectedItemData.id; // Asignar el ID encontrado
                        console.log("ID encontrado en lista maestra.");
                    } else {
                         console.warn("No se encontró objeto en lista maestra o no tiene ID para:", selectedValueFromAwesomplete);
                         selectedItemId = undefined; // Asegurarse de que es undefined si no se encuentra
                    }
                }
                // --- FIN BÚSQUEDA EN LISTA MAESTRA ---


                console.log("ID final determinado para llenar campo:", selectedItemId); // Log final del ID a usar

                // Buscar el input ID en la misma fila
                const currentRow = this.closest('tr');
                const idInputInRow = currentRow ? currentRow.querySelector('.torni-id') : null;

                // Actualizar el input ID usando el ID determinado
                // Solo actualizar si el input ID existe Y tenemos un ID válido (no undefined/null/vacío)
                if (idInputInRow && selectedItemId) {
                    console.log(`Actualizando ID para fila con ID ${currentRow.getAttribute('data-row-id')}:`, selectedItemId);
                    idInputInRow.value = String(selectedItemId).trim(); // Asegurarse de que es string y trim
                    idInputInRow.classList.remove('error-field'); // Limpiar error visual
                    this.classList.remove('error-field'); // Limpiar error visual en descripción si se encontró el ID
                } else if (idInputInRow) {
                     // Si no se pudo determinar el ID, limpiar el campo ID y marcar error
                     idInputInRow.value = '';
                     console.warn(`Fila con ID ${currentRow.getAttribute('data-row-id')}: No se pudo determinar el ID para "${event.text.value}". Limpiando campo ID.`);
                     this.classList.add('error-field'); // Marcar descripción como error
                     // Opcional: Marcar idInputInRow también
                     // idInputInRow.classList.add('error-field');
                } else {
                     console.error(`Fila con ID ${currentRow.getAttribute('data-row-id')}: No se pudo encontrar el campo ID en la fila para actualizar.`);
                }
            });

             // --- Limpiar ID si se borra/cambia descripción manualmente ---
             descInput.addEventListener('input', function() {
                 const currentDesc = this.value.trim(); // 'this' es el input descInput
                 const idInputInRow = this.closest('tr').querySelector('.torni-id'); // Obtener ID input en la misma fila

                 // Limpiar el ID si la descripción está vacía.
                 // Esto evita que se envíe un ID sin descripción.
                 if (idInputInRow && currentDesc === '') {
                     idInputInRow.value = ''; // Borrar ID
                 }
                 // Opcional: Lógica más avanzada aquí si quieres que el ID se borre
                 // si la descripción ya no coincide con un item válido DESPUÉS de escribir/borrar
                 // Pero la validación de submit ya verifica que el ID no esté vacío.
             });


        } else {
             if (typeof Awesomplete === 'undefined') console.error("¡Awesomplete NO está definido! Revisa la carga del script.");
             if (!torniMasterList || torniMasterList.length === 0) console.warn("torniMasterList está vacía o no cargada. No se puede inicializar Awesomplete para sugerencias.");
             if (!descInput) console.error("Input de descripción (.torni-desc) no encontrado en la nueva fila.");
             if (!idInput) console.error("Input de ID (.torni-id) no encontrado en la nueva fila.");
        }
         return newRow;
    } // Fin addTorniRow

    // Esta función elimina una fila de la tabla Torni
    function deleteTorniRow(event) {
        if (!torniTableBody) return;
        const button = event.target;
        const row = button.closest('tr');
        if (row) {
            row.remove();
        }
    }


    // --- Lógica de UI basada en Proveedor (Simplificada para este formulario) ---
    // Esta función en el formulario Torni es mínima ya que el proveedor es fijo.
     function handleProveedorChange() {
        // En este formulario, el proveedor siempre es Torni (está deshabilitado)
        // No necesitas alternar visibilidad de secciones, ya que solo existe la sección Torni
        console.log("handleProveedorChange ejecutado en formulario Torni. UI siempre en modo Torni.");

        // Limpiar errores visuales si es necesario (la validación de submit ya lo hace)
        // materialForm.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
        // if (responseMessageDiv) { ... limpiar ... }

        // Asegurar que la tabla tiene al menos una fila si hay datos maestros
        // Esto ya lo hace la lógica de carga inicial si el proveedor por defecto es Torni
        // Si necesitas añadir una fila después de un reset, hazlo en la lógica de reset del submit listener
        if (torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
            addTorniRow();
        } else if (torniTableBody && torniMasterList.length === 0) {
             // Si no hay datos maestros, loguear y quizás mostrar mensaje
             console.warn("Lista maestra de items Torni está vacía. No se pueden añadir items.");
             // Mostrar mensaje en el div de respuesta AJAX si no hay ya un mensaje de error/loading
              if(responseMessageDiv && responseMessageDiv.textContent === "") {
                 responseMessageDiv.textContent = "Lista de productos Torni no cargada. La creación de ítems no es posible.";
                 responseMessageDiv.classList.add('warning');
              }
         }
     }


    // --- Función para Recolectar TODOS los Datos del Formulario Torni ---
    // Recolecta campos comunes y los items de la tabla Torni
    function collectFormData() {
        const data = {};
        const form = materialForm;

        // Recolectar campos comunes (solo si están habilitados)
        // En este formulario, muchos campos comunes pueden ser deshabilitados (ej: proveedor)
        form.querySelectorAll('input, select, textarea').forEach(input => {
             // Solo recolectar campos con name y que no estén deshabilitados
             if (input.name && !input.disabled) {
                  if (input.type === 'number') {
                       data[input.name] = parseFloat(input.value) || 0; // Usar 0 como default si no es número
                  } else if (input.type === 'checkbox') {
                      data[input.name] = input.checked;
                  } else {
                       // Para campos de texto como dimensiones o texto general
                       // Solo incluir si tienen un valor no vacío después de trim
                       if (input.value.trim()) {
                           data[input.name] = input.value.trim();
                       }
                   }
             }
             // >>> AÑADIR LÓGICA PARA RECOLECTAR INPUTS OCULTOS (como el proveedor oculto) <<<
             // Los inputs ocultos suelen NO estar deshabilitados, pero es bueno ser explícito
             // o usar un selector diferente si hay muchos ocultos que no quieres
             if (input.type === 'hidden' && input.name) {
                 data[input.name] = input.value;
             }
        });

        // Obtener el proveedor del objeto data recolectado (debería ser 'Torni' del input hidden)
        const selectedProvider = data['proveedor'];


        // Recolectar items Torni de la tabla
        if (selectedProvider === 'Torni' && torniTableBody) {
            const torniItems = [];
            torniTableBody.querySelectorAll('tr').forEach(row => {
                const qtyInput = row.querySelector('.torni-qty');
                const idInput = row.querySelector('.torni-id');
                const descInput = row.querySelector('.torni-desc');

                if (qtyInput && idInput && descInput) {
                    const quantityValue = parseInt(qtyInput.value, 10);
                    const idValue = idInput.value.trim();
                    const descValue = descInput.value.trim();

                    // Validar si el item completo es válido para incluirlo
                    // La condición es: cantidad > 0 Y ID no vacío Y Descripción no vacía
                    if (quantityValue > 0 && idValue !== '' && descValue !== '') {
                        torniItems.push({
                            quantity: quantityValue,
                            id: idValue,
                            description: descValue
                        });
                    } else {
                        console.warn("Saltando item Torni inválido o incompleto en recolección:", {
                            qty: qtyInput.value,
                            id: idInput.value,
                            desc: descInput.value,
                            parsedQty: quantityValue,
                            isQtyValid: quantityValue > 0,
                            isIdEmpty: idValue === '',
                            isDescEmpty: descValue === ''
                        });
                         // Marcar visualmente los campos si son inválidos en la recolección
                         if (!(quantityValue > 0)) qtyInput.classList.add('error-field');
                         if (idValue === '') idInput.classList.add('error-field');
                         if (descValue === '') descInput.classList.add('error-field');
                    }
                } else {
                    console.error("Fila Torni sin todos los campos esperados encontrada en recolección.");
                }
            });
            data['torni_items'] = torniItems; // Añadir el array al objeto principal
        } else {
            // Si el proveedor no es Torni (lo cual no debería pasar en este formulario)
            // o si no se encontró el cuerpo de la tabla Torni, asegúrate de que torni_items es un array vacío
            data['torni_items'] = [];
        }


        console.log('Datos recolectados para JSON (Torni):', data);
        return data;
    }


    // --- Función para Configurar el Envío del Formulario (Fetch API) ---
    function setupFormSubmitListener() {
        if (!materialForm) {
             console.error("Formulario #torni-accessories-form no encontrado.");
             if(responseMessageDiv){
                  responseMessageDiv.textContent = `Error interno: Formulario principal no encontrado.`;
                  responseMessageDiv.classList.add('error');
             }
             return;
        }

       materialForm.addEventListener('submit', function(event) {
           event.preventDefault();

           const form = event.target;

           // 1. Recolectar datos Y validar ítems Torni al mismo tiempo con collectFormData
           const datosSolicitud = collectFormData();

           // 2. Validación General (Validar campos comunes obligatorios y al menos un item Torni válido)

           // Limpiar errores visuales y mensajes anteriores (hacerlo al inicio del submit)
            form.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
            if (responseMessageDiv) {
                 responseMessageDiv.textContent = '';
                 responseMessageDiv.classList.remove('processing', 'success', 'error');
            }

           let isValid = true;
           const errores = [];

           // Validar campos comunes requeridos (usan los IDs y names en el HTML)
           // Los names deben coincidir con las claves en el objeto 'datosSolicitud'
           const camposComunesReq = ['nombre_solicitante', 'proveedor', 'departamento_area', 'fecha_solicitud', 'Proyecto'];
           camposComunesReq.forEach(name => { // Itera sobre nombres, no IDs
               const value = datosSolicitud[name]; // Obtener valor del objeto recolectado
               // Validar que el valor no es null/undefined y no es una string vacía después de trim
               if (value === null || value === undefined || (typeof value === 'string' && !value.trim())) {
                   isValid = false;
                   // Intenta encontrar el input/select correspondiente para marcarlo visualmente
                   const campo = form.querySelector(`[name="${name}"]`);
                   if(campo) campo.classList.add('error-field');
                   // Intenta encontrar el label para un mensaje más descriptivo
                    const label = form.querySelector(`label[for="${campo ? campo.id : ''}"]`); // Encuentra label asociado por for="id"
                    const nombreCampo = label ? label.textContent.replace(':', '').trim() : name;
                   errores.push(`"${nombreCampo}" obligatorio.`);
                } else {
                   const campo = form.querySelector(`[name="${name}"]`);
                   if(campo) campo.classList.remove('error-field');
                }
           });

           // Validar si se recolectó al menos un item Torni válido
           const torniItemsRecogidos = datosSolicitud.torni_items || [];
           if (torniItemsRecogidos.length === 0) {
               isValid = false;
               errores.push("Debe añadir al menos un producto con cantidad, ID y descripción para proveedor Torni.");
               // Opcional: Marcar la tabla como error visual
               if(torniTableContainer) torniTableContainer.classList.add('error-field');
           } else {
               if(torniTableContainer) torniTableContainer.classList.remove('error-field');
           }


           // 3. Si hay errores de validación general, mostrar y detener
           if (!isValid) {
                console.log("Validación general fallida en frontend:", errores);
                const uniqueErrors = [...new Set(errores)];
                if (responseMessageDiv) {
                    responseMessageDiv.innerHTML = "Por favor, corrige los errores:<br>" + uniqueErrors.join('<br>');
                    responseMessageDiv.classList.add('error');
                }
                // Intenta enfocar el primer campo de error si existe
                 const primerErrorField = form.querySelector('.error-field:not(:disabled)');
                 if(primerErrorField) primerErrorField.focus();
                return; // Detener el submit
           }
           // --- Fin Validación General ---


           // 4. Si la validación general fue exitosa, proceder con el fetch
           console.log('Validación general exitosa. Datos del formulario a enviar:', datosSolicitud);

           // Mostrar estado de procesamiento ANTES del fetch
           if (responseMessageDiv) {
                responseMessageDiv.textContent = 'Enviando solicitud...';
                responseMessageDiv.classList.remove('error', 'success');
                responseMessageDiv.classList.add('processing');
            }

           fetch(form.action, { // Usa form.action para obtener la URL correcta
               method: form.method, // Usa el método del formulario (POST)
               headers: {
                   'Content-Type': 'application/json', // Enviamos JSON al backend
               },
               body: JSON.stringify(datosSolicitud) // Convertir el objeto de datos a string JSON
           })
           .then(response => {
                if (responseMessageDiv) responseMessageDiv.classList.remove('processing');

                if (!response.ok) {
                     return response.json().then(errData => {
                          let msg = errData.error || `Error: ${response.status}`;
                          if(errData.details) msg += `: ${errData.details}`; // Añadir detalles si existen
                          // Aquí puedes añadir manejo de errores específicos de Notion si vienen en la respuesta del backend
                          // Ej: if(errData.notion_error) msg += ` (Notion: ${errData.notion_error.message})`;

                          throw new Error(msg); // Lanzar un error con el mensaje construido
                     }).catch(() => {
                          // Si la respuesta no es JSON o hay un error al parsear JSON
                          throw new Error(`Error ${response.status}: ${response.statusText}`);
                     });
                }
                // Si la respuesta es OK (200, 207), procesar el JSON de éxito
                return response.json();
           })
           .then(data => {
               console.log('Respuesta backend exitosa:', data);

               let feedbackMessage = "";
               let isSuccess = false;
               let firstUrl = null;

               // Determinar mensaje de feedback y si fue éxito basado en la respuesta del backend
               if (data.message) { feedbackMessage = data.message; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db2; }
               else if (data.warning) { feedbackMessage = data.warning; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db2; } // Considera warning como éxito parcial
               else if (data.error) { feedbackMessage = data.error; isSuccess = false; } // Considera error como fallo total
               else { feedbackMessage = "Respuesta inesperada del servidor."; isSuccess = false; } // Fallback


               if (responseMessageDiv) {
                   // Usar innerHTML para permitir enlaces si firstUrl existe
                   responseMessageDiv.innerHTML = feedbackMessage + (firstUrl ? ` <a href="${firstUrl}" target="_blank" rel="noopener noreferrer">Ver Registro</a>` : '');

                   // Aplicar clase CSS según el estado
                   responseMessageDiv.classList.remove('success', 'error'); // Limpiar ambas antes
                   if (isSuccess) {
                       responseMessageDiv.classList.add('success');
                   } else {
                       responseMessageDiv.classList.add('error');
                   }
               }

               // Resetear formulario y UI solo si fue éxito total o parcial (isSuccess es true)
               if (isSuccess) {
                   form.reset();
                   // Generar nuevo folio para la próxima solicitud
                   currentFolio = generateFolio(); updateFolioDisplay(currentFolio);

                   // Resetear la tabla Torni
                   if (torniTableBody) torniTableBody.innerHTML = '';
                   // Asegurar una fila Torni inicial si la tabla está vacía y hay datos maestros
                    if (torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
                         addTorniRow();
                    }

                   // Restablecer fecha por defecto
                    if(fechaInput && !fechaInput.value) { // Solo si está vacío después del reset
                        const today = new Date();
                        const year = today.getFullYear();
                        const month = ('0' + (today.getMonth() + 1)).slice(-2);
                        const day = ('0' + today.getDate()).slice(-2);
                        fechaInput.value = `${year}-${month}-${day}`;
                   }
               }
           })
           .catch(error => {
               console.error('Error inesperado en fetch o procesamiento:', error);

                if (responseMessageDiv) {
                    responseMessageDiv.classList.remove('processing');
                    // Usar error.message para mostrar el mensaje del error capturado
                    responseMessageDiv.textContent = error.message || 'Error de red o del servidor.';
                    responseMessageDiv.classList.add('error');
                }
               // No resetear el formulario si hubo un error para que el usuario pueda corregir
           });
       });


   }


    // --- ** CÓDIGO QUE SE EJECUTA AL CARGAR LA PÁGINA (LLAMA A FUNCIONES) ** ---

    // Generar y Mostrar Folio Inicial
    currentFolio = generateFolio();
    updateFolioDisplay(currentFolio);
    console.log("Folio inicial generado:", currentFolio);

    // Deshabilitar el botón de submit inicialmente hasta que los datos se carguen
    if(materialForm) { // Asegúrate de que el formulario existe antes de intentar acceder al botón
        const submitBtn = materialForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
        } else {
            console.error("Botón de submit no encontrado en el formulario.");
            // Puedes deshabilitar el formulario completo o mostrar un mensaje de error
            if(responseMessageDiv) {
                responseMessageDiv.textContent = "Error interno: Botón de submit no encontrado.";
                responseMessageDiv.classList.add('error');
            }
        }
    }


    // Carga de Datos (LLAMA A fetch, que en su .then llama a funciones para inicializar UI)
    // En este script, solo necesitas cargar TORNI_MASTERLIST_URL
    if (typeof TORNI_MASTERLIST_URL !== 'undefined') {
        fetch(TORNI_MASTERLIST_URL)
        .then(res => {
             if (!res.ok) throw new Error(`Items Torni: ${res.status} ${res.statusText}`);
             return res.json();
         }).catch(error => { console.error("Error en fetch de Items Torni:", error); throw error; })
        .then(torniData => {
            console.log("Datos iniciales cargados con éxito (Items Torni).");
            torniMasterList = torniData || [];
            console.log("Contenido de torniMasterList:", torniMasterList);

            // --- Llamadas a funciones para inicializar la UI *después* de cargar los datos ---
            // handleProveedorChange(); // No necesaria en este formulario Torni (proveedor fijo)

             // Asegurar que la tabla tiene al menos una fila si hay datos maestros
             if (torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
                 addTorniRow(); // Añadir una fila si la tabla está vacía y hay datos maestros
             } else if (torniTableBody && torniMasterList.length === 0) {
                 // Si no hay datos maestros, loguear y quizás mostrar mensaje
                 console.warn("Lista maestra de items Torni está vacía. No se pueden añadir items.");
                 // Mostrar mensaje en el div de respuesta AJAX si no hay ya un mensaje de error/loading
                  if(responseMessageDiv && responseMessageDiv.textContent === "") {
                     responseMessageDiv.textContent = "Lista de productos Torni no cargada. La creación de ítems no es posible.";
                     responseMessageDiv.classList.add('warning');
                 }
             }


             // Asegurar que el botón de submit esté habilitado solo si hay datos maestros
             if(materialForm) {
                 const submitBtn = materialForm.querySelector('button[type="submit"]');
                 if (submitBtn) {
                     submitBtn.disabled = torniMasterList.length === 0; // Deshabilitar si la lista está vacía
                     if (torniMasterList.length === 0 && responseMessageDiv && responseMessageDiv.textContent === "") {
                          responseMessageDiv.textContent = "Lista de productos Torni no cargada. La creación de ítems no es posible.";
                          responseMessageDiv.classList.add('warning');
                     }
                 }
             }


        })
        .catch(error => {
            console.error("Error general al cargar datos JSON iniciales:", error);
            if(responseMessageDiv){
                 responseMessageDiv.textContent = `Error al cargar datos iniciales: ${error.message || 'Ver logs de consola.'}`;
                 responseMessageDiv.classList.add('error');
            }
             // Deshabilitar el formulario si faltan URLs o datos iniciales son críticos
            if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
        });
    } else {
         console.error("URLs para datos iniciales (JSON estáticos) no definidas (Items Torni).");
         if(responseMessageDiv){
              responseMessageDiv.textContent = `Error: URLs de datos iniciales no configuradas en la plantilla HTML.`;
              responseMessageDiv.classList.add('error');
         }
         if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
    }


    // --- Event Listeners ---
    // Los event listeners se añaden aquí
    // No necesitas listeners de dimensiones o dropdowns dependientes en este formulario.

    // Event listeners para botones de añadir/eliminar filas Torni (el botón añadir está en el HTML)
    if (addTorniItemBtn) { addTorniItemBtn.addEventListener('click', addTorniRow); }
     // Listener para botones de eliminar filas existentes al cargar (si las hubiera)
     if (torniTableBody) {
         torniTableBody.querySelectorAll('.delete-row-btn').forEach(btn => {
             btn.addEventListener('click', deleteTorniRow);
         });
     }

    setupFormSubmitListener(); // Configura el listener del submit

    // Establecer fecha por defecto inicialmente (siempre presente en campos comunes)
    if (fechaInput && !fechaInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        const month = ('0' + (today.getMonth() + 1)).slice(-2);
        const day = ('0' + today.getDate()).slice(-2);
        fechaInput.value = `${year}-${month}-${day}`;
    }

}); // Fin DOMContentLoaded