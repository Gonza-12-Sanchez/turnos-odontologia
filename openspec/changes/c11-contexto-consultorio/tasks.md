# Tasks

## 1. Contexto administrativo

- [x] 1.1 Implementar GET `/api/config/contexto-consultorio` con respuesta tipada, sin caché y consulta limitada a dos consultorios activos; TDD HTTP en Postgres descartable para cero, uno sin sillones, dos, inactivos y error de lectura, sin escoger un registro arbitrario. Casos de sede y permisos verificados. Un error de lectura inyectado devolvió 500 sin publicar contexto.
- [x] 1.2 Probar RBAC real: anónimo401, paciente/odontólogo403, secretaria200; comprobar que solo expone id/nombre, sin cambios a auth ni a base existente; documentar contrato y límites de sede única.
- [x] 1.3 Verificar primer POST de sillón usando el id devuelto, rechazo si consultorio se desactiva y auditoría existente en Postgres descartable; ejecutar regresión del catálogo y documentar evidencia sin datos reales.

## 2. Integración con C-11

- [x] 2.1 Registrar evidencia y versión de contrato en C-11; habilitar su tarea3.4 solo tras aprobación de G-contexto y pruebas reales aisladas, sin marcarla completa por implementar únicamente el endpoint.
- [x] 2.2 Ejecutar validación OpenSpec estricta, lint y pruebas apropiadas; registrar comandos, entorno y resultados, sin afirmar pruebas omitidas ni construir imágenes finales sin autorización.

## Workflow follow-up

- Mantener C-11 abierto y sus demás gates independientes; no archivar sin revisión.
