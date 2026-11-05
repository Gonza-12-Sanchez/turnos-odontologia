# Evidencia: invocación del MCP PostgreSQL

**Fecha:** 2026-10-28
**Servidor:** `@modelcontextprotocol/server-postgres` (configurado en `~/.config/opencode/opencode.json`, `mcp.postgres`)

## Solicitud realizada

```
Usa la herramienta postgres para ejecutar:
SELECT current_database() AS db, current_user AS usuario, version() AS version;
```

## Resultado obtenido

```
postgres_query {"sql":"SELECT current_database() AS db, current_user AS usuario, version() AS version;"}
db: `turnos_test` · usuario: `turnos` · PostgreSQL 17.10 (x86_64-windows).
```

## Qué aportó al proyecto

Confirmó que el MCP está operativo y conectado a la base de desarrollo `turnos_test`
con el usuario `turnos`. Esto valida que el agente puede inspeccionar en vivo el motor
de base de datos (catálogo, tipos, constraints) para verificar los invariantes que exige
la skill `turnos-core-guardian` (RN-TU-01, RN-CO-03, RN-GL-02). Sin esta verificación
en vivo, el EXCLUDE y los tipos solo se revisarían en texto.

## Comprobación de conexión

```bash
opencode mcp list   # → postgres connected
```
