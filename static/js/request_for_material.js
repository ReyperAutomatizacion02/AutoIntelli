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

    // --- ** DEFINICIÓN DE FUNCIONES (MOVER AQUÍ ARRIBA) ** ---

    // --- Funciones de Folio ---
    function generateFolio() {
        const timestamp = Date.now();
        const randomPart = Math.random().toString(36).substring(2, 8).toUpperCase();
        // Usar un prefijo diferente si es necesario, por ejemplo "MAT"
        return `MAT-${timestamp}-${randomPart}`;
    }

    function updateFolioDisplay(folio) {
        if (folioDisplayValue) folioDisplayValue.textContent = folio;
        if (folioInputHidden) folioInputHidden.value = folio;
    }

    // --- Lógica Interdependiente de Dimensiones ---
    // Asegurarse de que los inputs de dimensiones existen antes de añadir listeners
    function handleDiameterLogic() { if (!largoInput || !anchoInput || !altoInput || !diametroInput) return; const largoValue = largoInput.value.trim(); const anchoValue = anchoInput.value.trim(); const altoValue = altoInput.value.trim(); if (largoValue && (anchoValue || altoValue)) { if (!anchoInput.disabled || !altoInput.disabled) { if (!diametroInput.disabled) { diametroInput.value = "N/A"; diametroInput.disabled = true; diametroInput.classList.add('na-field'); diametroInput.classList.remove('error-field'); } } } else { if (!anchoInput.disabled && !altoInput.disabled) { diametroInput.disabled = false; diametroInput.classList.remove('na-field'); if (diametroInput.value === "N/A") diametroInput.value = ""; } } }
    function handleWidthHeightLogic() { if (!anchoInput || !altoInput || !diametroInput) return; const diametroValue = diametroInput.value.trim(); if (diametroValue && diametroValue !== "N/A" && !diametroInput.disabled) { anchoInput.value = "N/A"; anchoInput.disabled = true; anchoInput.classList.add('na-field'); anchoInput.classList.remove('error-field'); altoInput.value = "N/A"; altoInput.disabled = true; altoInput.classList.add('na-field'); altoInput.classList.remove('error-field'); } else { if (!diametroInput.disabled || (diametroInput.disabled && diametroInput.value === "N/A")) { anchoInput.disabled = false; anchoInput.classList.remove('na-field'); if (anchoInput.value === "N/A") anchoInput.value = ""; altoInput.disabled = false; altoInput.classList.remove('na-field'); if (altoInput.value === "N/A") altoInput.value = ""; } } }
    function updateDimensionLogic() { handleWidthHeightLogic(); handleDiameterLogic(); }
    // Los event listeners para los inputs de dimensiones se añaden al final del script dentro del DOMContentLoaded


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
     // El event listener para el select de unidad se añade al final del script


    // --- Lógica Modo Oscuro ---
     const applyMode = (mode) => { if (!darkModeToggle) return; if (mode === 'dark') { body.classList.add('dark-mode'); localStorage.setItem('darkMode', 'enabled'); darkModeToggle.textContent = '☀️'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo claro'); } else { body.classList.remove('dark-mode'); localStorage.setItem('darkMode', 'disabled'); darkModeToggle.textContent = '🌙'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo oscuro'); } };
    // El event listener para el toggle se añade al final del script


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
    // Los event listeners para proveedor y material se añaden al final del script


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
                     let html = item.description.replace(new RegExp(Awesomplete.$.regExpEscape(input.trim()), "gi"), "<mark>$&</mark>");
                     return { label: html, value: item.description, original: item }; // Incluir 'original'
                 },
                 item: function (data, input) { // Recibe el objeto {label, value, original}
                      return Awesomplete.ITEM(data.label, input); // Usar data.label (el HTML)
                 },
                 replace: function(suggestion) { // Recibe el objeto {label, value, original}
                     this.input.value = suggestion.value; // Usar suggestion.value (la descripción)
                 },
                 minChars: 1, maxItems: 10, autoFirst: true,
                 filter: function(item, input) { // Custom filter por descripción (case-insensitive, trim)
                    return item.value.trim().toLowerCase().includes(input.trim().toLowerCase());
                 }
             });

             // --- Listener para cuando se SELECCIONA un item ---
             descInput.addEventListener('awesomplete-selectcomplete', function(event) {
                const selectedItemData = event.text.original; // Objeto item maestro seleccionado
                console.log("--- Awesomplete Selección Completa ---");
                console.log("Objeto de item maestro seleccionado:", selectedItemData);

                // Buscar el input ID en la misma fila
                const currentRow = this.closest('tr'); // 'this' es el input descInput
                const idInputInRow = currentRow ? currentRow.querySelector('.torni-id') : null;

                // Actualizar el input ID
                if (idInputInRow && selectedItemData && selectedItemData.id) {
                    console.log(`Actualizando ID para fila con ID ${rowId}:`, selectedItemData.id);
                    idInputInRow.value = selectedItemData.id.trim();
                    idInputInRow.classList.remove('error-field');
                    this.classList.remove('error-field'); // Limpiar error visual en descripción
                } else if (idInputInRow) {
                     idInputInRow.value = '';
                     console.warn(`Fila con ID ${rowId}: Objeto seleccionado no tiene ID o es inválido. Limpiando campo ID.`, selectedItemData);
                } else {
                     console.error(`Fila con ID ${rowId}: No se pudo encontrar el campo ID en la fila para actualizar.`);
                }
            });

             // --- Limpiar ID si se borra/cambia descripción manualmente ---
             descInput.addEventListener('input', function() {
                 const currentDesc = this.value.trim(); // 'this' es el input descInput
                 const idInputInRow = this.closest('tr').querySelector('.torni-id'); // Obtener ID input en la misma fila

                 // Buscar si el texto actual coincide EXACTAMENTE con una descripción en la lista de sugerencias actual
                 const awesompleteInstance = this.awesomplete; // Obtener la instancia Awesomplete asociada
                 const awesompleteItemMatch = awesompleteInstance ? awesompleteInstance.list.find(item => item.value.trim() === currentDesc) : null;


                 if (idInputInRow && (!awesompleteItemMatch || idInputInRow.value.trim() !== awesompleteItemMatch.original.id.trim())) {
                     // Si no hay coincidencia exacta en la lista de sugerencias actual
                     // O si hay coincidencia pero el ID actual en el input no coincide con el ID de la sugerencia encontrada
                      idInputInRow.value = ''; // Borrar ID
                 }
             });


        } else {
             if (typeof Awesomplete === 'undefined') console.error("¡Awesomplete NO está definido! Revisa la carga del script.");
             if (!torniMasterList || torniMasterList.length === 0) console.warn("torniMasterList está vacía o no cargada. No se puede inicializar Awesomplete para sugerencias.");
             if (!descInput) console.error("Input de descripción (.torni-desc) no encontrado en la nueva fila.");
             if (!idInput) console.error("Input de ID (.torni-id) no encontrado en la nueva fila.");
        }
         return newRow; // Opcional: devolver la fila creada
    } // Fin addTorniRow

    function deleteTorniRow(event) {
        if (!torniTableBody) return;
        const button = event.target;
        const row = button.closest('tr');
        if (row) {
            row.remove();
            // Opcional: Añadir una fila vacía si la tabla queda vacía después de eliminar
            // if (torniTableBody.rows.length === 0 && proveedorSelect && proveedorSelect.value === 'Torni') { addTorniRow(); }
        }
    }
    // Los event listeners para añadir/eliminar filas se añaden al final del script


    // --- Lógica de UI basada en Proveedor ---
     function handleProveedorChange() {
        if (!proveedorSelect || !dimensionesContainer || !torniTableContainer ||
            !cantidadUnidadGroup || !cantidadSolicitadaGroup || !nombreMaterialGroup || !tipoMaterialGroup || !materialForm || !standardFieldsContainer) { console.error("Faltan elementos DOM para control de UI."); return; }

        const selectedProveedor = proveedorSelect.value;
        const esTorni = selectedProveedor === 'Torni';

        // Mostrar/Ocultar secciones y limpiar errores visuales
        const allInputSelects = materialForm.querySelectorAll('input, select, textarea');
        allInputSelects.forEach(el => el.classList.remove('error-field')); // Limpiar errores visuales
         if (responseMessageDiv) { // Limpiar div de respuesta AJAX
             responseMessageDiv.textContent = '';
             responseMessageDiv.classList.remove('processing', 'success', 'error');
         }


        dimensionesContainer.classList.toggle('oculto', esTorni);
        torniTableContainer.classList.toggle('oculto', !esTorni);
        standardFieldsContainer.classList.toggle('oculto', esTorni); // Ocultar/mostrar el contenedor completo de campos estándar

        // Habilitar/Deshabilitar inputs según sección visible y limpiar valores/estado
        allInputSelects.forEach(el => {
            // Campos siempre habilitados (comunes)
            if (el.id === 'nombre_solicitante' || el.id === 'proyecto' || el.id === 'fecha_solicitud' ||
                el.id === 'departamento_area' || el.id === 'proveedor' || el.id === 'especificaciones_adicionales' || el.id === 'folio_solicitud') {
                 el.disabled = false;
                 // Requeridos excepto especificaciones (usar el atributo required en el HTML)
                 // el.required = (el.id !== 'especificaciones_adicionales');
            }
            // Campos de Torni (inputs dentro de la tabla Torni)
            else if (el.closest('#torni-items-table')) {
                el.disabled = !esTorni; // Habilitar si es Torni, deshabilitar si no
                // El estado 'required' para los inputs Torni se maneja en la validación JS, no en el HTML disabled/required
            }
            // Campos estándar (inputs/selects dentro del contenedor de campos estándar)
            else if (el.closest('#standard-fields-container')) {
                 el.disabled = esTorni; // Habilitar si NO es Torni, deshabilitar si es
                 // El estado 'required' para los campos estándar se maneja en la validación JS, no en el HTML disabled/required
            }
            // Otros campos (si los hay fuera de estas secciones)
            // ...
        });


        // Lógicas específicas después de habilitar/deshabilitar y limpiar errores/estado
        if (esTorni) {
            // Si es Torni, asegurar que la tabla tiene al menos una fila
            if (torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) { addTorniRow(); } // Solo añadir si hay datos maestros para Awesomplete
             // Limpiar valores de campos estándar (si no se borran con disabled)
             if (cantidadSolicitadaInput) cantidadSolicitadaInput.value = '1';
             if (unidadMedidaSelect) unidadMedidaSelect.value = '';
             if (materialSelect) materialSelect.value = '';
             if (tipoMaterialSelect) tipoMaterialSelect.value = '';
             if (largoInput) largoInput.value = ''; if (anchoInput) anchoInput.value = ''; if (altoInput) altoInput.value = ''; if (diametroInput) diametroInput.value = '';

             // Deshabilitar los selects de material y tipo en modo Torni (se hace arriba, pero re-confirmar)
             if (materialSelect) { materialSelect.disabled = true; }
             if (tipoMaterialSelect) { tipoMaterialSelect.disabled = true; }

        } else { // No es Torni (Proveedor estándar)
            // Limpiar filas de la tabla Torni (si había alguna)
             if (torniTableBody){ torniTableBody.innerHTML = ''; }

             // Habilitar selects dependientes si aplica
             if (proveedorSelect) { actualizarMateriales(); } // Recargar materiales según el proveedor seleccionado
             // Asegurar que la unidad de medida no es N/A por defecto en modo estándar
             if (unidadMedidaSelect && unidadMedidaSelect.value === 'N/A') { unidadMedidaSelect.value = ''; } // O establecer un valor por defecto válido

            // Actualizar lógicas dependientes
            updateDimensionLogic(); // Asegura que las reglas de dimensiones se aplican al estado inicial
            updateDatalistForUnit(); // Asegura que datalist se pobla para la unidad seleccionada
        }

     } // Fin handleProveedorChange
     // El event listener para proveedor se añade al final del script


    // --- Función para Recolectar TODOS los Datos del Formulario en un Objeto JavaScript (JSON Structure) ---
    // Esto es crucial para enviar JSON al backend que espera request.get_json()
    function collectFormData() {
        const data = {};
        const form = materialForm; // Usa la referencia al formulario

        // Recolectar campos comunes y estándar (si no están deshabilitados)
        // Usa el atributo 'name' para identificar los campos
        form.querySelectorAll('input, select, textarea').forEach(input => {
             // No recolectar inputs dentro de la tabla torni en este bucle principal
             // O si un campo está deshabilitado (ya lo hace el check input.name && !input.disabled)
             // Pero vamos a asegurarnos de no recolectar campos Torni aquí explícitamente
             if (input.closest('#torni-items-table')) {
                  return; // Saltar este input, se maneja en la lógica de Torni
             }

             if (input.name && !input.disabled) { // Solo recolectar campos con nombre y habilitados
                  if (input.type === 'number') {
                       // Parsear a float, default 0 si no es un número válido
                       data[input.name] = parseFloat(input.value) || 0;
                  } else if (input.type === 'checkbox') {
                      data[input.name] = input.checked;
                  }
                   else if (['largo', 'ancho', 'alto', 'diametro'].includes(input.name)) {
                      // Dimensiones: Si no están vacías, recolectarlas como string.
                      if (input.value.trim()) {
                           data[input.name] = input.value.trim();
                      }
                      // Si están vacías u opcionales, simplemente no las añadimos al objeto JSON
                   }
                  else {
                       data[input.name] = input.value.trim();
                  }
             }
        });

        const selectedProvider = proveedorSelect ? proveedorSelect.value : null;

        // Recolectar items Torni si es el proveedor seleccionado
        if (selectedProvider === 'Torni' && torniTableBody) {
            const torniItems = [];
            // Iterar sobre las filas DEL BODY de la tabla
            torniTableBody.querySelectorAll('tr').forEach(row => {
                const qtyInput = row.querySelector('.torni-qty');
                const idInput = row.querySelector('.torni-id');
                const descInput = row.querySelector('.torni-desc');

                // Solo añadir item si los campos esenciales (cantidad, ID, descripción) tienen valor
                // La validación ya verificó si son obligatorios y válidos antes.
                if (qtyInput && idInput && descInput) {
                     const quantityValue = parseInt(qtyInput.value, 10); // Parsear a entero para cantidad Torni
                    // Solo añadir si la cantidad es válida (>0) y la descripción/ID no están vacíos
                    if (quantityValue > 0 && idInput.value.trim() && descInput.value.trim()) {
                         torniItems.push({
                             quantity: quantityValue,
                             id: idInput.value.trim(),
                             description: descInput.value.trim()
                         });
                    } else {
                         // Esto no debería pasar si la validación frontend funciona, pero loguear advertencia
                         console.warn("Saltando item Torni inválido o incompleto en recolección:", {
                              qty: qtyInput ? qtyInput.value : null,
                              id: idInput ? idInput.value : null,
                              desc: descInput ? descInput.value : null
                         });
                    }
                } else {
                     console.warn("Fila Torni sin todos los campos esperados encontrada en recolección.");
                }
            });
            data['torni_items'] = torniItems; // Añadir el array al objeto principal con la clave esperada por el backend
        }

        console.log('Datos recolectados para JSON:', data);
        return data; // Retorna el objeto con todos los datos para enviar como JSON
    }


    // --- Función para Configurar el Envío del Formulario (Fetch API) ---
    // Esta función contiene el listener del submit del formulario
    function setupFormSubmitListener() {
        // materialForm ya está definida en el ámbito superior
        if (!materialForm) {
             console.error("Formulario #materialForm no encontrado. No se pudo configurar el listener de submit.");
             if(responseMessageDiv){
                  responseMessageDiv.textContent = `Error interno: Formulario principal no encontrado.`;
                  responseMessageDiv.classList.add('error');
             }
             // if (materialForm) materialForm.querySelector('button[type="submit"]').disabled = true; // No puedes usar materialForm.querySelector si materialForm es null
             return; // Salir si el formulario no existe
        }

       // Listener para el evento submit del formulario #materialForm
       materialForm.addEventListener('submit', function(event) {
           event.preventDefault(); // Prevenir envío tradicional

           // >>> CORRECCIÓN: Obtener la referencia al formulario (event.target) aquí <<<
           const form = event.target; // <-- Define 'form' dentro del listener

           // 1. Validación
           let isValid = true; // Bandera de validación
           const errores = []; // Array para errores
           const selectedProvider = proveedorSelect ? proveedorSelect.value : null; // Proveedor seleccionado

           // --- Lógica de Validación (Usa la variable 'form' aquí) ---
           // Limpiar errores visuales y mensajes anteriores
            form.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field')); // Usar 'form' para seleccionar dentro del formulario
            if (responseMessageDiv) { // Limpiar div de respuesta AJAX
                 responseMessageDiv.textContent = '';
                 responseMessageDiv.classList.remove('processing', 'success', 'error');
            }

           // Validar campos comunes (requeridos en HTML)
           const camposComunesReq = ['nombre_solicitante', 'fecha_solicitud', 'proveedor', 'departamento_area', 'proyecto'];
           camposComunesReq.forEach(id => {
               const campo = form.querySelector(`#${id}`); // Usar form.querySelector para seleccionar dentro del formulario
               // Verificar si el elemento existe, si es requerido en HTML5 (.required), no está deshabilitado y su valor no está vacío después de trim
               if (campo && campo.required && !campo.disabled && !campo.value.trim()) {
                   isValid = false;
                   const label = form.querySelector(`label[for="${id}"]`); // Usar form.querySelector
                   const nombreCampo = label ? label.textContent.replace(':', '').trim() : (campo.placeholder || campo.name || id);
                   errores.push(`"${nombreCampo}" obligatorio.`);
                   campo.classList.add('error-field');
                } else if (campo) { campo.classList.remove('error-field'); } // Limpiar si es válido o no requerido/deshabilitado
           });

           // Validación específica de Torni si el proveedor es Torni
           if (selectedProvider === 'Torni') {
               // Si el proveedor es Torni, la tabla DEBE tener al menos una fila con datos VÁLIDOS
               if (!torniTableBody || torniTableBody.rows.length === 0) {
                   isValid = false;
                   errores.push("Añadir al menos un producto para proveedor Torni.");
               } else {
                    // Validar cada fila de Torni
                    let hasValidTorniItem = false; // Verificar si al menos un item es válido (opcional, la validación por fila es más granular)
                    torniTableBody.querySelectorAll('tr').forEach((row, index) => {
                        const qtyInput = row.querySelector('.torni-qty');
                        const idInput = row.querySelector('.torni-id');
                        const descInput = row.querySelector('.torni-desc');

                        let isRowValid = true; // Bandera para la fila actual

                        // Validar Cantidad (>0)
                        if (!qtyInput || parseFloat(qtyInput.value) <= 0 || isNaN(parseFloat(qtyInput.value))) {
                            isRowValid = false; errores.push(`Fila Torni ${index + 1}: Cantidad > 0.`); if(qtyInput) qtyInput.classList.add('error-field'); // Marcar error visual
                        } else { if (qtyInput) qtyInput.classList.remove('error-field'); } // Limpiar si es válido


                        // Validar Descripción (no vacía)
                        if (!descInput || !descInput.value.trim()) {
                            isRowValid = false; errores.push(`Fila Torni ${index + 1}: Descripción obligatoria.`); if(descInput) descInput.classList.add('error-field');
                        } else { if (descInput) descInput.classList.remove('error-field'); }

                        // Validar ID (no vacío - debe ser llenado por Awesomplete select)
                        // El IDinput es readonly, su valor solo cambia al seleccionar de Awesomplete
                        if (!idInput || !idInput.value.trim()) {
                             isRowValid = false; errores.push(`Fila Torni ${index + 1}: Producto no seleccionado correctamente (usa sugerencias).`);
                             if(idInput) idInput.classList.add('error-field');
                             if(descInput && !descInput.classList.contains('error-field')) descInput.classList.add('error-field'); // Marcar descripción como error también si el ID falta
                        } else { if (idInput) idInput.classList.remove('error-field'); }

                        // Si la fila es válida, marcar que hay al menos un item válido (si es necesario para una validación general)
                        if (isRowValid) { hasValidTorniItem = true; } // Si al menos una fila es válida
                    });
                    // Si hay filas pero ninguna es completamente válida
                    // La validación general de 'isValid' ya se maneja por los errores individuales añadidos anteriormente.
                    // Si quieres que isValid sea false A MENOS QUE HAYA AL MENOS UNA FILA VÁLIDA:
                    // if (torniTableBody.rows.length > 0 && !hasValidTorniItem) isValid = false;


               }
           } else if (selectedProvider && selectedProvider !== '') { // Proveedor estándar seleccionado
                // Validar campos estándar requeridos (si están habilitados)
                const camposRequeridosStd = ['cantidad_solicitada', 'tipo_material', 'nombre_material', 'unidad_medida']; // Dimensiones NO son requeridas por defecto
                camposRequeridosStd.forEach(id => {
                    const campo = form.querySelector(`#${id}`); // Usar form.querySelector
                    if (campo && campo.required && !campo.disabled && !campo.value.trim()) {
                         isValid = false; const label = form.querySelector(`label[for="${id}"]`);
                         const nombreCampo = label ? label.textContent.replace(':', '').trim() : id;
                         errores.push(`"${nombreCampo}" obligatorio.`); campo.classList.add('error-field');
                     } else if (campo) { campo.classList.remove('error-field'); }
                });

                // Validación específica de cantidad solicitada si está habilitada y no es Torni
                if (cantidadSolicitadaInput && !cantidadSolicitadaInput.disabled) {
                    const valorCampo = cantidadSolicitadaInput.value.trim();
                    if (!valorCampo || parseFloat(valorCampo) <= 0 || isNaN(parseFloat(valorCampo))) {
                         isValid = false; errores.push(`"Cantidad Solicitada" > 0.`); cantidadSolicitadaInput.classList.add('error-field');
                    } else { cantidadSolicitadaInput.classList.remove('error-field'); }
                }
                // Validación opcional de dimensiones si están llenas (puedes añadir aquí)
                // ['largo', 'ancho', 'alto', 'diametro'].forEach(id => { ... });
           } else {
                // Si no se ha seleccionado proveedor, la validación de 'proveedor' ya lo marcó como obligatorio
                // No necesitas añadir más errores generales aquí.
           }


           // 2. Si hay errores, mostrar y detener el submit
           if (!isValid) {
                console.log("Validación fallida en frontend:", errores);
                const uniqueErrors = [...new Set(errores)];
                if (responseMessageDiv) {
                    responseMessageDiv.innerHTML = "Por favor, corrige los errores:<br>" + uniqueErrors.join('<br>');
                    responseMessageDiv.classList.add('error');
                }
                const primerErrorField = form.querySelector('.error-field:not(:disabled)'); // Usar 'form' para seleccionar
                if(primerErrorField) primerErrorField.focus();
                return; // Detener el submit
           }
           // --- Fin Lógica de Validación ---


           // 3. Recolectar datos en formato JSON
           console.log("Validación exitosa. Recolectando datos para JSON...");
           const datosSolicitud = collectFormData(); // Llama a la función de recolección implementada


           // 4. Fetch al backend
           console.log('Datos del formulario a enviar:', datosSolicitud);

           // Mostrar estado de procesamiento ANTES del fetch
           if (responseMessageDiv) {
                responseMessageDiv.textContent = 'Enviando solicitud...';
                responseMessageDiv.classList.remove('error', 'success');
                responseMessageDiv.classList.add('processing');
            }


           fetch(form.action, { // Usa form.action para obtener la URL correcta
               method: form.method, // Usa el método del formulario (POST)
               headers: {
                   'Content-Type': 'application/json', // Indicar que enviamos JSON
               },
               body: JSON.stringify(datosSolicitud) // Convertir el objeto de datos a string JSON
           })
           .then(response => {
                if (responseMessageDiv) responseMessageDiv.classList.remove('processing');

                if (!response.ok) {
                     return response.json().then(errData => {
                          let msg = errData.error || `Error: ${response.status}`;
                          if(errData.notion_error) msg += ` (Notion: ${errData.notion_error.message})`;
                          else if(errData.details) msg += `: ${errData.details}`;

                          throw new Error(msg);
                     }).catch(() => {
                          throw new Error(`Error ${response.status}: ${response.statusText}`);
                     });
                }
                return response.json();
           })
           .then(data => {
               console.log('Respuesta backend exitosa:', data);

               let feedbackMessage = "";
               let isSuccess = false;
               let firstUrl = null;

               if (data.message) { feedbackMessage = data.message; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db2; }
               else if (data.warning) { feedbackMessage = data.warning; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db2; }
               else if (data.error) { feedbackMessage = data.error; isSuccess = false; }
               else { feedbackMessage = "Respuesta inesperada del servidor."; isSuccess = false; }

               if (responseMessageDiv) { // Asegurarse que existe
                   if (isSuccess) {
                       responseMessageDiv.innerHTML = feedbackMessage + (firstUrl ? ` <a href="${firstUrl}" target="_blank" rel="noopener noreferrer">Ver Registro</a>` : '');
                       responseMessageDiv.classList.add('success');
                   } else {
                       responseMessageDiv.textContent = feedbackMessage;
                       responseMessageDiv.classList.add('error');
                   }
               }

               // Resetear formulario y UI solo si fue éxito total o parcial manejado
               if (isSuccess) {
                   form.reset(); // <<< Usar 'form' aquí para resetear
                   currentFolio = generateFolio(); updateFolioDisplay(currentFolio);
                   // Llama a handleProveedorChange para resetear UI y habilitar/deshabilitar
                   handleProveedorChange(); // Esto también llama a actualizarMateriales y updateDatalistForUnit si es necesario

                   // Asegurar que la fecha actual se restablece
                    if(fechaInput) {
                        const today = new Date();
                        const year = today.getFullYear();
                        const month = ('0' + (today.getMonth() + 1)).slice(-2);
                        const day = ('0' + today.getDate()).slice(-2);
                        fechaInput.value = `${year}-${month}-${day}`;
                   }
                   // Limpiar la tabla Torni
                   if (torniTableBody) torniTableBody.innerHTML = '';
                   // Añadir una fila Torni inicial si es el proveedor por defecto y la tabla está vacía
                    if (proveedorSelect && proveedorSelect.value === 'Torni' && torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
                         addTorniRow();
                    }
               }
           })
           .catch(error => {
               console.error('Error inesperado en fetch o procesamiento:', error);

                if (responseMessageDiv) {
                    responseMessageDiv.classList.remove('processing');
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


    // Carga de Datos (LLAMA A fetch, que en su .then llama a funciones para inicializar UI)
    // Verificar si las variables de URL existen antes de usar fetch
    if (typeof STANDARD_DIMENSIONS_URL !== 'undefined' && typeof TORNI_MASTERLIST_URL !== 'undefined') {
        Promise.all([
            // Usar las variables JavaScript definidas en la plantilla HTML
            fetch(STANDARD_DIMENSIONS_URL).then(res => {
                 if (!res.ok) throw new Error(`Dimensiones: ${res.status} ${res.statusText}`);
                 return res.json();
             }).catch(error => { console.error("Error en fetch de Dimensiones:", error); throw error; }), // Re-lanzar error después de log
            fetch(TORNI_MASTERLIST_URL).then(res => {
                 if (!res.ok) throw new Error(`Items Torni: ${res.status} ${res.statusText}`);
                 return res.json();
             }).catch(error => { console.error("Error en fetch de Items Torni:", error); throw error; }) // Re-lanzar error después de log
        ])
        .then(([dimensionsData, torniData]) => {
            console.log("Datos iniciales cargados con éxito.");
            allStandardDimensions = dimensionsData; // Guardar datos de dimensiones
            torniMasterList = torniData || []; // Guardar lista maestra Torni o array vacío

            // --- Llamadas a funciones para inicializar la UI *después* de cargar los datos ---
            updateDatalistForUnit(); // Poblar datalist inicial con unidad por defecto
            handleProveedorChange(); // Trigger initial UI state based on default/saved proveedor

            // Añadir una fila Torni por defecto si el proveedor inicial es Torni y la tabla está vacía
            // Solo si hay datos maestros cargados
            if (proveedorSelect && proveedorSelect.value === 'Torni' && torniTableBody && torniTableBody.rows.length === 0 && torniMasterList.length > 0) {
                 addTorniRow();
            }

             // Asegurar que el botón de submit esté habilitado si los datos cargaron correctamente y el formulario existe
             if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = false;

        })
        .catch(error => {
            console.error("Error general al cargar datos JSON iniciales:", error);
            // Mostrar error en el div de respuesta AJAX
            if(responseMessageDiv){
                 responseMessageDiv.textContent = `Error al cargar datos iniciales: ${error.message || 'Ver logs de consola.'}`;
                 responseMessageDiv.classList.add('error');
            }
             // Deshabilitar el formulario o el botón de submit si los datos iniciales son críticos
            if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
        });
    } else {
         console.error("URLs para datos iniciales (JSON estáticos) no definidas. Asegura que STANDARD_DIMENSIONS_URL y TORNI_MASTERLIST_URL están definidas en la plantilla HTML antes de cargar request_for_material.js.");
          // Mostrar error en el div de respuesta AJAX
         if(responseMessageDiv){
              responseMessageDiv.textContent = `Error: URLs de datos iniciales no configuradas en la plantilla HTML.`;
              responseMessageDiv.classList.add('error');
         }
         // Deshabilitar el formulario si faltan URLs
         if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
    }


    // --- Event Listeners (Añadirlos después de definir las funciones) ---
    // Event listeners para inputs de dimensiones
    if(largoInput) largoInput.addEventListener('input', updateDimensionLogic);
    if(anchoInput) anchoInput.addEventListener('input', updateDimensionLogic);
    if(altoInput) altoInput.addEventListener('input', updateDimensionLogic);
    if(diametroInput) diametroInput.addEventListener('input', updateDimensionLogic);

    // Event listener para Unidad de Medida
    if (unidadMedidaSelect) { unidadMedidaSelect.addEventListener('change', updateDatalistForUnit); }

    // Event listeners para dropdowns dependientes (Proveedor y Material)
     if (proveedorSelect) { proveedorSelect.addEventListener('change', handleProveedorChange); } // Este controla UI y llama a actualizarMateriales
    if (materialSelect) { materialSelect.addEventListener('change', actualizarTipoMaterial); }


    // Event listeners para botones de añadir/eliminar filas Torni (el botón añadir está en el HTML)
    if (addTorniItemBtn) { addTorniItemBtn.addEventListener('click', addTorniRow); }
     // Listener para botones de eliminar filas existentes al cargar (si las hubiera)
     // y para botones de eliminar en filas añadidas dinámicamente (gestionado en addTorniRow)
     if (torniTableBody) {
         torniTableBody.querySelectorAll('.delete-row-btn').forEach(btn => {
             btn.addEventListener('click', deleteTorniRow);
         });
         // Opcional: Observar cambios en el DOM para añadir listeners a nuevos botones de eliminar
         // const observer = new MutationObserver(mutations => {
         //    mutations.forEach(mutation => {
         //        if (mutation.type === 'childList') {
         //            mutation.addedNodes.forEach(node => {
         //                if (node.tagName === 'TR') {
         //                    const deleteBtn = node.querySelector('.delete-row-btn');
         //                    if (deleteBtn) deleteBtn.addEventListener('click', deleteTorniRow);
         //                }
         //            });
         //        }
         //    });
         // });
         // observer.observe(torniTableBody, { childList: true });
     }

    // Event listener para el submit del formulario
    setupFormSubmitListener(); // Configura el listener del submit


    // --- Lógica de Inicialización de UI (Llamadas de funciones al cargar) ---
    // Estas llamadas se hacen DESPUÉS de definir las funciones y DESPUÉS de cargar los datos iniciales
    // Algunas de estas llamadas ya están integradas en el .then() de Promise.all o en handleProveedorChange()

    // Establecer fecha por defecto si no está puesta
    // Esto ya lo haces, asegúrate que está en el DOMContentLoaded
    if (fechaInput && !fechaInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        const month = ('0' + (today.getMonth() + 1)).slice(-2);
        const day = ('0' + today.getDate()).slice(-2);
        fechaInput.value = `${year}-${month}-${day}`;
    }

     // La lógica de UI inicial (mostrar/ocultar secciones, habilitar/deshabilitar campos)
     // y la lógica de actualizar dropdowns dependientes
     // y la lógica de añadir fila Torni por defecto (si aplica)
     // SE EJECUTAN DENTRO DEL .then() de Promise.all, DESPUÉS de que los datos JSON se cargan.
     // Esto es correcto porque estas lógicas dependen de tener los datos (torniMasterList) y la UI lista.


}); // Fin DOMContentLoaded