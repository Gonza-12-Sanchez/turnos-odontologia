# Design — Correcciones de C-03

## Context

Ver `proposal.md` para motivación. `security.py` usa bcrypt directamente; `RegistroIn` admite 128 caracteres. `refresh()` ejecuta lecturas y escrituras Redis separadas. `rate_limit_auth()` toma `X-Forwarded-For` sin validar el emisor y usa INCR/EXPIRE separados. `decode_token()` no exige todos los claims. Los tests sustituyen Redis por un fake y monkeypatchean internamente UnitOfWork, por lo que no demuestran atomicidad real.

## Goals / Non-Goals

**Goals:** conservar rutas y respuestas existentes, endurecer su contrato, probar concurrencia y revocación con infraestructura de test aislada.

**Non-Goals:** OTP, nuevos roles, rediseño de identidad, migraciones SQL o cambios de funcionalidades posteriores a C-03.

## Decisions

### D-01 — Límite explícito de bcrypt y actualización de costo

Registro valida mínimo 8 caracteres, letra/dígito y máximo 72 bytes UTF-8. Hashing nunca recorta entradas. Login mantiene 401 genérico para una entrada que excede el límite y no puede verificar de forma segura con el esquema actual. La longitud en bytes cubre caracteres multibyte. Es una reducción explícita respecto del máximo 128 del diseño archivado; preserva el algoritmo vigente sin introducir un formato criptográfico propio. Alternativas: truncar es inseguro; cambiar algoritmo o formato para aceptar 128 requiere una migración de credenciales más amplia.

Tras verificar correctamente una contraseña, si el costo bcrypt almacenado es menor al configurado, recalcular en threadpool y guardar en una transacción antes de emitir tokens. No reducir un costo existente mayor. No exigir política de registro en login para preservar contraseñas históricas válidas. Contraseñas nunca aparecen en logs o errores personalizados.

### D-02 — Validación JWT común y estricta

Mantener HS256 con algoritmo fijo. Exigir `sub`, `roles`, `email`, `jti`, `type`, `iat`, `exp`; `fid` solo en refresh. Validar UUID en identificadores, lista de roles conocidos, email string/null, timestamps enteros (no booleanos), expiración futura, `exp > iat` e `iat` no futuro. Refresh usa los valores actuales `roles=[]`, `email=null`. Verificar el tipo esperado antes de leer Redis. La autorización sigue consultando el rol vigente en PostgreSQL. Alternativa descartada: defaults para claims ausentes permitirían saltar revocación.

### D-03 — Rotación indivisible en Redis

Usar un script Lua con claves explícitas para blacklist anterior y familia, ejecutado mediante el cliente Redis async existente. Una sola ejecución: si el refresh está revocado, eliminar familia y devolver reutilizado; si familia no coincide o falta, rechazar; si coincide, blacklist del anterior con TTL restante y reemplazo por nuevo jti con TTL del refresh nuevo. Generar nuevos tokens y validar usuario activo antes del script; emitirlos solo si retorna éxito. Una solicitud concurrente posterior detecta reuso y revoca la familia completa, incluso si la primera ya devolvió 200. Un logout concurrente que elimina la familia no puede ser revertido por una escritura posterior del refresh. Evitar WATCH/reintentos distribuidos porque Lua expresa toda la transición en una operación acotada.

### D-04 — Rate limit atómico e IP confiable

Otro script Lua realiza INCR, asigna EXPIRE cuando corresponde y devuelve contador/TTL; repara una clave existente sin expiración. Conservar 5 intentos/60 s por scope+IP+email. Usar `request.client.host`, sin interpretar `X-Forwarded-For` en la aplicación. El servidor ASGI solo debe convertir headers reenviados en cliente cuando el proxy esté explícitamente autorizado; documentar ese requisito. Se conserva la identidad normalizada del email.

### D-05 — Fallo controlado de Redis

Los helpers Redis usados por login, refresh, logout y dependencias de access traducen errores de conexión/timeout a una excepción identificable; la API responde 503 genérico y no autentica sin la verificación de revocación. Mantener timeout de socket explícito y acotar conexión. No capturar genéricamente errores de programación. Un fallo parcial de logout no devuelve éxito; la expiración natural sigue siendo el límite de seguridad.

### D-06 — Verificación del contrato

Agregar pruebas red→green por comportamiento: 72/73 bytes, multibyte, hash almacenado, rehash de costo, cada claim ausente/tipo inválido, expiración y confusión access/refresh. Verificar atributos de cookie en login/refresh y limpieza en logout; comprobar que access y refresh revocados ya no funcionan. Probar rotación concurrente con Redis real usando prefijo aislado y limpieza solo de sus claves; un fake secuencial no demuestra atomicidad. Usar sesiones separadas por solicitud en pruebas concurrentes; sustituir la factoría de sesiones vía fixture en vez de compartir una AsyncSession concurrentemente.

## Risks / Trade-offs

- [Clientes que enviaban más de 72 bytes] → 422 explícito al registrar, 401 al verificar; documentar límite, sin truncamiento silencioso.
- [Dos refresh legítimos simultáneos] → se revoca familia por política conservadora ya declarada en C-03; probarlo y documentar serialización de refresh por cliente.
- [Redis real requerido para concurrencia] → fixture aislada y fallo visible si no está disponible durante la verificación requerida.
- [Headers reenviados mal configurados] → aplicación ignora header crudo; documentar confianza del proxy en el servidor.

## Migration Plan

1. Aplicar correcciones y pruebas; no modificar el histórico de C-03 ni el esquema SQL.
2. Mantener nombres y estructura de claves Redis para familias existentes; nuevos helpers respetan TTL.
3. Verificar tokens actuales completos y hashes bcrypt existentes, rehash al login cuando corresponda.
4. Tras revisión de Apply, sincronizar delta `identity/auth` y archivar este seguimiento. Solo entonces iniciar Apply C-04.
5. Rollback de código no requiere DDL; mantener blacklists vigentes. No hacer flush global de Redis.
