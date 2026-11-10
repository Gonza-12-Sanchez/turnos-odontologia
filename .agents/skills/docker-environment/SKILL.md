# Skill: docker-environment

Levanta el entorno completo de Docker para el proyecto `turnos-odontologia` (db + redis + api + frontend), aplica migraciones, carga seeds ficticios y verifica health checks. Diseñada para modo prueba y modo real.

## Trigger

Cuando el usuario dice:
- "levantar el proyecto con docker"
- "levantar entorno de prueba docker"
- "levantar backend y frontend con docker compose"
- "docker compose up para turnos"
- "levantar contenedores turnos-odontologia"

## Qué hace esta skill

1. Verifica que Docker Desktop esté corriendo (WSL2 backend).
2. Levanta los servicios definidos en `docker-compose.yml`:
   - `db`: PostgreSQL 16 (puerto 5432)
   - `redis`: Redis 7 (puerto 6379)
   - `api`: FastAPI backend (puerto 8000)
   - `frontend`: Vite/React PWA (puerto 4173)
3. Aplica migraciones Alembic contra la base de datos.
4. Carga seeds ficticios (modo prueba) o deja lista para datos reales (modo real).
5. Verifica health checks de todos los servicios.
6. Reporta URLs de acceso y comandos útiles.

## Modos

| Modo | Datos | Uso |
|------|-------|-----|
| `prueba` | Seeds ficticios (RN-GL-02, nunca datos reales) | Testing, validación de funcionalidades |
| `real` | Sin datos ficticios | Piloto con datos reales del consultorio |

## Archivos de referencia

- `docker-compose.yml` — definición de servicios
- `backend/.env.example` — variables de entorno del backend
- `frontend/.env.example` — variables de entorno del frontend
- `backend/alembic/` — migraciones
- `knowledge-base/08_arquitectura_propuesta.md` — variables de entorno

## Reglas duras aplicables

- NUNCA commitear, buildear imágenes finales ni pushear sin pedido explícito.
- NUNCA secretos en el repo — WA/MP/JWT solo por variables de entorno.
- NUNCA datos reales de pacientes en el repo — seeds siempre ficticios (RN-GL-02).
- NUNCA usar Dockerfiles/Compose generados sin revisión línea por línea.

## Flujo de ejecución

```
1. Verificar Docker Desktop (WSL2 docker-desktop running)
2. docker compose up -d db redis    (infraestructura primero)
3. Esperar health checks de db y redis
4. docker compose up -d api         (backend)
5. Aplicar migraciones: alembic upgrade head
6. Cargar seeds (solo modo prueba)
7. docker compose up -d frontend    (frontend)
8. Verificar health check de api y frontend
9. Reportar URLs y estado
```

## Comandos generados por la skill

```bash
# Levantar todo (modo prueba con seeds)
docker compose up -d
cd backend && alembic upgrade head
# cargar seeds ficticios según scripts del proyecto

# Ver estado
docker compose ps
docker compose logs -f api

# Parar
docker compose down

# Parar y borrar volúmenes (cuidado: borra datos)
docker compose down -v

# Solo infraestructura (db + redis) para tests de backend
docker compose up -d db redis
```

## Engram

Guardar con `mem_save`:
- project: "turnos-odontologia"
- topic_key: "opsx/docker-environment/skill"
- title: "Creada skill docker-environment para levantar entorno Docker del proyecto"