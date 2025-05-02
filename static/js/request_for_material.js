// static/js/request_for_material.js

// Este script asume que las siguientes variables globales se definen en la plantilla HTML
// antes de que este script se cargue, usando url_for:
// const STANDARD_DIMENSIONS_URL = "{{ url_for('static', filename='data/standard_dimensions_by_unit.json') }}";
// const TORNI_MASTERLIST_URL = "{{ url_for('static', filename='data/torni_items_masterlist.json') }}";


document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a elementos DOM ---
    const materialForm = document.getElementById('materialForm'); // ID del formulario principal
    // Elemento donde mostrar el feedback de la solicitud AJAX
    const responseMessageDiv = document.getElementById('response-message'); // Usa el ID del div para feedback AJAX

    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    const proveedorSelect = document.getElementById('proveedor');
    const materialSelect = document.getElementById('nombre_material');
    const tipoMaterialSelect = document.getElementById('tipo_material');
    const fechaInput = document.getElementById('fecha_solicitud');
    const unidadMedidaSelect = document.getElementById('unidad_medida');
    const dimensionDatalist = document.getElementById('dimensionList');
    const largoInput = document.getElementById('largo');
    const anchoInput = document.getElementById('ancho');
    const altoInput = document.getElementById('alto');
    const diametroInput = document.getElementById('diametro');
    const dimensionesContainer = document.getElementById('dimensiones-container');
    // --- Referencias a grupos estándar ---
    const cantidadUnidadGroup = document.getElementById('cantidad-unidad-group');
    const cantidadSolicitadaGroup = document.getElementById('cantidad-solicitada-group');
    const cantidadSolicitadaInput = document.getElementById('cantidad_solicitada');
    const unidadMedidaGroup = document.getElementById('unidad-medida-group');
    const nombreMaterialGroup = document.getElementById('nombre-material-group');
    const tipoMaterialGroup = document.getElementById('tipo-material-group');
    const standardFieldsContainer = document.getElementById('standard-fields-container'); // Contenedor de campos estándar

    // --- Referencias a elementos de Torni ---
    const torniTableContainer = document.getElementById('torni-table-container');
    const torniTableBody = document.getElementById('torni-items-tbody'); // Body de la tabla donde se añaden filas
    const addTorniItemBtn = document.getElementById('add-torni-item-btn'); // Botón para añadir fila Torni

    // --- Referencias Folio ---
    const folioDisplayValue = document.getElementById('folio-display-value');
    const folioInputHidden = document.getElementById('folio_solicitud');
    // --- Fin Referencias DOM ---


    // --- Variables Globales del Script ---
    let allStandardDimensions = {}; // Para dimensiones estándar (cargado de JSON)
    let torniMasterList = []; // Para lista maestra de items Torni (cargado de JSON)
    let currentFolio = null; // Para folio actual

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

    // --- Lógica Interdependiente de Dimensiones ---
    function handleDiameterLogic() { if (!largoInput || !anchoInput || !altoInput || !diametroInput) return; const largoValue = largoInput.value.trim(); const anchoValue = anchoInput.value.trim(); const altoValue = altoInput.value.trim(); if (largoValue && (anchoValue || altoValue)) { if (!anchoInput.disabled || !altoInput.disabled) { if (!diametroInput.disabled) { diametroInput.value = "N/A"; diametroInput.disabled = true; diametroInput.classList.add('na-field'); diametroInput.classList.remove('error-field'); } } } else { if (!anchoInput.disabled && !altoInput.disabled) { diametroInput.disabled = false; diametroInput.classList.remove('na-field'); if (diametroInput.value === "N/A") diametroInput.value = ""; } } }
    function handleWidthHeightLogic() { if (!anchoInput || !altoInput || !diametroInput) return; const diametroValue = diametroInput.value.trim(); if (diametroValue && diametroValue !== "N/A" && !diametroInput.disabled) { anchoInput.value = "N/A"; anchoInput.disabled = true; anchoInput.classList.add('na-field'); anchoInput.classList.remove('error-field'); altoInput.value = "N/A"; altoInput.disabled = true; altoInput.classList.add('na-field'); altoInput.classList.remove('error-field'); } else { if (!diametroInput.disabled || (diametroInput.disabled && diametroInput.value === "N/A")) { anchoInput.disabled = false; anchoInput.classList.remove('na-field'); if (anchoInput.value === "N/A") anchoInput.value = ""; altoInput.disabled = false; altoInput.classList.remove('na-field'); if (altoInput.value === "N/A") altoInput.value = ""; } } }
    function updateDimensionLogic() { handleWidthHeightLogic(); handleDiameterLogic(); }

    // --- Funciones de Datalist ---
    function populateDimensionDatalist(dimensionsArray) {
        if (!dimensionDatalist) return;
        if (dimensionsArray && Array.isArray(dimensionsArray)) {
            dimensionDatalist.innerHTML = '';
            dimensionsArray.forEach(dim => {
                const option = document.createElement('option');
                option.value = String(dim);
                dimensionDatalist.appendChild(option);
            });
            console.log(`Datalist poblado con ${dimensionsArray.length} opciones.`);
        } else {
            dimensionDatalist.innerHTML = '';
            console.log("Datalist limpiado.");
        }
    }

    function updateDatalistForUnit() {
        if (!unidadMedidaSelect || !allStandardDimensions) return;
        const selectedUnit = unidadMedidaSelect.value;
        const dimensionsForUnit = allStandardDimensions[selectedUnit] || [];
        populateDimensionDatalist(dimensionsForUnit);
    }

    // --- Lógica Modo Oscuro ---
     const applyMode = (mode) => { if (!darkModeToggle) return; if (mode === 'dark') { body.classList.add('dark-mode'); localStorage.setItem('darkMode', 'enabled'); darkModeToggle.textContent = '☀️'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo claro'); } else { body.classList.remove('dark-mode'); localStorage.setItem('darkMode', 'disabled'); darkModeToggle.textContent = '🌙'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo oscuro'); } };

    // --- Lógica Dropdowns Dependientes (Material/Tipo) ---
    const materialesPorProveedor = { "Mipsa": ["D2", "Cobre", "Aluminio"], "LBO": ["H13", "1018", "4140T"], "Grupo Collado": ["D2", "4140T", "H13", "1018", "Acetal"], "Cameisa": ["Aluminio", "Cobre", "Acetal", "Nylamid"], "Surcosa": ["1018", "Nylamid", "Acetal", "D2"], "Diace": ["D2", "H13", "Aluminio", "4140T", "Cobre", "1018"] };
    const tipoPorMaterial = { "D2": "Metal", "Aluminio": "Metal", "Cobre": "Metal", "4140T": "Metal", "H13": "Metal", "1018": "Metal", "Acetal": "Plastico", "Nylamid": "Plastico" };

    function actualizarMateriales() {
        if (!proveedorSelect || !materialSelect || !tipoMaterialSelect) return;
        const selectedProveedor = proveedorSelect.value;
        materialSelect.innerHTML = '<option value="" disabled selected>Seleccionar material:</option>';
        tipoMaterialSelect.value = "";
        tipoMaterialSelect.disabled = true;

        if (selectedProveedor && materialesPorProveedor[selectedProveedor]) {
            const materialesDisponibles = materialesPorProveedor[selectedProveedor];
            materialesDisponibles.forEach(material => {
                const option = document.createElement('option');
                option.value = material;
                option.textContent = material;
                materialSelect.appendChild(option);
            });
            materialSelect.disabled = false;
            actualizarTipoMaterial(); // Actualizar tipo basado en material por defecto (si hay)
        } else {
            materialSelect.disabled = true;
        }
    }

    function actualizarTipoMaterial() {
        if (!materialSelect || !tipoMaterialSelect) return;
        const selectedMaterial = materialSelect.value;
        if(selectedMaterial && tipoPorMaterial[selectedMaterial]) {
            const tipo = tipoPorMaterial[selectedMaterial];
            tipoMaterialSelect.value = tipo;
            tipoMaterialSelect.disabled = false; // Opcional: mantener deshabilitado si el tipo no es editable
        } else {
            tipoMaterialSelect.value = "";
            tipoMaterialSelect.disabled = true;
        }
    }

    // --- Lógica Tabla Torni (con Awesomplete) ---
    function addTorniRow() {
        if (!torniTableBody) return;
        console.log("Intentando añadir fila Torni...");
        const rowId = Date.now() + Math.random().toString(36).substring(2, 5); // ID simple para la fila
        const newRow = torniTableBody.insertRow();
        newRow.setAttribute('data-row-id', rowId);

        newRow.innerHTML = `
            <td><input type="number" class="torni-qty" name="quantity" min="1" value="1" required></td>
            <td><input type="text" class="torni-id" name="id" readonly></td>
            <td><input type="text" class="torni-desc" name="description" placeholder="Escribe para buscar..." required autocomplete="off"></td>
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
                 list: torniMasterList, // Pasar el ARRAY COMPLETO de objetos
                 data: function (item, input) { // Trabajar con objetos { id, description }
                     console.log("Awesomplete 'data' function - input item:", item);
                     let html = item.description.replace(new RegExp(Awesomplete.$.regExpEscape(input.trim()), "gi"), "<mark>$&</mark>");
                     return { label: html, value: item.description, original: item, id: item.id }; // <<< Incluir 'original' Y 'id' explícitamente
                 },
                 item: function (data, input) { // Recibe el objeto {label, value, original, id}
                      return Awesomplete.ITEM(data.label, input);
                 },
                 replace: function(suggestion) { // Recibe el objeto {label, value, original, id}
                     console.log("Awesomplete 'replace' function - suggestion:", suggestion);
                     this.input.value = suggestion.value;
                 },
                 minChars: 1, maxItems: 10, autoFirst: true,
                 filter: function(item, input) { // Custom filter por descripción (case-insensitive, trim)
                    // item aquí es el objeto retornado por la función 'data': {label, value, original, id}
                    // Asegúrate de que la propiedad a filtrar es 'value' (la descripción)
                    return item.value.trim().toLowerCase().includes(input.trim().toLowerCase());
                 }
             });

             // --- Listener para cuando se SELECCIONA un item ---
             descInput.addEventListener('awesomplete-selectcomplete', function(event) {
                console.log("--- Awesomplete Selección Completa (DEBUG) ---");
                console.log("Contenido completo de event.text:", event.text); // {label: ..., value: ...}

                // El valor seleccionado por Awesomplete (la descripción)
                const selectedValueFromAwesomplete = event.text.value;

                // Limpiar y normalizar el valor seleccionado (quitar espacios, mayúsculas, posibles saltos de línea)
                const normalizedSelectedValue = selectedValueFromAwesomplete.trim().toLowerCase().replace(/[\r\n]/g, ''); // <<< CORREGIDO

                // Intentar encontrar el objeto original en la lista maestra
                // Asegúrate de que la comparación en find() también normaliza la descripción del item maestro
                const selectedItemData = torniMasterList.find(item => {
                    if (item && typeof item.description === 'string') {
                        const normalizedItemDescription = item.description.trim().toLowerCase().replace(/[\r\n]/g, '');
                        console.log(`Comparando "${normalizedSelectedValue}" con item "${item.id}": "${normalizedItemDescription}" -> ${normalizedSelectedValue === normalizedItemDescription}`); // Log de comparación
                        return normalizedItemDescription === normalizedSelectedValue;
                    }
                    return false;
                });

                console.log("Objeto original encontrado en lista maestra:", selectedItemData); // LOGUEA ESTO (DEBERÍA SER EL OBJETO {id, description})


                // Buscar el input ID en la misma fila
                const currentRow = this.closest('tr');
                const idInputInRow = currentRow ? currentRow.querySelector('.torni-id') : null;

                // Actualizar el input ID usando el ID del objeto encontrado
                if (idInputInRow && selectedItemData && selectedItemData.id) { // Verifica que selectedItemData existe Y tiene propiedad .id
                    console.log(`Actualizando ID para fila con ID ${currentRow.getAttribute('data-row-id')}:`, selectedItemData.id);
                    idInputInRow.value = selectedItemData.id.trim();
                    idInputInRow.classList.remove('error-field');
                    this.classList.remove('error-field'); // Limpiar error visual en descripción si se encontró el ID
                } else if (idInputInRow) {
                     idInputInRow.value = ''; // Limpiar si no se encontró el objeto o no tiene ID
                     console.warn(`Fila con ID ${currentRow.getAttribute('data-row-id')}: No se pudo determinar el ID en lista maestra para "${selectedValueFromAwesomplete}". Limpiando campo ID.`, selectedItemData);
                      // Marcar error visual en el campo de descripción si no se encontró coincidencia exacta en la lista maestra
                     this.classList.add('error-field');
                } else {
                     console.error(`Fila con ID ${currentRow.getAttribute('data-row-id')}: No se pudo encontrar el campo ID en la fila para actualizar.`);
                }
            });

             // --- Limpiar ID si se borra/cambia descripción manualmente ---
             descInput.addEventListener('input', function() {
                 const currentDesc = this.value.trim();
                 const idInputInRow = this.closest('tr').querySelector('.torni-id');

                 // Para evitar limpiar el ID si el usuario solo borra y vuelve a escribir la descripción correcta
                 // Solo limpiamos el ID si la descripción está vacía
                 if (idInputInRow && currentDesc === '') {
                     idInputInRow.value = ''; // Borrar ID si la descripción está vacía
                 }
                 // Opcional: Lógica más compleja para verificar si la descripción actual coincide con algún item en la lista maestra
                 // (similar a la lógica find() en selectcomplete, pero más pesada)
                 // Por ahora, limpiar solo si la descripción está vacía es suficiente.
             });


        } else {
             if (typeof Awesomplete === 'undefined') console.error("¡Awesomplete NO está definido! Revisa la carga del script.");
             if (!torniMasterList || torniMasterList.length === 0) console.warn("torniMasterList está vacía o no cargada. No se puede inicializar Awesomplete para sugerencias.");
             if (!descInput) console.error("Input de descripción (.torni-desc) no encontrado en la nueva fila.");
             if (!idInput) console.error("Input de ID (.torni-id) no encontrado en la nueva fila.");
        }
         return newRow;
    } // Fin addTorniRow

    function deleteTorniRow(event) {
        if (!torniTableBody) return;
        const button = event.target;
        const row = button.closest('tr');
        if (row) {
            row.remove();
        }
        // No añadir una fila vacía por defecto aquí, la lógica handleProveedorChange lo maneja al inicio.
    }


    // --- Lógica de UI basada en Proveedor ---
     function handleProveedorChange() {
        if (!proveedorSelect || !dimensionesContainer || !torniTableContainer ||
            !cantidadUnidadGroup || !cantidadSolicitadaGroup || !nombreMaterialGroup || !tipoMaterialGroup || !materialForm || !standardFieldsContainer) { console.error("Faltan elementos DOM para control de UI."); return; }

        const selectedProveedor = proveedorSelect.value;
        const esTorni = selectedProveedor === 'Torni';

        // Mostrar/Ocultar secciones y limpiar errores visuales
        const allInputSelects = materialForm.querySelectorAll('input, select, textarea');
        allInputSelects.forEach(el => el.classList.remove('error-field'));
         if (responseMessageDiv) { // Limpiar div de respuesta AJAX
             responseMessageDiv.textContent = '';
             responseMessageDiv.classList.remove('processing', 'success', 'error');
         }

        // Ocultar/mostrar contenedores principales
        dimensionesContainer.classList.toggle('oculto', esTorni);
        torniTableContainer.classList.toggle('oculto', !esTorni);
        standardFieldsContainer.classList.toggle('oculto', esTorni);


        // Habilitar/Deshabilitar inputs y limpiar valores/estado según sección visible
        allInputSelects.forEach(el => {
            const isTorniInput = el.closest('#torni-items-table');
            const isStandardInput = el.closest('#standard-fields-container');
            const isCommonInput = el.id === 'nombre_solicitante' || el.id === 'proyecto' || el.id === 'fecha_solicitud' || el.id === 'departamento_area' || el.id === 'proveedor' || el.id === 'especificaciones_adicionales' || el.id === 'folio_solicitud';

            if (isCommonInput) {
                 el.disabled = false; // Campos comunes siempre habilitados
            } else if (isTorniInput) {
                 el.disabled = !esTorni; // Campos Torni habilitados solo en modo Torni
            } else if (isStandardInput) {
                 el.disabled = esTorni; // Campos estándar habilitados solo en modo estándar
            } else {
                 // Otros campos no identificados, quizás deshabilitarlos por defecto si no son comunes
                 el.disabled = true;
            }

            // Limpiar valor del input si ha sido deshabilitado por el cambio de proveedor
             // o si es un campo específico que debe resetearse
            if (el.disabled) {
                 el.value = ''; // Limpiar el valor si el campo está deshabilitado
            } else {
                 // Lógica específica de limpieza para campos habilitados
                 if (el.id === 'cantidad_solicitada' && el.value === '') el.value = '1'; // Default 1 para cantidad solicitada estándar si se habilita y está vacío
                 // Puedes añadir otros defaults si es necesario
            }

        });

        // Lógicas específicas después de habilitar/deshabilitar y limpiar
        if (esTorni) {
            // Si es Torni, asegurar que la tabla tiene al menos una fila si hay datos maestros
            if (torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) { addTorniRow(); }
             // Limpiar la tabla Torni si NO hay datos maestros (para evitar añadir filas vacías)
             if (torniTableBody && torniMasterList.length === 0) { torniTableBody.innerHTML = '';}

        } else { // No es Torni (Proveedor estándar)
            // Limpiar filas de la tabla Torni (si había alguna)
             if (torniTableBody){ torniTableBody.innerHTML = ''; }

             // Recargar dropdowns dependientes para campos estándar
             if (proveedorSelect) { actualizarMateriales(); }
             updateDatalistForUnit(); // Asegura que datalist se pobla para la unidad seleccionada

            // Actualizar lógicas de dimensiones si aplica
            updateDimensionLogic();
        }

     }


    // --- Función para Recolectar TODOS los Datos del Formulario en un Objeto JavaScript (JSON Structure) ---
    // ESTA FUNCIÓN FALTABA O ESTABA INCOMPLETA EN EL CÓDIGO ANTERIOR.
    function collectFormData() {
        const data = {};
        const form = materialForm;

        // Recolectar campos comunes y estándar (solo si están habilitados)
        form.querySelectorAll('input, select, textarea').forEach(input => {
             // No recolectar inputs dentro de la tabla torni en este bucle principal
             if (input.closest('#torni-items-table')) {
                  return; // Saltar este input
             }

             if (input.name && !input.disabled) {
                  if (input.type === 'number') {
                       data[input.name] = parseFloat(input.value) || 0; // Default a 0 si no es número válido
                  } else if (input.type === 'checkbox') {
                      data[input.name] = input.checked;
                  } else {
                       // Para campos de texto como dimensiones o texto general
                       // Solo incluir si tienen un valor no vacío
                       if (input.value.trim()) {
                           data[input.name] = input.value.trim();
                       }
                       // Si el campo está vacío, simplemente no se añade al objeto data
                   }
             }
        });

        const selectedProvider = proveedorSelect ? proveedorSelect.value : null;

        // Recolectar items Torni si es el proveedor seleccionado
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
                         // Marcar visualmente los campos si son inválidos en la recolección (opcional, la validación de submit ya lo hace)
                         if (!(quantityValue > 0)) qtyInput.classList.add('error-field');
                         if (idValue === '') idInput.classList.add('error-field');
                         if (descValue === '') descInput.classList.add('error-field');
                    }
                } else {
                    console.error("Fila Torni sin todos los campos esperados encontrada en recolección.");
                }
            });
            data['torni_items'] = torniItems; // Añadir el array al objeto principal
        }

        console.log('Datos recolectados para JSON:', data);
        return data;
    }


    // --- Función para Configurar el Envío del Formulario (Fetch API) ---
    function setupFormSubmitListener() {
        if (!materialForm) {
             console.error("Formulario #materialForm no encontrado.");
             if(responseMessageDiv){
                  responseMessageDiv.textContent = `Error interno: Formulario principal no encontrado.`;
                  responseMessageDiv.classList.add('error');
             }
             return;
        }

       materialForm.addEventListener('submit', function(event) {
           event.preventDefault();

           const form = event.target;

           // 1. Validación (Llama a collectFormData para ayudar a validar y obtener datos)
           // Ya no necesitamos hacer toda la validación aquí si collectFormData lo hace y loguea advertencias.
           // Pero es bueno validar campos comunes y al menos si hay items Torni válidos.
           // Vamos a simplificar esta parte para no duplicar validación de items Torni.

           // Limpiar errores visuales y mensajes anteriores
            form.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
            if (responseMessageDiv) {
                 responseMessageDiv.textContent = '';
                 responseMessageDiv.classList.remove('processing', 'success', 'error');
            }

           const selectedProvider = proveedorSelect ? proveedorSelect.value : null;
           const datosSolicitud = collectFormData(); // Recolectar datos Y validar items Torni si aplica

           let isValid = true;
           const errores = [];

           // Validar campos comunes requeridos
           const camposComunesReq = ['nombre_solicitante', 'fecha_solicitud', 'proveedor', 'departamento_area', 'proyecto'];
           camposComunesReq.forEach(id => {
               const campo = form.querySelector(`#${id}`);
               if (campo && campo.required && !campo.disabled && !campo.value.trim()) {
                   isValid = false;
                   const label = form.querySelector(`label[for="${id}"]`);
                   const nombreCampo = label ? label.textContent.replace(':', '').trim() : (campo.placeholder || campo.name || id);
                   errores.push(`"${nombreCampo}" obligatorio.`);
                   campo.classList.add('error-field');
                } // Limpiar errores ya se hizo al inicio
           });

           // Validar si es modo Torni y NO se recolectó ningún item Torni válido
           if (selectedProvider === 'Torni') {
                const torniItemsRecogidos = datosSolicitud.torni_items || [];
                if (torniItemsRecogidos.length === 0) {
                    isValid = false;
                    errores.push("Debe añadir al menos un producto con cantidad, ID y descripción para proveedor Torni.");
                    // Opcional: Marcar la tabla como error visual
                    if(torniTableContainer) torniTableContainer.classList.add('error-field');
                } else {
                    if(torniTableContainer) torniTableContainer.classList.remove('error-field');
                }
           } else if (selectedProvider && selectedProvider !== '') { // Proveedor estándar seleccionado
                // Validar si es modo estándar y la cantidad solicitada es inválida/faltante
                // La lógica de collectFormData ya salta items inválidos, pero aquí validamos el campo principal
                 const cantidadInput = form.querySelector('#cantidad_solicitada');
                 if (cantidadInput && !cantidadInput.disabled) {
                     const valorCampo = cantidadInput.value.trim();
                     if (!valorCampo || parseFloat(valorCampo) <= 0 || isNaN(parseFloat(valorCampo))) {
                          isValid = false; errores.push(`"Cantidad Solicitada" > 0.`); cantidadInput.classList.add('error-field');
                     } // Limpiar errores ya se hizo al inicio
                 }
                // Puedes añadir validación para otros campos estándar requeridos aquí si es necesario
                // (ej: nombre material, unidad medida si no son Torni)
           }


           // 2. Si hay errores de validación general, mostrar y detener
           if (!isValid) {
                console.log("Validación general fallida en frontend:", errores);
                const uniqueErrors = [...new Set(errores)];
                if (responseMessageDiv) {
                    responseMessageDiv.innerHTML = "Por favor, corrige los errores:<br>" + uniqueErrors.join('<br>');
                    responseMessageDiv.classList.add('error');
                }
                const primerErrorField = form.querySelector('.error-field:not(:disabled)');
                if(primerErrorField) primerErrorField.focus();
                return;
           }
           // --- Fin Validación General ---


           // 3. Si la validación general fue exitosa, proceder con el fetch
           console.log('Validación general exitosa. Datos del formulario a enviar:', datosSolicitud);

           // Mostrar estado de procesamiento ANTES del fetch
           if (responseMessageDiv) {
                responseMessageDiv.textContent = 'Enviando solicitud...';
                responseMessageDiv.classList.remove('error', 'success');
                responseMessageDiv.classList.add('processing');
            }

           fetch(form.action, {
               method: form.method,
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
                   // Resetear UI a estado inicial (basado en proveedor por defecto o el que quedó)
                   handleProveedorChange(); // Esto limpia campos y restablece la tabla Torni si es necesario

                   // Asegurar que la fecha actual se restablece (si no se resetea con form.reset)
                    if(fechaInput && !fechaInput.value) { // Solo si está vacío después del reset
                        const today = new Date();
                        const year = today.getFullYear();
                        const month = ('0' + (today.getMonth() + 1)).slice(-2);
                        const day = ('0' + today.getDate()).slice(-2);
                        fechaInput.value = `${year}-${month}-${day}`;
                   }
                   // Limpiar la tabla Torni si no se limpió en handleProveedorChange
                   if (torniTableBody && proveedorSelect && proveedorSelect.value !== 'Torni') {
                        torniTableBody.innerHTML = '';
                   }
                   // Asegurar una fila Torni si el proveedor es Torni después del reset
                   if (proveedorSelect && proveedorSelect.value === 'Torni' && torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
                        addTorniRow();
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
       }); // Fin submit listener


   }


    // --- ** CÓDIGO QUE SE EJECUTA AL CARGAR LA PÁGINA (LLAMA A FUNCIONES) ** ---

    // Generar y Mostrar Folio Inicial al Cargar (solo si no hay uno ya puesto)
    if (!folioInputHidden || !folioInputHidden.value) {
        currentFolio = generateFolio();
        updateFolioDisplay(currentFolio);
        console.log("Folio inicial generado:", currentFolio);
    } else {
         currentFolio = folioInputHidden.value;
         console.log("Folio existente cargado:", currentFolio);
    }

    // Deshabilitar el botón de submit inicialmente hasta que los datos se carguen (si es necesario)
    // if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true; # Ya lo haces más abajo


    // Carga de Datos (LLAMA A fetch, que en su .then llama a funciones para inicializar UI)
    if (typeof STANDARD_DIMENSIONS_URL !== 'undefined' && typeof TORNI_MASTERLIST_URL !== 'undefined') {
        Promise.all([
            fetch(STANDARD_DIMENSIONS_URL).then(res => {
                 if (!res.ok) throw new Error(`Dimensiones: ${res.status} ${res.statusText}`);
                 return res.json();
             }).catch(error => { console.error("Error en fetch de Dimensiones:", error); throw error; }),
            fetch(TORNI_MASTERLIST_URL).then(res => {
                 if (!res.ok) throw new Error(`Items Torni: ${res.status} ${res.statusText}`);
                 return res.json();
             }).catch(error => { console.error("Error en fetch de Items Torni:", error); throw error; })
        ])
        .then(([dimensionsData, torniData]) => {
            console.log("Datos iniciales cargados con éxito.");
            allStandardDimensions = dimensionsData;
            torniMasterList = torniData || [];
            console.log("Contenido de torniMasterList:", torniMasterList); // LOGUEA EL CONTENIDO

            // --- Llamadas a funciones para inicializar la UI *después* de cargar los datos ---
            updateDatalistForUnit();
            handleProveedorChange(); // Esto configura la UI inicial y puede añadir la fila Torni si es el proveedor por defecto

             // Asegurar que el botón de submit esté habilitado si los datos cargaron correctamente y el formulario existe
             if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = false;

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
         console.error("URLs para datos iniciales (JSON estáticos) no definidas. Asegura que STANDARD_DIMENSIONS_URL y TORNI_MASTERLIST_URL están definidas en la plantilla HTML antes de cargar request_for_material.js.");
         if(responseMessageDiv){
              responseMessageDiv.textContent = `Error: URLs de datos iniciales no configuradas en la plantilla HTML.`;
              responseMessageDiv.classList.add('error');
         }
         // Deshabilitar el formulario si faltan URLs
         if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
    }


    // --- Event Listeners (Añadirlos después de definir las funciones) ---
    // Los event listeners se añaden aquí
    if(largoInput) largoInput.addEventListener('input', updateDimensionLogic);
    if(anchoInput) anchoInput.addEventListener('input', updateDimensionLogic);
    if(altoInput) altoInput.addEventListener('input', updateDimensionLogic);
    if(diametroInput) diametroInput.addEventListener('input', updateDimensionLogic);

    if (unidadMedidaSelect) { unidadMedidaSelect.addEventListener('change', updateDatalistForUnit); }

    if (proveedorSelect) { proveedorSelect.addEventListener('change', handleProveedorChange); }
    if (materialSelect) { materialSelect.addEventListener('change', actualizarTipoMaterial); }

    if (addTorniItemBtn) { addTorniItemBtn.addEventListener('click', addTorniRow); }
    if (torniTableBody) {
         torniTableBody.querySelectorAll('.delete-row-btn').forEach(btn => {
             btn.addEventListener('click', deleteTorniRow);
         });
     }

    setupFormSubmitListener(); // Configura el listener del submit

    // Establecer fecha por defecto si no está puesta inicialmente
    if (fechaInput && !fechaInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        const month = ('0' + (today.getMonth() + 1)).slice(-2);
        const day = ('0' + today.getDate()).slice(-2);
        fechaInput.value = `${year}-${month}-${day}`;
    }

}); // Fin DOMContentLoaded