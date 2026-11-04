# Autenticación — C-03

Rutas: `POST /auth/registro`, `/auth/login`, `/auth/refresh`, `/auth/logout` y `GET /auth/me`.

## Contraseñas

Registro requiere mínimo 8 caracteres, una letra y un dígito. Bcrypt admite como máximo **72 bytes UTF-8**, no 72 caracteres: una contraseña multibyte puede alcanzar el límite antes. Un registro que supera el límite recibe 422, sin truncar; login devuelve 401 genérico si no se puede verificar la contraseña. Los hashes existentes siguen siendo bcrypt. Después de un login correcto se aumenta transparentemente un costo inferior a `BCRYPT_ROUNDS`, nunca se reduce un costo mayor. Hashing y verificación se ejecutan fuera del event loop.

## Sesiones y proxy

Los JWT requieren claims completos y tipados, identificadores UUID, tipo access/refresh correcto y tiempos coherentes. La autorización consulta el rol y estado actual del usuario, no confía solo en el claim del cliente.

Refresh rota en una operación atómica de Redis. Reutilizar un token anterior revoca su familia, incluido el reemplazo ya emitido. **El cliente debe serializar los refreshes**: dos solicitudes simultáneas con el mismo token provocan revocación conservadora. Logout elimina la familia y una rotación concurrente no puede restaurarla. El access se devuelve en JSON; refresh solo en cookie HttpOnly, Secure configurable, SameSite=lax y Path=/auth.

Login y registro admiten 5 intentos por 60 segundos por IP+email normalizado. El contador y su vencimiento se actualizan atómicamente. La aplicación usa `request.client.host` e ignora `X-Forwarded-For` crudo. Si existe reverse proxy, configurar en Uvicorn únicamente las IPs de proxies confiables (`--forwarded-allow-ips`); nunca confiar en `*` ante clientes directos. Un error/timeout Redis responde 503 genérico, sin omitir controles de sesión.

## Entorno de pruebas

Desde `backend/`, instalar `python -m pip install -e ".[dev]"` en un entorno virtual Python 3.12+.
La suite requiere PostgreSQL con la migración aplicada sobre una base **turnos_test** y Redis real.
`TEST_DATABASE_URL` permite seleccionar otra instancia local (por ejemplo puerto 55432), manteniendo el nombre de base turnos_test. `TEST_REDIS_URL` permite seleccionar Redis de pruebas; default `redis://127.0.0.1:6379/15`. Cada test usa un prefijo UUID y solo elimina sus propias claves, sin FLUSHDB.

Ejemplo PowerShell con una instancia de pruebas ya preparada:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://turnos@127.0.0.1:55432/turnos_test'
python -m pytest tests/test_auth.py -q
```

No usar una base con pacientes reales para tests. Las credenciales y direcciones de desarrollo son configurables y no se imprimen desde el entorno real.

El job backend de CI levanta PostgreSQL 16 y Redis 7 efímeros, espera sus health checks y ejecuta `alembic upgrade head` antes de la suite. Las credenciales ficticias de esos contenedores no dan acceso a servicios externos.
