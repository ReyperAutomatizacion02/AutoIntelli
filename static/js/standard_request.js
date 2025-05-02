// static/js/standard_request.js

// Este script asume que las siguientes variables globales se definen en la plantilla HTML
// const STANDARD_DIMENSIONS_URL = "{{ url_for('static', filename='data/standard_dimensions_by_unit.json') }}";
// NOTA: No necesitas TORNI_MASTERLIST_URL en este script


document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a elementos DOM ---
    const materialForm = document.getElementById('standard-material-form'); // ID del formulario estándar
    const responseMessageDiv = document.getElementById('response-message'); // Div para feedback AJAX

    // NOTA: Elimina referencias a elementos de Torni aquí
    // const torniTableContainer = document.getElementById('torni-table-container');
    // const torniTableBody = document.getElementById('torni-items-tbody');
    // const addTorniItemBtn = document.getElementById('add-torni-item-btn');

    const proveedorSelect = document.getElementById('proveedor'); // Campo proveedor (común, pero usado aquí)
    const materialSelect = document.getElementById('nombre_material'); // Dropdown dependiente
    const tipoMaterialSelect = document.getElementById('tipo_material'); // Dropdown dependiente
    const fechaInput = document.getElementById('fecha_solicitud'); // Campo fecha (común)

    // Campos estándar
    const cantidadSolicitadaInput = document.getElementById('cantidad_solicitada');
    const unidadMedidaSelect = document.getElementById('unidad_medida'); // Usado para datalist
    const dimensionDatalist = document.getElementById('dimensionList'); // Datalist
    const largoInput = document.getElementById('largo'); // Dimensiones
    const anchoInput = document.getElementById('ancho');
    const altoInput = document.getElementById('alto');
    const diametroInput = document.getElementById('diametro');
    const dimensionesContainer = document.getElementById('dimensiones-container'); // Contenedor de dimensiones

    // Campos comunes restantes
    const nombreSolicitanteInput = document.getElementById('nombre_solicitante');
    const departamentoAreaSelect = document.getElementById('departamento_area');
    const proyectoInput = document.getElementById('proyecto'); // Asumo ID 'proyecto' y name 'Proyecto' (OJO mayúscula si es así)
    const especificacionesAdicionalesInput = document.getElementById('especificaciones_adicionales');
    const folioDisplayValue = document.getElementById('folio-display-value'); // Folio display
    const folioInputHidden = document.getElementById('folio_solicitud'); // Folio oculto


    // --- Variables Globales del Script ---
    let allStandardDimensions = {}; // Para dimensiones estándar (cargado de JSON)
    // NOTA: Elimina torniMasterList aquí
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

    // --- Lógica Interdependiente de Dimensiones ---
    // Mantén esta lógica tal cual si usa los mismos IDs de input
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


    // --- Lógica Dropdowns Dependientes (Proveedor y Material) ---
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
            actualizarTipoMaterial();
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
            tipoMaterialSelect.disabled = false;
        } else {
            tipoMaterialSelect.value = "";
            tipoMaterialSelect.disabled = true;
        }
    }

    // --- Lógica Tabla Torni (ELIMINAR ESTO) ---
    // Las funciones addTorniRow, deleteTorniRow, y la lógica de Awesomplete NO van aquí.


    // --- Lógica de UI basada en Proveedor (ADAPTAR) ---
    // Esta función en el formulario estándar solo necesita resetear los campos si el proveedor cambia.
    // No necesita manejar la visibilidad de secciones Torni o estándar, ya que este form SIEMPRE es estándar.
     function handleProveedorChange() {
        if (!proveedorSelect || !materialSelect || !tipoMaterialSelect || !cantidadSolicitadaInput || !unidadMedidaSelect || !largoInput || !anchoInput || !altoInput || !diametroInput) {
             console.error("Faltan elementos DOM para handleProveedorChange."); return;
        }

        const selectedProveedor = proveedorSelect.value;

        // Recargar materiales y tipo según el proveedor seleccionado
        actualizarMateriales();
        updateDatalistForUnit(); // Asegura que datalist se pobla para la unidad seleccionada

        // Limpiar valores de campos estándar (opcional, o solo limpiar dropdowns dependientes)
        // cantidadSolicitadaInput.value = '1'; // Mantener default 1
        // unidadMedidaSelect.value = ''; // Esto ya lo hace actualizarMateriales indirectamente si cambia proveedor

        // Limpiar campos de dimensiones (opcional, o manejado por updateDimensionLogic)
        // largoInput.value = ''; anchoInput.value = ''; altoInput.value = ''; diametroInput.value = '';
        updateDimensionLogic(); // Asegura que las reglas de dimensiones se aplican al estado inicial

     }


    // --- Función para Recolectar TODOS los Datos del Formulario Estándar ---
    // Recolecta solo los campos presentes en este formulario (estándar + comunes)
    function collectFormData() {
        const data = {};
        const form = materialForm;

        // Recolectar todos los campos con name que no estén deshabilitados
        form.querySelectorAll('input, select, textarea').forEach(input => {
             if (input.name && !input.disabled) {
                  if (input.type === 'number') {
                       data[input.name] = parseFloat(input.value) || 0;
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
        });

        // Asegurarse de que el proveedor siempre se incluya (debería estar habilitado)
         if (proveedorSelect && proveedorSelect.name && !proveedorSelect.disabled) {
              data[proveedorSelect.name] = proveedorSelect.value;
         }

        console.log('Datos recolectados para JSON (Estándar):', data);
        return data;
    }


    // --- Función para Configurar el Envío del Formulario (Fetch API) ---
    function setupFormSubmitListener() {
        if (!materialForm) {
             console.error("Formulario #standard-material-form no encontrado.");
             if(responseMessageDiv){
                  responseMessageDiv.textContent = `Error interno: Formulario principal no encontrado.`;
                  responseMessageDiv.classList.add('error');
             }
             return;
        }

       materialForm.addEventListener('submit', function(event) {
           event.preventDefault();

           const form = event.target;

           // 1. Validación (Solo validación básica del frontend aquí, el backend valida completamente)
           // La validación detallada de campos obligatorios se puede hacer aquí si se desea,
           // pero el backend ya lo hace. Validaremos si hay al menos un proveedor seleccionado.

           // Limpiar errores visuales y mensajes anteriores
            form.querySelectorAll('.error-field').forEach(el => el.classList.remove('error-field'));
            if (responseMessageDiv) {
                 responseMessageDiv.textContent = '';
                 responseMessageDiv.classList.remove('processing', 'success', 'error');
            }

           const selectedProvider = proveedorSelect ? proveedorSelect.value : null;

           if (!selectedProvider || selectedProvider === '') {
               console.log("Validación fallida: Proveedor no seleccionado.");
               if (responseMessageDiv) {
                   responseMessageDiv.textContent = "Por favor, selecciona un proveedor.";
                   responseMessageDiv.classList.add('error');
               }
               if(proveedorSelect) proveedorSelect.classList.add('error-field');
               return; // Detener el submit
           }


           const datosSolicitud = collectFormData(); // Recolectar todos los datos estándar

           // 2. Fetch al backend
           console.log('Validación básica exitosa. Datos del formulario a enviar:', datosSolicitud);

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
                          if(errData.details) msg += `: ${errData.details}`;
                          if(errData.notion_error) msg += ` (Notion: ${errData.notion_error.message})`;

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


               if (responseMessageDiv) {
                   responseMessageDiv.innerHTML = feedbackMessage + (firstUrl ? ` <a href="${firstUrl}" target="_blank" rel="noopener noreferrer">Ver Registro</a>` : '');
                   responseMessageDiv.classList.remove('success', 'error');
                   if (isSuccess) {
                       responseMessageDiv.classList.add('success');
                   } else {
                       responseMessageDiv.classList.add('error');
                   }
               }

               // Resetear formulario y UI solo si fue éxito total o parcial (isSuccess es true)
               if (isSuccess) {
                   form.reset();
                   currentFolio = generateFolio(); updateFolioDisplay(currentFolio);
                   // Llama a handleProveedorChange para resetear dropdowns dependientes, etc.
                   handleProveedorChange();

                   // Restablecer fecha por defecto
                    if(fechaInput && !fechaInput.value) {
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

    // Deshabilitar el botón de submit inicialmente
    if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;


    // Carga de Datos (LLAMA A fetch, que en su .then llama a funciones para inicializar UI)
    if (typeof STANDARD_DIMENSIONS_URL !== 'undefined') { // Solo necesitas STANDARD_DIMENSIONS_URL aquí
        fetch(STANDARD_DIMENSIONS_URL)
        .then(res => {
             if (!res.ok) throw new Error(`Dimensiones: ${res.status} ${res.statusText}`);
             return res.json();
         }).catch(error => { console.error("Error en fetch de Dimensiones:", error); throw error; })
        .then(dimensionsData => {
            console.log("Datos iniciales cargados con éxito (Dimensiones).");
            allStandardDimensions = dimensionsData;

            // --- Llamadas a funciones para inicializar la UI *después* de cargar los datos ---
            handleProveedorChange(); // Configura UI inicial, llama a actualizarMateriales y updateDatalistForUnit

             // Asegurar que el botón de submit esté habilitado
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
         console.error("URLs para datos iniciales (JSON estáticos) no definidas (Dimensiones).");
         if(responseMessageDiv){
              responseMessageDiv.textContent = `Error: URLs de datos iniciales no configuradas en la plantilla HTML.`;
              responseMessageDiv.classList.add('error');
         }
         if(materialForm) materialForm.querySelector('button[type="submit"]').disabled = true;
    }


    // --- Event Listeners ---
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

    // El botón añadir/eliminar filas Torni y la lógica de Awesomplete NO van aquí.

    setupFormSubmitListener(); // Configura el listener del submit

    // Establecer fecha por defecto inicialmente
    if (fechaInput && !fechaInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        const month = ('0' + (today.getMonth() + 1)).slice(-2);
        const day = ('0' + today.getDate()).slice(-2);
        fechaInput.value = `${year}-${month}-${day}`;
    }


}); // Fin DOMContentLoaded