// static/js/dashboard_compras.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a elementos DOM ---
    const solicitudesTable = document.getElementById('solicitudes-table-compras'); // La tabla de solicitudes de Compras
    // Puedes tener un div específico para mensajes de feedback de AJAX de actualización si no confías en los mensajes flash
    // const updateFeedbackDiv = document.getElementById('compras-update-feedback');


    // --- Event Listeners ---

    // Añadir listener a la tabla para delegar eventos de los selects de estatus
    // Esto es más eficiente que añadir un listener a cada select individualmente,
    // especialmente si la tabla es grande o se carga contenido dinámicamente.
    if (solicitudesTable) {
        solicitudesTable.addEventListener('change', function(event) {
            const target = event.target;

            // Verificar si el elemento que disparó el evento es un select con clase 'update-estatus-select'
            if (target.classList.contains('update-estatus-select')) {
                const selectElement = target;
                const newStatus = selectElement.value; // Obtener el nuevo estatus seleccionado
                const row = selectElement.closest('tr'); // Obtener la fila (tr) a la que pertenece este select
                const pageId = row ? row.getAttribute('data-page-id') : null; // Obtener el page-id del atributo data-page-id de la fila

                // Verificar que tenemos un page ID y un estatus seleccionado válido
                if (pageId && newStatus) {
                    console.log(`Intentando actualizar estatus para page ID: ${pageId} a "${newStatus}"`);
                    // Llamar a la función para enviar la solicitud de actualización
                    updateSolicitudStatus(pageId, newStatus, row); // Pasar también la fila para actualizar la UI
                } else if (!newStatus) {
                    console.log("Select de estatus cambiado, pero el valor es vacío o inválido.");
                    // El usuario seleccionó la opción disabled/empty
                    // Opcional: mostrar un mensaje al usuario
                } else {
                    console.warn("No se pudo obtener page ID para actualizar estatus.");
                    // Opcional: mostrar un mensaje de error al usuario (ej: usando un div de feedback)
                }
            }
             // Puedes añadir listeners para botones si usas botones en lugar de selects para confirmar
             // else if (target.classList.contains('confirm-status-btn')) { ... }
        });
    } else {
        console.error("Tabla de solicitudes #solicitudes-table-compras no encontrada.");
        // Puedes mostrar un mensaje de error si la tabla no se encuentra
    }


    // --- Funciones ---

    // Función para enviar la solicitud de actualización de estatus via AJAX al backend
    function updateSolicitudStatus(pageId, newStatus, rowElement) {
        // Construir la URL para la ruta de actualización en el backend
        // Asegúrate de que el endpoint coincide con la ruta en compras.py: /compras/update_solicitud_status/<string:page_id>
        const updateUrl = `/compras/update_solicitud_status/${pageId}`; // La URL es /compras/update_solicitud_status/page_id

        // Datos a enviar en el cuerpo de la solicitud (JSON)
        // El backend espera {"properties": {"Estatus": {"select": {"name": "Nuevo Estatus"}}}}
        const propertiesToUpdate = {
            "Estatus": {"select": {"name": newStatus}} // <<< Asegúrate de que "Estatus" coincide con el nombre de la propiedad en tu DB Notion
            // Si tu propiedad de estatus es tipo Status: {"Status": {"name": newStatus}}
            // Si necesitas actualizar más propiedades, inclúyelas aquí.
        };

        const requestBody = {
            properties: propertiesToUpdate
        };


        // Opcional: Mostrar un indicador visual de carga en la fila o en un área de mensajes
        if (rowElement) {
             rowElement.classList.add('updating'); // Añadir clase CSS para indicar que se está actualizando
             // Deshabilitar el select temporalmente
             const selectElement = rowElement.querySelector('.update-estatus-select');
             if(selectElement) selectElement.disabled = true;
             // Ocultar el texto de estatus actual para que solo se vea el select (opcional)
             // const statusTextSpan = rowElement.querySelector('.current-estatus-text');
             // if(statusTextSpan) statusTextSpan.style.display = 'none';
        }
        // if(updateFeedbackDiv) { updateFeedbackDiv.textContent = 'Actualizando...'; updateFeedbackDiv.classList.remove('success', 'error'); updateFeedbackDiv.classList.add('processing'); }


        fetch(updateUrl, {
            method: 'POST', // Usar método POST según la ruta del backend
            headers: {
                'Content-Type': 'application/json', // Indicar que enviamos JSON
            },
            body: JSON.stringify(requestBody) // Convertir el objeto de datos a string JSON
        })
        .then(response => {
            // Opcional: Eliminar indicador visual de carga
            if (rowElement) rowElement.classList.remove('updating');
            // if(updateFeedbackDiv) updateFeedbackDiv.classList.remove('processing');

             // Re-habilitar el select si hubo un error
             const selectElement = rowElement ? rowElement.querySelector('.update-estatus-select') : null;


            if (!response.ok) {
                // Si la respuesta no es OK (ej. 400, 500), lanzar error
                return response.json().then(errData => {
                     let msg = errData.error || `Error: ${response.status}`;
                     // Incluir detalles si existen (por ejemplo, del backend)
                     if(errData.details) msg += `: ${errData.details}`;
                     // Incluir mensaje de Notion API si viene
                     if(errData.notion_message) msg += ` (Notion: ${errData.notion_message})`;

                     throw new Error(msg); // Lanzar error con mensaje construido
                }).catch(() => {
                    // Si no se puede parsear JSON de error
                    throw new Error(`Error ${response.status}: ${response.statusText}`);
                });
            }
            // Si la respuesta es OK (200, 207), procesar éxito
            return response.json();
        })
        .then(data => {
            console.log('Actualización exitosa:', data);
            // Actualizar la UI de la fila en el frontend
            if (rowElement) {
                // Buscar la celda del estatus
                const statusCell = rowElement.querySelector('.solicitud-estatus-celda');
                if (statusCell) {
                    // Buscar el span que muestra el estatus actual
                    const statusTextSpan = statusCell.querySelector('.current-estatus-text');
                    if(statusTextSpan) statusTextSpan.textContent = newStatus; // Actualizar el texto del estatus
                    // Opcional: Remover la clase oculto del span si se ocultó
                    // if(statusTextSpan) statusTextSpan.style.display = '';

                     // Opcional: Aplicar una clase CSS a la celda o fila basada en el nuevo estatus
                     // rowElement.classList.remove('status-pendiente', 'status-en-proceso', ...);
                     // rowElement.classList.add(`status-${newStatus.toLowerCase().replace(/\s/g, '-')}`);
                }
                 // Re-habilitar el select y resetear su valor al estatus recién actualizado
                const selectElement = rowElement.querySelector('.update-estatus-select');
                if(selectElement) {
                    selectElement.value = ""; // Resetear al valor por defecto (Cambiar Estatus)
                    selectElement.disabled = false; // Re-habilitar
                     // Opcional: seleccionar la opción que coincide con el nuevo estatus si no tienes la opción default "Cambiar Estatus"
                     // selectElement.value = newStatus;
                }

            }

            // Opcional: Mostrar un mensaje de éxito al usuario (usando mensajes flash de Flask o un div de feedback)
            // Si usas un div de feedback:
            // if(updateFeedbackDiv) { updateFeedbackDiv.textContent = data.message || 'Actualizado con éxito!'; updateFeedbackDiv.classList.add('success'); }
             // Si no usas un div de feedback, puedes usar alert() temporalmente
             // alert(`Actualizado: ${data.message || 'Con éxito'}`); // Temporal para depuración

        })
        .catch(error => {
            console.error('Error al actualizar estatus via AJAX:', error);
            // Eliminar indicador visual de carga
            if (rowElement) rowElement.classList.remove('updating');
             // Re-habilitar el select si hubo un error
             const selectElement = rowElement ? rowElement.querySelector('.update-estatus-select') : null;
             if(selectElement) selectElement.disabled = false;


            // Mostrar mensaje de error al usuario
            // Si usas un div de feedback:
            // if(updateFeedbackDiv) { updateFeedbackDiv.textContent = error.message || 'Error al actualizar estatus.'; updateFeedbackDiv.classList.add('error'); }
             // Si no usas un div de feedback, puedes usar alert() temporalmente
             alert(`Error al actualizar estatus: ${error.message || 'Error desconocido.'}`); // Temporal para depuración


        });
    }

}); // Fin DOMContentLoaded