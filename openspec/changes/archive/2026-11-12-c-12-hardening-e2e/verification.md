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

## Estado de CI y dependencias

- [GitHub Actions #43298806887](https://github.com/Gonza-12-Sanchez/turnos-odontologia/actions/runs/43298806887) pasó en el commit 09cd874: backend, frontend y compose-smoke. Los jobs frontend y compose-smoke fijan Ubuntu 24.04 en ci.yml para evitar el fallo de instalación de Chromium con Playwright 1.56.1 en Ubuntu 26.04.
- C-11 se archivó el 2026-11-12 con 30/30 tareas y la especificación gestion-pwa consolidada. El correctivo de sede tiene 5/5 tareas verificadas y conserva su change separado.
- C-10 está archivado y su tarea 8.2 sigue pendiente de una cuenta de pruebas de Mercado Pago autorizada. El piloto académico usa el adaptador simulado. El usuario confirmó el cierre exclusivamente académico, por lo que el sandbox queda fuera de C-12.


## Ejecución del piloto académico

- Con la API de Compose y los tres roles ficticios, se creó una reserva sin seña, se confirmó y se marcó asistida. El reporte pasó de un turno sin confirmar con alerta a cero y luego reflejó la asistencia. El historial incluyó creación, confirmación y asistencia. El paciente recibió 403 al intentar consultar el reporte.
- Checkout con seña, consulta del titular, aprobación con creación de turno y rechazo sin turno se comprobaron por integración con Mercado Pago simulado. El sandbox de C-10 sigue pendiente.
- El worker de WhatsApp consumió una cola aislada de Redis con proveedor ficticio. El primer envío falló, se reencoló y el segundo envío se persistió correctamente. Se observaron los estados fallido y enviado en PostgreSQL.
- La regresión final de backend pasó con 325 pruebas, PostgreSQL y Redis reales, con una base de pruebas separada de la demo.

## Revisión final de CI y trazabilidad

- GitHub Actions #43298806887 pasó en el commit 09cd874. Se confirmó Chromium en frontend y compose-smoke, además de migraciones y la sesión contra Compose. Esta ejecución precede a las últimas modificaciones locales.
- La regresión local completa de backend obtuvo 338 pruebas aprobadas con PostgreSQL y Redis reales en el entorno de prueba separado. Ruff y su verificación de formato también pasaron.
- Se agregaron seis casos HTTP que comprueban la persistencia de la acción, el actor, la fecha con zona y el origen de confirmación, cancelación, reprogramación, ausencia, sobreturno y cambio de origen. La suite también comprueba creación directa, creación tras pago simulado y asistencia. Los intentos fuera de ventana conservan el turno y el historial.
- La trazabilidad del piloto académico quedó verificada. El sandbox de C-10 requiere configuración de prueba autorizada y permanece como pendiente separado de C-10. Con el alcance académico confirmado, se cierra la tarea 2.3.

## Revisión del repositorio del equipo — 2026-11-13

- Base revisada: 3cc0c25. Compose levantó los cuatro servicios con volúmenes de prueba separados y migración 005 en head.
- Backend: 338 pruebas aprobadas con PostgreSQL y Redis reales. Ruff sin hallazgos. Frontend: 208 pruebas aprobadas, TypeScript y build correctos.
- Playwright: 15 casos con API interceptada contra el build local y 5 casos contra Compose. Los dos escenarios marcados skip se verificaron aparte con datos ficticios: reserva 201 desde Chrome, reserva duplicada 409 y cancelación dentro de dos horas 422 por HTTP real.
- Se ajustó la prueba de reconexión para esperar la consulta de disponibilidad. GitHub Actions #43434644029 pasó sobre 3cc0c25, antes de los ajustes locales de esta revisión.
- Se archivó el correctivo de sede y se validaron las 14 especificaciones canónicas con OpenSpec estricto.
