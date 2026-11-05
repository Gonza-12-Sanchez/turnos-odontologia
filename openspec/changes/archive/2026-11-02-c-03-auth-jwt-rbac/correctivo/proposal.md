# Proposal — Correcciones de C-03

## Why

C-03 está archivado, pero la implementación deja brechas entre el contrato de identidad y su comportamiento: hashing de contraseñas largas, rotación concurrente, claims incompletos y errores Redis. Corregirlas antes de implementar C-04 evita construir configuración administrativa sobre sesiones insuficientemente verificadas.

## What Changes

- Registrar un seguimiento correctivo de C-03, conservando el archivo histórico y la secuencia C-03 → C-04 del roadmap.
- **BREAKING**: validar el límite real de bcrypt de 72 bytes UTF-8 en registro; rechazar con 422, nunca truncar. Mantener lectura de hashes bcrypt existentes y agregar rehash cuando su costo sea inferior al configurado.
- Exigir claims JWT completos, tipos correctos y expiración para access/refresh.
- Rotar refresh de forma atómica en Redis, incluyendo detección de reutilización y revocación de familia bajo concurrencia.
- Aplicar rate limit 5/60 s con contador y expiración atómicos, sin confiar en headers de IP enviados por el cliente.
- Responder 503 ante indisponibilidad Redis en todos los caminos de autenticación dependientes de ese servicio.
- Ampliar regresiones para cookies, logout, validación de tokens, hashing y concurrencia real en Redis.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `identity/auth`: precisar validación estricta de tokens, límite bcrypt, rotación concurrente, origen confiable de IP y disponibilidad Redis.

## Impact

Archivos previstos: `backend/app/{api/deps.py,services/auth_service.py,shared/security.py,shared/rate_limit.py,schemas/auth.py,db/redis.py}`, tests de auth y documentación operativa de proxy. Reutiliza bcrypt, python-jose y Redis; no necesita nuevas tablas ni migraciones. Apply y archivo correctivo deben finalizar antes de Apply de C-04. No introduce C-05 ni posteriores.
