# turnos-odontologia — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| Frontend | React + TypeScript + Vite (PWA mobile-first) | React 18+, TS 5+, Vite 6+ |
| Backend | Python + FastAPI + JWT (Bearer) | Python 3.12+, FastAPI 0.115+ |
| ORM | SQLAlchemy 2.x (async) | 2.0+ |
| Base de datos | PostgreSQL | 16+ |
| Async / colas | Redis | 7+ |
| Contenedores | Docker / Docker Compose | Docker 24+ |
| Integraciones | WhatsApp plantillas Meta (a elegir proveedor) · Mercado Pago | API vigentes |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |

> ⚠️ Alta pendientes antes del primer change: password-vs-OTP paciente (IN-10-03) y proveedor WhatsApp + quién paga (IN-10-02/04).

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / async / Postgres / TDD | `fastapi-templates`, `fastapi`, `async-python-patterns`, `supabase-postgres-best-practices`, `postgresql-table-design`, `tdd`, `turnos-core-guardian` (skill propia — invariantes núcleo) |
| **Backend Aux** | Seguridad / integraciones / deploy | `security-and-hardening`, `docker-patterns` (⚠️ flag Snyk High Risk: revisar Dockerfiles línea por línea) |
| **Frontend** | React / TS / Vite PWA + testing | `vercel-react-best-practices`, `web-design-guidelines`, `frontend-design`, `typescript-advanced-types`, `vite`, `webapp-testing` |
| **Calidad** | Debug / review / E2E | `diagnosing-bugs`, `code-review`, `playwright-cli`, `e2e-testing-patterns` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

### Skill propia: `turnos-core-guardian`

- **Ubicación:** `.agents/skills/turnos-core-guardian/` (`SKILL.md`, `references/`, `scripts/check_turnos_invariants.py`).
- **Cuándo usarla:** al crear o revisar modelos SQLAlchemy, migraciones Alembic, constraints `EXCLUDE`, montos en centavos, fechas `TIMESTAMPTZ`, seeds (changes C-02, C-04, C-05, C-06). No aplica a WhatsApp (C-08), Mercado Pago (C-09) ni UI (C-10/C-11).
- **Qué necesita:** archivos de modelos (`backend/app/models/*.py`), migraciones (`backend/alembic/versions/*.py`), seeds o artefactos de diseño del change.
- **Cómo revisar el resultado:** el agente emite `Veredicto Guardian: OK / BLOQUEADO` con detalle por categoría (EXCLUDE, invariantes, seeds). Si es `BLOQUEADO`, corregir antes de avanzar. Las reglas duras de este archivo prevalecen ante cualquier contradicción.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 12 changes en 6 fases (FASE 0 cimientos → FASE 5 cierre MVP).
- **Camino crítico** (8): C-01 → C-02 → C-03 → C-04 → C-05 → C-06/C-07 → C-09 → C-11 → C-12.
- **Primer change**: `C-01` (`foundation-setup`).
- **Corazón de agenda**: `C-05` (`disponibilidad-reserva`, RN-TU-01).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> No hay `~/.claude/CLAUDE.md` global en esta máquina: las reglas universales viven acá hasta que exista uno. Son contrato; romperlas es un defecto.

**Universales:**
- NUNCA commitear, buildear imágenes finales ni pushear sin pedido explícito → proponer y esperar.
- NUNCA commitear sin `git status`/`git diff` revisados → solo archivos intencionales, jamás secretos.
- Commits en formato conventional commits, sin co-autoría IA en el mensaje.

**Específicas del proyecto (confirmadas 2026-10-06):**
- NUNCA doble reserva solo a nivel UI → constraint `EXCLUDE` en Postgres a nivel motor (RN-TU-01).
- NUNCA confiar en el cliente para reglas críticas → ventana 2 h y validaciones en backend aunque la UI no las pida (RN-TU-02, RN-GL-01).
- NUNCA dinero en float → centavos ARS / `NUMERIC`, jamás tipo `money` (RN-CO-03).
- NUNCA fechas naive → siempre `TIMESTAMPTZ` en agenda y turnos.
- NUNCA `any` en TypeScript → tipado estricto, componentes en PascalCase.
- NUNCA secretos en el repo → WA/MP/JWT solo por variables de entorno.
- NUNCA datos reales de pacientes en el repositorio ni en los ejemplos → seeds y fixtures siempre ficticios (RN-GL-02).
- NUNCA bloquear el event loop → async puro, timeouts explícitos, trabajo pesado fuera del loop (workers Redis).
- NUNCA usar Dockerfiles/Compose generados sin revisión → lectura línea por línea antes de buildear (flag Snyk en `docker-patterns`).

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md            → respetar dependencias
3. /opsx:propose C-NN-nombre                      → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)        → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]         → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
