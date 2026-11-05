---
name: project-test-runner
description: Levanta el proyecto turnos-odontologia completo (db + redis + api + frontend) para dos objetivos: modo prueba (con datos ficticios para probar funcionalidades) o modo real (sin datos ficticios, para usar con datos reales). Verifica que Docker esté instalado, crea los contenedores, aplica migraciones, carga seeds ficticios si es modo prueba, y verifica health checks. Trigger cuando el usuario dice "levantar el proyecto", "correr tests", "preparar entorno de prueba", "levantar para probar", "levantar frontend y swagger", "levantar proyecto para realizar pruebas".
---

# Project Test Runner

Skill para levantar el proyecto completo de turnos-odontologia (db + redis + api + frontend)
en dos modos: **prueba** (con datos ficticios) o **real** (sin datos ficticios).

## Cuándo usar

Usa esta skill cuando:
- El usuario pide "levantar el proyecto", "correr tests", "preparar entorno de prueba"
- El usuario pide "levantar para probar", "levantar frontend y swagger"
- El usuario pide "levantar proyecto para realizar pruebas"
- El usuario quiere probar funcionalidades con datos ficticios
- El usuario quiere usar el proyecto con datos reales

No la uses para:
- Levantar solo un servicio individual (usar `docker compose up -d <servicio>` directamente)
- Debugging de un contenedor específico
- Producción (este compose es solo para desarrollo)

## Modos de operación

### Modo prueba (con datos ficticios)
1. Levantar todos los contenedores
2. Aplicar migraciones
3. Cargar seed ficticio (`backend/app/db/seed.py`)
4. Verificar health checks
5. Informar URLs de acceso
6. Al finalizar: limpiar datos ficticios (rollback de migraciones o drop+recreate)

### Modo real (sin datos ficticios)
1. Levantar todos los contenedores
2. Aplicar migraciones
3. NO cargar seed
4. Verificar health checks
5. Informar URLs de acceso

## Procedimiento

### Paso 1: Verificar Docker

```bash
docker --version
docker ps
```

- Si Docker no está instalado: indicar al usuario que instale Docker Desktop desde https://www.docker.com/products/docker-desktop
- Si Docker está instalado pero no corriendo: indicar que inicie Docker Desktop
- Si Docker está corriendo: continuar

### Paso 2: Levantar contenedores

```bash
cd <repo-root>
docker compose up -d
```

Esperar a que todos los contenedores estén healthy:
```bash
docker compose ps
```

Los 4 servicios deben estar: `db`, `redis`, `api`, `frontend`.

### Paso 3: Aplicar migraciones

```bash
docker compose exec api alembic upgrade head
```

O desde el host (si los puertos están mapeados):
```bash
cd backend
alembic upgrade head
```

### Paso 4: Cargar datos (solo modo prueba)

```bash
docker compose exec api python -m app.db.seed
```

O desde el host:
```bash
cd backend
python -m app.db.seed
```

### Paso 5: Verificar health checks

```bash
curl http://localhost:8000/api/health
# Debe devolver: {"status":"ok","checks":{"db":"up","redis":"up"}}
```

### Paso 6: Informar URLs de acceso

- **Frontend (PWA):** http://localhost:4173
- **Swagger (API docs):** http://localhost:8000/docs
- **API base:** http://localhost:8000/api
- **Health check:** http://localhost:8000/api/health

### Paso 7: Limpiar datos ficticios (AUTOMÁTICO al finalizar modo prueba)

**Se ejecuta automáticamente cuando el usuario indica que terminó de probar.** No requiere intervención manual.

**Este paso se ejecuta automáticamente al finalizar el modo prueba.** No requiere intervención manual.

```bash
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

O desde el host:
```bash
cd backend
alembic downgrade base
alembic upgrade head
```

Esto elimina todos los datos (incluyendo seeds ficticios) y recrea el schema vacío.

**IMPORTANTE:** Si el usuario dice "limpiá los datos de prueba" o "terminé de probar", ejecutar este paso automáticamente sin preguntar. Si el usuario dice "no limpies" o "dejá los datos", omitir este paso.

## Resultado esperado

- Todos los contenedores corriendo y healthy
- Health check `/api/health` → `{"status":"ok"}`
- Frontend accesible en `http://localhost:4173`
- Swagger accesible en `http://localhost:8000/docs`
- En modo prueba: seed cargado y tests pasando
- En modo real: sin datos ficticios residuales

## Criterios de revisión

- [ ] Todos los contenedores corriendo y healthy
- [ ] Health check OK
- [ ] En modo prueba: seed cargado, tests pasando
- [ ] En modo real: sin datos ficticios residuales
- [ ] Frontend accesible
- [ ] Swagger accesible

## Ejemplos

**Ejemplo 1 — Levantar para pruebas (modo prueba):**
Usuario: "Levantá el proyecto para realizar pruebas"
Agente: Verifica Docker → levanta contenedores → aplica migraciones → carga seed → verifica health → informa URLs.

**Ejemplo 2 — Levantar sin datos (modo real):**
Usuario: "Levantá el proyecto"
Agente: Verifica Docker → levanta contenedores → aplica migraciones → NO carga seed → verifica health → informa URLs.

**Ejemplo 3 — Limpiar datos de prueba:**
Usuario: "Limpiá los datos de prueba"
Agente: Ejecuta downgrade + upgrade de migraciones → schema vacío, sin datos ficticios.

## Límites
- No usar en producción: el compose es solo para desarrollo
- Las credenciales (`turnos`/`turnos`) son ficticias de desarrollo; cambiar en producción
- El seed carga datos ficticios (`@example.com`, teléfonos 0000) — nunca datos reales
- Si un contenedor falla al levantar, reportar el error y no continuar
- Si Docker no está instalado, indicar al usuario cómo instalarlo (no instalar automáticamente)