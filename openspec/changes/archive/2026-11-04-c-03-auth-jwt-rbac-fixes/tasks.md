# Tasks — Correcciones de C-03

## 1. Hashing compatible y actualización de costo

- [x] 1.1 Agregar regresiones de registro para 72/73 bytes y UTF-8 multibyte; ejecutar primero contra el código actual y registrar fallos relevantes antes de corregir. RED: 1 pasó y 2 fallaron por ValueError de bcrypt (73 bytes y UTF-8 multibyte).
- [x] 1.2 Validar máximo 72 bytes sin truncar, conservar mínimo/letra/dígito y manejar verificación larga como credenciales inválidas; verificar 201/422/401 y hash persistido con las regresiones de 1.1.
- [x] 1.3 Agregar test de rehash desde costo inferior y de conservación de costo superior, implementar actualización en threadpool tras login válido; verificar persistencia y que contraseña errónea no actualice el hash. RED costo 4→5 falló; GREEN 7/7 pruebas de contraseñas.
- [x] 1.4 Documentar límite en bytes y política de rehash en documentación de auth existente o sección README; verificar que coincide con schemas y respuestas reales. Ver docs/auth.md.

## 2. JWT estrictos y revocación observable

- [x] 2.1 Agregar tests parametrizados para claims ausentes/tipos inválidos, UUID inválido, tiempos incoherentes, firma alterada y confusión access/refresh; demostrar fallos actuales de los casos relevantes. RED: 23 fallos y 14 casos ya correctos.
- [x] 2.2 Implementar validación común estricta según design D-02, usando JWTError o error de validación controlado; verificar 401 para cada token inválido y 200 para tokens actuales completos. GREEN: 39 pruebas de claims/tipos y flujos válidos.
- [x] 2.3 Completar tests de cookies HttpOnly/Secure/SameSite/Path/Max-Age en login/refresh y limpieza en logout, más reuso de access tras logout; verificar headers y 401 efectivo sin limitarse al status de logout.

## 3. Rotación atómica y Redis real

- [x] 3.1 Crear fixture de Redis real aislada por prefijo y sesiones DB independientes por solicitud para concurrencia; verificar conexión y limpieza exclusiva de sus claves, sin flush global ni monkeypatch de internals de UoW compartida. Usada en regresiones HTTP con PostgreSQL y Redis reales.
- [x] 3.2 Agregar prueba de dos refresh simultáneos y de refresh intercalado con logout que evidencie la carrera actual; verificar que no puedan quedar dos rotaciones exitosas ni restaurarse una familia eliminada. RED: dos refresh devolvieron 200 y un refresh restauró familia tras logout.
- [x] 3.3 Implementar transición Lua atómica de blacklist/familia y usarla en refresh después de validar usuario; pasar pruebas 3.2 y comprobar como máximo un 200, otro 401 y familia revocada por reuso. GREEN: 4/4 sesiones/cookies/concurrencia.
- [x] 3.4 Ampliar reutilización secuencial para intentar usar el refresh reemplazo después del anterior; verificar 401 y TTL acotado de claves reales.
- [x] 3.5 Documentar que el cliente debe serializar refreshes y que reuso revoca familia; verificar coherencia con los escenarios de integración. Ver docs/auth.md.

## 4. Límite de intentos e indisponibilidad

- [x] 4.1 Agregar test de seis intentos con X-Forwarded-For distinto y prueba concurrente de contador/TTL en Redis real; demostrar bypass o falta de atomicidad antes de corregir. RED: header evadía 429 y clave existente quedaba sin TTL.
- [x] 4.2 Usar IP resuelta por servidor ASGI y contador Lua con expiración atómica; verificar 5/60 s, 429 con Retry-After, vencimiento y reparación de clave sin TTL en pruebas acotadas. GREEN: 3/3 rate limit real.
- [x] 4.3 Agregar tests de error/timeout Redis en login, refresh, logout y rutas protegidas; implementar manejo acotado y comprobar 503 genérico sin omitir verificaciones ni exponer errores internos. RED: 8 fallos en sesión/revocación; GREEN: 12/12 casos de connection/timeout en la suite completa.
- [x] 4.4 Documentar confianza del proxy y el uso de request.client.host; verificar que ningún helper de aplicación interprete headers crudos para reemplazar la IP. Ver docs/auth.md y regresión X-Forwarded-For.

## 5. Verificación integrada del seguimiento

- [x] 5.1 Ejecutar suite backend completa (`python -m pytest` desde backend) con PostgreSQL turnos_test y Redis de test disponibles, más `python -m ruff check .`; registrar resultados reales y resolver regresiones de C-03. 102 passed, lint OK, formato 48 archivos OK; evidencia en verification.md.
- [x] 5.2 Ejecutar `openspec validate c-03-auth-jwt-rbac-fixes --strict`, revisar `git status`/`git diff` y presentar archivos y resultados al usuario; comprobar que no se agregaron secretos ni datos reales y no ejecutar git add/commit/push. Validación y diff-check OK; resultados presentados y documentados en verification.md. Pendiente revisión para Archive.

## Workflow follow-up

- Solicitar revisión de Apply antes de Archive, según las reglas del usuario.
- Guardar progreso de cada etapa en Engram con topic_key `opsx/c-03-auth-jwt-rbac-fixes/<fase>` si mem_save está disponible; informar falta de herramienta, sin simular guardado.
- Sincronizar delta identity/auth y archivar el seguimiento aprobado; conservar archivo histórico C-03 original.
- Verificar archivo y spec principal antes de comenzar Apply de C-04.
- Cualquier git add, commit o push requiere confirmación explícita del usuario.
