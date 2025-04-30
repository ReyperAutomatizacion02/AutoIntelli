document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a elementos ---
    const materialForm = document.getElementById('materialForm');
    const mensajeExito = document.getElementById('mensaje-exito');
    const mensajeValidacion = document.getElementById('mensaje-validacion');
    const mensajeErrorEnvio = document.getElementById('mensaje-error-envio');
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
    const nombreMaterialGroup = document.getElementById('nombre-material-group'); // Verifica que exista
    const tipoMaterialGroup = document.getElementById('tipo-material-group'); // Verifica que exista
    // --- Referencias a elementos de Torni ---
    const torniTableContainer = document.getElementById('torni-table-container');
    const torniTableBody = document.getElementById('torni-items-tbody');
    const addTorniItemBtn = document.getElementById('add-torni-item-btn');
    // --- Referencias Folio ---
    const folioDisplayValue = document.getElementById('folio-display-value');
    const folioInputHidden = document.getElementById('folio_solicitud');
    // --- Fin Referencias ---
    let allStandardDimensions = {}; // Para dimensiones estándar
    let torniMasterList = []; // <-- NUEVO: para lista de items Torni
    let currentFolio = null; // Para folio actual

    // --- Función para generar Folio ---
    function generateFolio() {
        const timestamp = Date.now();
        const randomPart = Math.random().toString(36).substring(2, 8).toUpperCase();
        return `SOL-${timestamp}-${randomPart}`;
    }

    // --- Función para actualizar display y campo oculto del folio ---
    function updateFolioDisplay(folio) {
        if (folioDisplayValue) folioDisplayValue.textContent = folio;
        if (folioInputHidden) folioInputHidden.value = folio;
    }

    // --- Generar y Mostrar Folio Inicial al Cargar ---
    currentFolio = generateFolio();
    updateFolioDisplay(currentFolio);
    console.log("Folio inicial generado:", currentFolio);

    // --- Lógica Interdependiente de Dimensiones ---
    function handleDiameterLogic() { if (!largoInput || !anchoInput || !altoInput || !diametroInput) return; const largoValue = largoInput.value.trim(); const anchoValue = anchoInput.value.trim(); const altoValue = altoInput.value.trim(); if (largoValue && (anchoValue || altoValue)) { if (!anchoInput.disabled || !altoInput.disabled) { if (!diametroInput.disabled) { diametroInput.value = "N/A"; diametroInput.disabled = true; diametroInput.classList.add('na-field'); diametroInput.classList.remove('error-field'); } } } else { if (!anchoInput.disabled && !altoInput.disabled) { diametroInput.disabled = false; diametroInput.classList.remove('na-field'); if (diametroInput.value === "N/A") diametroInput.value = ""; } } }
    function handleWidthHeightLogic() { if (!anchoInput || !altoInput || !diametroInput) return; const diametroValue = diametroInput.value.trim(); if (diametroValue && diametroValue !== "N/A" && !diametroInput.disabled) { anchoInput.value = "N/A"; anchoInput.disabled = true; anchoInput.classList.add('na-field'); anchoInput.classList.remove('error-field'); altoInput.value = "N/A"; altoInput.disabled = true; altoInput.classList.add('na-field'); altoInput.classList.remove('error-field'); } else { if (!diametroInput.disabled || (diametroInput.disabled && diametroInput.value === "N/A")) { anchoInput.disabled = false; anchoInput.classList.remove('na-field'); if (anchoInput.value === "N/A") anchoInput.value = ""; altoInput.disabled = false; altoInput.classList.remove('na-field'); if (altoInput.value === "N/A") altoInput.value = ""; } } }
    function updateDimensionLogic() { handleWidthHeightLogic(); handleDiameterLogic(); }
    if(largoInput) largoInput.addEventListener('input', updateDimensionLogic); if(anchoInput) anchoInput.addEventListener('input', updateDimensionLogic); if(altoInput) altoInput.addEventListener('input', updateDimensionLogic); if(diametroInput) diametroInput.addEventListener('input', updateDimensionLogic);

    // --- Función para Poblar Datalist ---
    function populateDimensionDatalist(dimensionsArray) { if (dimensionDatalist && dimensionsArray && Array.isArray(dimensionsArray)) { dimensionDatalist.innerHTML = ''; dimensionsArray.forEach(dim => { const option = document.createElement('option'); option.value = String(dim); dimensionDatalist.appendChild(option); }); console.log(`Datalist poblado con ${dimensionsArray.length} opciones.`); } else { if(dimensionDatalist) dimensionDatalist.innerHTML = ''; console.log("Datalist limpiado."); } }

    // --- Función para Actualizar Datalist según Unidad ---
    function updateDatalistForUnit() { if (!unidadMedidaSelect) return; const selectedUnit = unidadMedidaSelect.value; const dimensionsForUnit = allStandardDimensions[selectedUnit] || []; populateDimensionDatalist(dimensionsForUnit); }

    // --- Carga de Datos (Dimensiones y Torni) ---
    Promise.all([
        fetch('/static/data/standard_dimensions_by_unit.json').then(res => { if (!res.ok) throw new Error(`Dimensiones: ${res.statusText}`); return res.json(); }),
        fetch('/static/data/torni_items_masterlist.json').then(res => { if (!res.ok) throw new Error(`Items Torni: ${res.statusText}`); return res.json(); }) // Cargar lista Torni
    ])
    .then(([dimensionsData, torniData]) => {
        console.log("Dimensiones cargadas:", dimensionsData);
        console.log("Items Torni cargados:", torniData);
        allStandardDimensions = dimensionsData;
        torniMasterList = torniData || []; // Guardar lista Torni o array vacío si falla

        updateDatalistForUnit(); // Poblar datalist inicial
        setupFormValidationAndSubmit(allStandardDimensions); // Configurar validación/submit
    })
    .catch(error => {
        console.error("Error cargando datos JSON:", error);
        if(mensajeErrorEnvio){ mensajeErrorEnvio.textContent = `Error al cargar datos: ${error.message}`; mensajeErrorEnvio.classList.remove('oculto'); }
        setupFormValidationAndSubmit({}); // Configurar con datos vacíos
    });

    // --- Event Listener para Unidad de Medida ---
    if (unidadMedidaSelect) { unidadMedidaSelect.addEventListener('change', updateDatalistForUnit); }

    // --- Lógica Modo Oscuro ---
    const applyMode = (mode) => { if (!darkModeToggle) return; if (mode === 'dark') { body.classList.add('dark-mode'); localStorage.setItem('darkMode', 'enabled'); darkModeToggle.textContent = '☀️'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo claro'); } else { body.classList.remove('dark-mode'); localStorage.setItem('darkMode', 'disabled'); darkModeToggle.textContent = '🌙'; darkModeToggle.setAttribute('aria-label', 'Cambiar a modo oscuro'); } };
    let currentMode = localStorage.getItem('darkMode'); const prefersDarkScheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches; let initialMode = 'light'; if (currentMode === 'enabled' || (currentMode === null && prefersDarkScheme)) { initialMode = 'dark'; } applyMode(initialMode);
    if(darkModeToggle) { darkModeToggle.addEventListener('click', () => { if (body.classList.contains('dark-mode')) { applyMode('light'); } else { applyMode('dark'); } }); }

    // --- Lógica Dropdowns Dependientes (Material/Tipo) ---
    const materialesPorProveedor = { "Mipsa": ["D2", "Cobre", "Aluminio"], "LBO": ["H13", "1018", "4140T"], "Grupo Collado": ["D2", "4140T", "H13", "1018", "Acetal"], "Cameisa": ["Aluminio", "Cobre", "Acetal", "Nylamid"], "Surcosa": ["1018", "Nylamid", "Acetal", "D2"], "Diace": ["D2", "H13", "Aluminio", "4140T", "Cobre", "1018"] };
    const tipoPorMaterial = { "D2": "Metal", "Aluminio": "Metal", "Cobre": "Metal", "4140T": "Metal", "H13": "Metal", "1018": "Metal", "Acetal": "Plastico", "Nylamid": "Plastico" };
    function actualizarMateriales() { if (!proveedorSelect || !materialSelect || !tipoMaterialSelect) return; const selectedProveedor = proveedorSelect.value; materialSelect.innerHTML = '<option value="" disabled selected>Seleccionar material:</option>'; tipoMaterialSelect.value = ""; tipoMaterialSelect.disabled = true; if (selectedProveedor && materialesPorProveedor[selectedProveedor]) { const materialesDisponibles = materialesPorProveedor[selectedProveedor]; materialesDisponibles.forEach(material => { const option = document.createElement('option'); option.value = material; option.textContent = material; materialSelect.appendChild(option); }); materialSelect.disabled = false; actualizarTipoMaterial(); } else { materialSelect.disabled = true; } }
    function actualizarTipoMaterial() { if (!materialSelect || !tipoMaterialSelect) return; const selectedMaterial = materialSelect.value; if(selectedMaterial && tipoPorMaterial[selectedMaterial]) { const tipo = tipoPorMaterial[selectedMaterial]; tipoMaterialSelect.value = tipo; tipoMaterialSelect.disabled = false; } else { tipoMaterialSelect.value = ""; tipoMaterialSelect.disabled = true; } }
    if (materialSelect) { materialSelect.addEventListener('change', actualizarTipoMaterial); }

    // --- Lógica Tabla Torni (ACTUALIZADA con Awesomplete) ---
    function addTorniRow() {
        if (!torniTableBody) return;
        console.log("Intentando añadir fila Torni...");
        const rowCount = torniTableBody.rows.length;
        const newRow = torniTableBody.insertRow();
        newRow.innerHTML = `
            <td><input type="number" class="torni-qty" name="torni_qty_${rowCount}" min="1" value="1" required></td>
            <td><input type="text" class="torni-id" id="torni-id-${rowCount}" name="torni_id_${rowCount}" readonly></td> <!-- Empieza readonly -->
            <td><input type="text" class="torni-desc" id="torni-desc-${rowCount}" name="torni_desc_${rowCount}" placeholder="Escribe para buscar..." required autocomplete="off"></td>
            <td><button type="button" class="delete-row-btn">X</button></td>
        `;

        const descInput = newRow.querySelector('.torni-desc');
        const idInput = newRow.querySelector('.torni-id');
        const deleteBtn = newRow.querySelector('.delete-row-btn');

        if (deleteBtn) { deleteBtn.addEventListener('click', deleteTorniRow); }

        // --- Inicializar Awesomplete ---
        console.log("Verificando Awesomplete y datos Torni...");
        console.log("Awesomplete disponible:", typeof Awesomplete);
        console.log("Datos Torni para lista:", torniMasterList);
        if (descInput && typeof Awesomplete !== 'undefined' && torniMasterList.length > 0) {
             console.log("Inicializando Awesomplete (Modo Simple)...");
             // *** CORRECCIÓN: Pasar solo las descripciones a la lista ***
             const descriptionsList = torniMasterList.map(item => item.description);

             const awesompleteInstance = new Awesomplete(descInput, {
                 list: descriptionsList, // <-- Usar solo array de strings (descripciones)
                 // data: ya no es necesaria si usamos list de strings
                 item: function (text, input) { // <-- 'text' ahora SÍ es un string
                     console.log("Inside item (simple) - text:", text, "input:", input); // Para debug
                     if (typeof text !== 'string') { // Check por si acaso
                        console.error("Invalid text suggestion:", text);
                        return Awesomplete.ITEM(String(text || ''), input);
                     }
                     // Resaltar la parte coincidente
                     let html = input.trim() === "" ? text :
                                text.replace(new RegExp(Awesomplete.$.regExpEscape(input.trim()), "gi"), "<mark>$&</mark>");
                     // Devolver el elemento li formateado
                     return Awesomplete.ITEM(html, text); // Pasamos text dos veces para el resaltado y valor interno
                 },
                 replace: function(suggestionText) { // suggestionText es el string seleccionado
                     this.input.value = suggestionText; // Poner la descripción completa en el input
                 },
                 minChars: 1, maxItems: 10, autoFirst: true
             });
             console.log("Instancia Awesomplete creada (Modo Simple):", awesompleteInstance);

             // --- Listener para cuando se SELECCIONA un item (ACTUALIZADO) ---
             descInput.addEventListener('awesomplete-selectcomplete', function(event) {
                const selectedDescription = event.text; // String de la descripción seleccionada
                console.log("--- Awesomplete Selección Completa ---");
                console.log("Descripción seleccionada:", selectedDescription);

                // *** DEBUG: Verificar que idInput existe y es el correcto ***
                const currentRow = descInput.closest('tr'); // Obtener la fila actual
                const idInputInRow = currentRow ? currentRow.querySelector('.torni-id') : null; // Buscar ID dentro de esa fila
                console.log("Input ID encontrado en la fila:", idInputInRow);
                // *** Fin DEBUG ***

                // Buscar el item completo en la lista maestra
                const selectedItem = torniMasterList.find(item => {
                    // Comparación más robusta (ignorar espacios extra y case-insensitive)
                    return typeof item.description === 'string' &&
                           item.description.trim().toLowerCase() === selectedDescription.trim().toLowerCase();
                });
                console.log("Item encontrado en Master List:", selectedItem); // Verifica si lo encuentra

                // Actualizar el input ID correcto
                if (idInputInRow && selectedItem?.id) {
                    console.log("Actualizando ID con:", selectedItem.id); // <-- Verifica el ID
                    idInputInRow.value = selectedItem.id; // Poner el ID
                    idInputInRow.classList.remove('error-field'); // Limpiar error si lo había
                    descInput.classList.remove('error-field'); // Limpiar error descripción
                } else if (idInputInRow) {
                     idInputInRow.value = ''; // Limpiar ID si no se encontró
                     console.warn("No se encontró ID para la descripción o el item no tiene ID:", selectedDescription, selectedItem);
                     // Marcar como error si se requiere una selección válida?
                     // idInputInRow.classList.add('error-field');
                     // descInput.classList.add('error-field');
                } else {
                     console.error("No se pudo encontrar el campo ID en la fila para actualizar.");
                }
            });

             // --- Limpiar ID si se borra/cambia descripción manualmente (ACTUALIZADO) ---
             descInput.addEventListener('input', function() {
                 const currentDesc = descInput.value.trim();
                 // Buscar si el texto actual coincide EXACTAMENTE con alguna descripción
                 const match = torniMasterList.find(item => item.description === currentDesc);
                 if (idInput && !match) { // Si no hay coincidencia exacta, borrar el ID
                      idInput.value = '';
                 } else if (idInput && match && idInput.value !== match.id) {
                      // Opcional: Si coincide pero el ID es incorrecto, corregirlo
                      idInput.value = match.id;
                 }
             });

        } else {
             if (typeof Awesomplete === 'undefined') console.error("¡Awesomplete NO está definido! Revisa la carga del script.");
             if (torniMasterList.length === 0) console.warn("torniMasterList está vacía. No se puede inicializar Awesomplete.");
             if (!descInput) console.error("Input de descripción no encontrado en la nueva fila.");
        }
    } // Fin addTorniRow

    function deleteTorniRow(event) { if (!torniTableBody) return; const button = event.target; const row = button.closest('tr'); if (row) { row.remove(); if (torniTableBody.rows.length === 0) { addTorniRow(); } } }
    if (addTorniItemBtn) { addTorniItemBtn.addEventListener('click', addTorniRow); }
    if (torniTableBody) { torniTableBody.querySelectorAll('.delete-row-btn').forEach(btn => { btn.addEventListener('click', deleteTorniRow); }); }
    // --- Fin Lógica Tabla Torni ---


     // --- Lógica de UI basada en Proveedor ---
     function handleProveedorChange() {
        if (!proveedorSelect || !dimensionesContainer || !torniTableContainer ||
            !cantidadUnidadGroup || !cantidadSolicitadaGroup || !nombreMaterialGroup || !tipoMaterialGroup) { console.error("Faltan elementos DOM."); return; }

        const selectedProveedor = proveedorSelect.value;
        const esTorni = selectedProveedor === 'Torni';

        dimensionesContainer.classList.toggle('oculto', esTorni);
        torniTableContainer.classList.toggle('oculto', !esTorni);
        cantidadUnidadGroup.classList.toggle('oculto', esTorni);
        cantidadSolicitadaGroup.classList.toggle('oculto', esTorni);

        // --- AÑADIDO: Controlar los grupos movidos ---
        if (nombreMaterialGroup) nombreMaterialGroup.classList.toggle('oculto', esTorni);
        if (tipoMaterialGroup) tipoMaterialGroup.classList.toggle('oculto', esTorni);
        // --- FIN AÑADIDO ---

        if (esTorni) {
            if (torniTableBody && torniTableBody.rows.length === 0) { addTorniRow(); }
            [materialSelect, tipoMaterialSelect, unidadMedidaSelect, largoInput, anchoInput, altoInput, diametroInput, cantidadSolicitadaInput].forEach(el => { if(el) { el.classList.remove('error-field'); el.value = ''; } });
             if (unidadMedidaSelect) unidadMedidaSelect.value = 'N/A';
             if (cantidadSolicitadaInput) cantidadSolicitadaInput.value = '1';
        } else {
             if (torniTableBody){ torniTableBody.querySelectorAll('input').forEach(input => input.classList.remove('error-field')); }
             // Habilitar campos estándar
            if (unidadMedidaSelect) { unidadMedidaSelect.disabled = false; unidadMedidaSelect.classList.remove('na-field'); if(unidadMedidaSelect.value === 'N/A') unidadMedidaSelect.value = 'Milímetros'; }
            if(cantidadSolicitadaInput) cantidadSolicitadaInput.disabled = false;
            if(largoInput) largoInput.disabled = false; if(anchoInput) anchoInput.disabled = false; if(altoInput) altoInput.disabled = false; if(diametroInput) diametroInput.disabled = false;
            // Actualizar lógicas dependientes
            updateDimensionLogic(); updateDatalistForUnit(); actualizarMateriales();
        }
     }
     if (proveedorSelect) { proveedorSelect.addEventListener('change', handleProveedorChange); }
     // --- Fin Lógica UI ---


    // --- Función para Configurar la Validación y el Envío del Formulario ---
    function setupFormValidationAndSubmit(standardDimensionsByUnit) {
        if (!materialForm) return;

        materialForm.addEventListener('submit', function(event) {
            event.preventDefault();
            // --- Folio ---
            console.log("Intentando enviar con folio:", currentFolio);
            if (!currentFolio) { currentFolio = generateFolio(); updateFolioDisplay(currentFolio); }
            else if (folioInputHidden && !folioInputHidden.value) { folioInputHidden.value = currentFolio; }
            // --- Fin Folio ---

            // 1. Limpiar errores
            if (mensajeValidacion) { mensajeValidacion.classList.add('oculto'); mensajeValidacion.innerHTML = ''; }
            if (mensajeExito) mensajeExito.classList.add('oculto'); if (mensajeErrorEnvio) mensajeErrorEnvio.classList.add('oculto');
            materialForm.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
            if (torniTableBody) torniTableBody.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));

            // 2. Validación
            let isValid = true; const errores = []; const selectedProvider = proveedorSelect ? proveedorSelect.value : null;

            // Validar campos comunes
            ['nombre_solicitante', 'fecha_solicitud', 'proveedor', 'departamento_area', 'proyecto'].forEach(id => { const campo = document.getElementById(id); if (campo && !campo.disabled && !campo.value.trim()) { isValid = false; const label = document.querySelector(`label[for="${id}"]`); const nombreCampo = label ? label.textContent.replace(':', '').trim() : (campo.placeholder || campo.name || id); errores.push(`"${nombreCampo}" obligatorio.`); campo.classList.add('error-field'); } });

            // Validación específica
            if (selectedProvider === 'Torni') {
                if (!torniTableBody || torniTableBody.rows.length === 0) { isValid = false; errores.push("Añadir al menos un producto."); }
                else {
                     torniTableBody.querySelectorAll('tr').forEach((row, index) => {
                         const qtyInput = row.querySelector('.torni-qty'); const idInput = row.querySelector('.torni-id'); const descInput = row.querySelector('.torni-desc');
                         if (!qtyInput || parseFloat(qtyInput.value) <= 0 || isNaN(parseFloat(qtyInput.value))) { isValid = false; errores.push(`F${index + 1}: Cantidad > 0.`); if(qtyInput) qtyInput.classList.add('error-field'); }
                         if (!idInput || !idInput.value.trim()) { isValid = false; errores.push(`F${index + 1}: ID obligatorio (selecciona descripción).`); if(idInput) idInput.classList.add('error-field'); if(descInput && !descInput.classList.contains('error-field')) descInput.classList.add('error-field'); } // Marcar ambos si ID falta
                         if (!descInput || !descInput.value.trim()) { isValid = false; errores.push(`F${index + 1}: Descripción obligatoria.`); if(descInput) descInput.classList.add('error-field'); }
                     });
                }
            } else { // Proveedor estándar
                 const camposRequeridosStd = ['cantidad_solicitada', 'tipo_material', 'nombre_material', 'unidad_medida', 'largo', 'ancho', 'alto', 'diametro'];
                 const camposDimension = ['largo', 'ancho', 'alto', 'diametro'];
                 const currentUnit = unidadMedidaSelect ? unidadMedidaSelect.value : null;
                 const currentStandardDimensions = (currentUnit && standardDimensionsByUnit[currentUnit]) ? standardDimensionsByUnit[currentUnit].map(String) : [];
                 camposRequeridosStd.forEach(id => { const campo = document.getElementById(id); if (!campo || campo.disabled) return; const label = document.querySelector(`label[for="${id}"]`); const nombreCampo = label ? label.textContent.replace(':', '').trim() : id; let isCampoInvalido = false; const valorCampo = campo.value.trim(); if (!valorCampo) { isCampoInvalido = true; errores.push(`"${nombreCampo}" obligatorio.`); } else { if (id === 'cantidad_solicitada') { if (parseFloat(valorCampo) <= 0 || isNaN(parseFloat(valorCampo))) { isCampoInvalido = true; errores.push(`"${nombreCampo}" > 0.`); } } else if (camposDimension.includes(id)) { if (currentStandardDimensions.length > 0 && !currentStandardDimensions.includes(valorCampo)) { isCampoInvalido = true; errores.push(`"${nombreCampo}" debe ser estándar.`); } } } if (isCampoInvalido) { isValid = false; campo.classList.add('error-field'); } });
            }

            // 3. Si hay errores, mostrar y detener
            if (!isValid) { const uniqueErrors = [...new Set(errores)]; if (mensajeValidacion) { mensajeValidacion.innerHTML = "Por favor, corrige los errores:<br>" + uniqueErrors.join('<br>'); mensajeValidacion.classList.remove('oculto'); } const primerError = materialForm.querySelector('.error-field:not(:disabled)'); if(primerError) primerError.focus(); return; }

            // 4. Recolectar datos
            console.log("Validación exitosa. Enviando datos...");
            const formData = new FormData(materialForm); const datosSolicitud = {};
             ['nombre_solicitante', 'fecha_solicitud', 'proveedor', 'departamento_area', 'especificaciones_adicionales', 'folio_solicitud', 'Proyecto'].forEach(key => { const value = formData.get(key); if (key !== 'especificaciones_adicionales' || value) { datosSolicitud[key] = value ? value.trim() : ''; } });
             if (!datosSolicitud['folio_solicitud'] && currentFolio) datosSolicitud['folio_solicitud'] = currentFolio;

            if (selectedProvider === 'Torni') {
                const torniItems = [];
                if(torniTableBody) {
                    torniTableBody.querySelectorAll('tr').forEach(row => {
                        const qtyInput = row.querySelector('.torni-qty'); const idInput = row.querySelector('.torni-id'); const descInput = row.querySelector('.torni-desc');
                        if (qtyInput && idInput && descInput) { torniItems.push({ quantity: parseInt(qtyInput.value, 10) || 0, id: idInput.value.trim(), description: descInput.value.trim() }); }
                    });
                }
                datosSolicitud['torni_items'] = torniItems; datosSolicitud['unidad_medida'] = 'N/A';
            } else {
                if(formData.get('cantidad_solicitada')) datosSolicitud['cantidad_solicitada'] = parseInt(formData.get('cantidad_solicitada'), 10) || 0;
                datosSolicitud['tipo_material'] = formData.get('tipo_material') ? formData.get('tipo_material').trim() : '';
                datosSolicitud['nombre_material'] = formData.get('nombre_material') ? formData.get('nombre_material').trim() : '';
                datosSolicitud['unidad_medida'] = formData.get('unidad_medida') ? formData.get('unidad_medida').trim() : '';
                ['largo', 'ancho', 'alto', 'diametro'].forEach(dimKey => { const campo = document.getElementById(dimKey); if (campo) datosSolicitud[dimKey] = campo.disabled ? "N/A" : campo.value.trim(); });
            }
            console.log('Datos del formulario a enviar:', datosSolicitud);

            // 5. Fetch al backend
            fetch('http://127.0.0.1:5000/submit-request', { method: 'POST', headers: { 'Content-Type': 'application/json', }, body: JSON.stringify(datosSolicitud) })
            .then(response => { if (!response.ok) { return response.json().then(errData => { let msg = errData.error || `Error: ${response.status}`; if(errData.notion_error) msg += ` (Notion: ${errData.notion_error.message})`; throw new Error(msg); }).catch(()=> {throw new Error(`Error: ${response.status}`)})}; return response.json(); })
            .then(data => {
                console.log('Respuesta backend:', data);
                let feedbackMessage = ""; let isSuccess = false; let firstUrl = null;
                if (data.message) { feedbackMessage = data.message; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db1; }
                else if (data.warning) { feedbackMessage = data.warning; isSuccess = true; firstUrl = data.notion_url || data.notion_url_db1; }
                else if (data.error) { throw new Error(data.details ? `${data.error}: ${data.details}` : data.error); }
                else if (Array.isArray(data) && data.length > 0) { let successCount = data.filter(r => r.message || r.warning).length; let errorCount = data.filter(r => r.error).length; if(successCount > 0 && errorCount === 0) { feedbackMessage = `Solicitud Folio '${currentFolio}' (${successCount} item(s)) procesada.`; isSuccess = true; firstUrl = data.find(r => r.notion_url)?.notion_url || data.find(r => r.notion_url_db1)?.notion_url_db1; } else if (successCount > 0 && errorCount > 0) { feedbackMessage = `Folio '${currentFolio}' procesado parcialmente: ${successCount} OK, ${errorCount} fallaron.`; isSuccess = true; firstUrl = data.find(r => r.notion_url)?.notion_url || data.find(r => r.notion_url_db1)?.notion_url_db1; } else { throw new Error(data[0]?.details || data[0]?.error || `Error procesando items para Folio ${currentFolio}.`); } }
                else { throw new Error("Respuesta inesperada del servidor."); }

                if (isSuccess) {
                    materialForm.reset();
                    currentFolio = generateFolio(); updateFolioDisplay(currentFolio); // NUEVO folio
                    handleProveedorChange(); updateDimensionLogic();
                    const solicitanteSelect = document.getElementById('nombre_solicitante'); if(solicitanteSelect) solicitanteSelect.value = 'Maribel Reyes'; const deptoSelect = document.getElementById('departamento_area'); if(deptoSelect) deptoSelect.value = 'Producción'; if(fechaInput) fechaInput.valueAsDate = new Date();
                    if (torniTableBody) torniTableBody.innerHTML = ''; // Limpiar tabla
                    if(mensajeExito){ mensajeExito.innerHTML = feedbackMessage + (firstUrl ? ` <a href="${firstUrl}" target="_blank" rel="noopener noreferrer">Ver Registro</a>` : ''); mensajeExito.classList.remove('oculto'); mensajeExito.classList.toggle('mensaje-warning-estilo', !!data.warning || (Array.isArray(data) && data.some(r => r.error || r.warning))); setTimeout(() => { mensajeExito.classList.add('oculto'); mensajeExito.classList.remove('mensaje-warning-estilo'); }, 9000); }
                }
            })
            .catch(error => {
                console.error('Error en fetch o procesamiento:', error);
                // No resetear folio si hay error
                if (mensajeErrorEnvio) { mensajeErrorEnvio.textContent = `Error: ${error.message || 'Error de red o del servidor.'}`; mensajeErrorEnvio.classList.remove('oculto'); setTimeout(() => { mensajeErrorEnvio.classList.add('oculto'); }, 8000); }
            });
        }); // Fin submit listener
    } // Fin if form

    // --- Inicialización Final ---
    if (fechaInput && !fechaInput.value) fechaInput.valueAsDate = new Date();
    updateDimensionLogic();
    handleProveedorChange(); // Asegura UI inicial

}); // Fin DOMContentLoaded