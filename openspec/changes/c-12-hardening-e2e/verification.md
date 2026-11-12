# Verificación C-12

## Evidencia local

- Backend completo: 325 pruebas aprobadas con PostgreSQL 18 descartable y Redis simulado por TCP. Se detuvo el clúster al finalizar. La suite cubre reserva concurrente, cancelación fuera de ventana, agenda multisillón, webhook duplicado, pago rechazado y reintento ante fallas del proveedor de WhatsApp.
- Se comprobó el registro del evento inicial de una reserva directa y otra creada al aprobarse una seña. Las acciones posteriores conservan el historial de C-11. Los datos históricos previos a esa instrumentación no se reconstruyen.
- El reporte de higiene se probó con sesión de secretaría y odontología, rechazo de paciente y anónimo, fecha vacía y salida agregada.
- Ruff, formato de backend, build de la PWA, validación estricta de OpenSpec y revisión de whitespace aprobados. Los YAML de Compose y CI se validaron estructuralmente.
- Revisión de archivos versionados: el seed usa nombres y cuentas ficticios, no hay archivos de entorno con credenciales entre los rastreados y la búsqueda de patrones de claves privadas, tokens de GitHub y credenciales de producción de Mercado Pago no devolvió coincidencias.

- Playwright: 15 pruebas aprobadas en Chrome con API interceptada, incluidas agenda multisillón, navegación por teclado, cambio de rol, privacidad y modo offline a 360 y 1440 px. Los seis casos optativos contra backend se detectaron con `--list`.

## Verificación del cierre académico

- El proyecto `odonto-c12` arrancó en Ubuntu WSL 2 con Docker 29.1.3, Compose 2.40.3 y volúmenes nuevos. Los cuatro contenedores quedaron saludables. Desde Windows, `/api/health` devolvió PostgreSQL y Redis activos, y la PWA sirvió su manifiesto. Una consulta de solo lectura a `alembic_version` confirmó la revisión `005`, última del repositorio.
- Playwright contra Compose: 5 pruebas aprobadas y 2 omitidas. El recorrido por la interfaz verificó inicio de sesión desde una ruta protegida, restauración tras recarga y cierre de sesión. Las omisiones corresponden a reserva directa, conflicto y cancelación, que requieren datos de agenda.
- Pasaron TypeScript y los dos casos de Chrome sobre agenda, roles y privacidad a 360 y 1440 px con la API interceptada.
- La guía del piloto define proveedor simulado, pagador ficticio, política de seña por tratamiento y criterios de aceptación.

## Pendientes de aceptación

- Queda pendiente la ejecución remota del job de GitHub Actions.
- C-11 avanzó con la verificación local de agenda, roles, gestión, cobros y configuración contra Compose. El checklist integral de C-11 y el correctivo de sede siguen abiertos. C-10 requiere validación sandbox de Mercado Pago.


## Ejecución del piloto académico

- Con la API de Compose y los tres roles ficticios, se creó una reserva sin seña, se confirmó y se marcó asistida. El reporte pasó de un turno sin confirmar con alerta a cero y luego reflejó la asistencia. El historial incluyó creación, confirmación y asistencia. El paciente recibió 403 al intentar consultar el reporte.
- Checkout con seña, consulta del titular, aprobación con creación de turno y rechazo sin turno se comprobaron por integración con Mercado Pago simulado. El sandbox de C-10 sigue pendiente.
- El worker de WhatsApp consumió una cola aislada de Redis con proveedor ficticio. El primer envío falló, se reencoló y el segundo envío se persistió correctamente. Se observaron los estados fallido y enviado en PostgreSQL.
- La regresión final de backend pasó con 325 pruebas, PostgreSQL y Redis reales, con una base de pruebas separada de la demo.
