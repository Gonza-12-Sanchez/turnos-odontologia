# Evidencia de apply

## Preparación — 2026-11-11

`openspec instructions apply --change c11-contexto-consultorio --json`: estado
ready, 0/5 tareas. El usuario solicitó aplicar el correctivo expresamente.

Comprobaciones locales sin cambiar datos:

- `docker version --format '{{.Server.Version}}'`: falló porque `docker` no está
  disponible en PATH; la ubicación estándar de Docker Desktop tampoco existe.
- `python -c "import fastapi, sqlalchemy, pytest; ..."`: falló por ausencia de
  SQLAlchemy en el Python global; no hay `python.exe` de venv en el repositorio.
- Hay PostgreSQL 18 instalado y su servicio existente está iniciado; no es una
  instancia descartable creada por esta sesión y **no se usó**. `initdb.exe`
  existe, pero aún no hay instancia aislada validada ni Redis descartable.
- `backend/tests/conftest.py` ejecuta `TRUNCATE TABLE ... CASCADE` al cerrar la
  fixture de sesión; el nombre `turnos_test` por sí solo no acredita aislamiento.

No se ejecutaron pruebas backend, no se alteraron bases ni se modificó código.
La tarea1.1 exige TDD HTTP sobre PostgreSQL descartable y el plan exige Redis
descartable para RBAC real. No se marca ninguna tarea completa ni G-contexto
satisfecho. Se necesita disponer de un entorno aislado para continuar.

## Implementación y pruebas — 2026-11-12

- El endpoint devuelve el único consultorio activo con id y nombre, o null si el contexto es ambiguo. La respuesta tiene Cache-Control: no-store. La PWA obtiene el contexto de esa ruta antes de enviar el alta.
- Se ejecutaron cuatro pruebas HTTP de contexto, permisos y alta contra un clúster descartable de PostgreSQL 18. Los casos cubren sede única, cero y dos activas, sede inactiva, alta del primer sillón con auditoría y rechazo tras desactivar el consultorio. Se simuló Redis por TCP en un puerto efímero.
- La UI tiene pruebas DOM/HTTP de sede válida y contexto ausente. Ambos changes pasaron la validación estricta de OpenSpec. Sigue pendiente la aceptación con Redis real y navegador integrado.
