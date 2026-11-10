# Design

## Context

Ver proposal.md. `App.tsx` solo renderiza Home en max-w-md; no router ni sesion. React 18.3.1, Vite 6.3.6, Tailwind 4 y vite-plugin-pwa ya declarados; Vitest solo prueba cliente HTTP, sin DOM. Cliente tiene GET/POST, AbortSignal y Bearer por llamada, pero descarta cuerpos de error y no configura credentials. PWA usa autoUpdate y manifest sin iconos. `main.py` sirve auth en `/auth`, config en `/api/config`, turnos/horarios/mis-reservas en raiz: no asumir prefijo /api para todo.

Catalogo solo existe en `/api/config` con rol secretaria. C-07 devuelve listas (no pages) con `acciones` y alias `acciones_permitidas`, `tolerancia_min` y nombres. Registro devuelve UserOut sin token, login TokenOut y cookie refresh HttpOnly Path=/auth; hay refresh rotativo con deteccion de reuso. No cambiar estas reglas.

## Goals / Non-Goals

**Goals:** circuito paciente utilizable en 360px y desktop, feedback de negocio correcto, sesion segura y PWA instalable sin PII en almacenamiento offline. Un pequeno endpoint de lectura resuelve la brecha de filtros sin expandir administracion.

**Non-Goals:** C-11/C-12, agenda profesional, config/cobros administrativos, editar reglas o estados backend, UI de reprogramacion, OTP, upgrade React/Vite, offline booking y autofacturacion.

## Decisions

### 1. Dependencias y limite de entrega

Planning solo, sin codigo ni tests en este encargo. C-05/C-07 archivados habilitan propuesta y futuro flujo sin sena. C-09 es dependencia de contrato para flujo MP aunque la lista textual C-10 de CHANGES.md omita esa arista que el arbol incluye. No simular que el placeholder actual es checkout funcional. Mock de contrato permite TDD de UI, no evidencia de integracion real. Aceptacion integral 402/retorno espera backend C-09 aprobado y verificado; no activar MP al usuario con ese gate pendiente. No escribir las tablas/campos MP desde C-10.

### 2. Contrato publico minimo

Agregar `GET /catalogo-publico`, anonimo, devuelve `{sillones:[{id,nombre}],tratamientos:[{id,nombre,duracion_min,sena_politica,sena_centavos}]}`. Solo activos, orden estable nombre/id, sin pacientes, bloqueos, consultorio_id, auditoria ni precio de referencia (no es tarifa final). Sin parametro para leer inactivos. Respuesta vacia 200 permite mensaje claro; fallo 503 no reemplazar por fixtures. Backend usa DTO allowlist, nunca serializa modelo entero.

Los campos de sena pertenecen a C-09. Hasta su disponibilidad, C-10 no inventa ni persiste politica: la entrega integrada del catalogo con esos campos se realiza despues de C-09. No pedir UUIDs manualmente ni hardcodear seeds. Alternativa descartada: habilitar anonimo sobre `/api/config` o extraer IDs de horarios sin disponer de tratamiento inicial.

### 3. Rutas y estructura pequena

Proponer React Router compatible con React 18 para rutas, revisando version/lockfile y scripts antes de instalar en apply. No introducir libreria de estado global/query por defecto. `features/auth`, `features/reserva`, `features/mis-reservas` y `shared/api` bastan; estado compartido de sesion en un proveedor, componentes PascalCase y TS estricto sin any. Cargas independientes paralelas, AbortController para cambios rapidos de filtros y evitar respuestas viejas. No useMemo/useCallback por rutina; sin APIs exclusivas React 19 como useEffectEvent.

| Ruta | Flujo |
|---|---|
| / | identidad del consultorio sin datos ficticios publicados como reales, accion Ver horarios |
| /horarios | catalogo, fecha local AR, tratamiento obligatorio y sillon opcional; GET /horarios-libres?tratamiento=<uuid>&fecha=YYYY-MM-DD&sillon=<uuid> |
| /login | email/password; mantiene seleccion no sensible y destino interno validado |
| /registro | nombre/email/telefono AR/password; omitir obra_social opcional para minimizar PII; 201 no implica login |
| /mis-reservas | protegido paciente; GET /mis-reservas lista propia, confirmar/cancelar |
| /pagos/retorno | requiere sesion paciente antes de consultar intento; nunca confia en query MP ni muestra exito por redirect |

Una ruta desconocida muestra 404 navegable. No crear `/agenda`, `/cobros` o `/config`. Otros roles autenticados reciben explicacion de area paciente no disponible, sin prometer UI C-11.

Seleccion de fecha/tratamiento/sillon/inicio puede viajar en URL interna validada (no PII). Login no reenvia automaticamente POST pendiente: vuelve al resumen y revalida disponibilidad; usuario confirma. `returnTo` solo rutas internas allowlist, no URL externa. Mostrar horarios con zona explicita America/Argentina/Buenos_Aires usando los instantes aware API, sin cortar ISO UTC para obtener fecha local. No recalcular duracion/fin como fuente de verdad.

### 4. Sesion y cliente HTTP

Base de API por env publica de origen, sin secretos VITE_. Extender cliente con PATCH y errores que conserven body como unknown y sean estrechados por contrato (409 alternativas vs 409 registro vs validacion Pydantic 422). Mantener status y UnauthorizedError; respuestas no JSON tienen mensaje seguro, no HTML servidor. No buscar errores criticos por strings. Incluir credentials en auth para recibir/enviar refresh, Bearer en rutas protegidas y AbortSignal. No ampliar CORS ni SameSite: despliegue same-site y origen permitido existente.

Access token solo memoria; refresh solo cookie HttpOnly existente. En arranque intentar refresh una vez y `/auth/me`, estado inicial loading para evitar flash privado; 401 limpia sesion, 503 muestra indisponibilidad, no finge logout definitivo. Registro 201 ofrece login con email precargado, no reusa/guarda password. Logout llama backend, limpia memoria/listas privadas y no deja datos al cambiar cuenta. En fallo de logout limpiar vista local pero informar que no se verifico cierre servidor.

Coordinar refresh single-flight y evitar carreras entre pestanas mediante Web Locks cuando disponible; no persistir tokens. Si no hay coordinacion multi-tab soportada, fallar seguro solicitando login ante rotacion/reuso, nunca bucle de refresh. Retry de GET como maximo una vez tras refresh. No reintentar POST/PATCH de negocio automaticamente: si falla red su resultado puede ser ambiguo. Para sena reutilizar misma Idempotency-Key por accion y payload en memoria; volver del checkout consulta intento, no vuelve a cobrar. Idempotencia backend de reserva directa no existe hoy: ante timeout consultar Mis reservas antes de ofrecer repetir.

### 5. Reserva y pagos: contrato compartido exacto

POST /turnos con `{sillon_id,tratamiento_id,inicio,sena?}`. Omitir los otros aliases antiguos; la politica servidor es autoridad. Mostrar monto fijo y consentimiento antes de enviar rama de sena; Idempotency-Key generado por accion, estable durante reintentos del mismo payload. C-09 responde:

- 201 TurnoOut: mostrar reserva registrada y actualizar Mis reservas.
- 409 `{detail,alternativas:[{sillon_id,inicio,fin}]}`: ofrecer elegir una alternativa, nunca reservarla automaticamente; lista vacia ofrece cambiar filtros.
- 402 `{detail,checkout:{provider:"mercadopago",status:"pendiente",intento_id,checkout_url,expires_at,monto_centavos,moneda:"ARS",modo}}`: mostrar resumen y redirigir solo checkout HTTPS de host MP permitido en sandbox/production. Mock claramente rotulado solo en desarrollo con retorno local, sin pago real.
- 422 detalle string o lista de validacion: mensaje accionable, sin ocultar regla servidor. 401 requiere login; 403 no intentar refrescar permisos; 503 no muestra exito.

Un 503 con `{code:"CHECKOUT_NO_VERIFICADO",intento_id}` permite consultar estado de ese intento, sin redirect ni nueva preferencia; no interpretar un checkout incompleto como 402 utilizable.

Antes del checkout indicar "El horario se verifica al aprobar el pago" porque C-09 propone no retener cupo. `/pagos/retorno?intento_id=<uuid>` usa GET `/pagos/sena/{id}` autenticado; status `aprobado` con turno_id es reserva efectiva. `pendiente/creando_checkout` -> espera; `rechazado/expirado` -> sin reserva y volver a horarios; `requiere_revision` -> pago a revisar, contactar consultorio, no ofrecer pagar otra vez. Polling acotado cada 3s hasta 60s, detener al desmontar/offline/terminal; luego boton Consultar estado. UUID opaco en URL no reemplaza ownership; 404 ajeno no revela PII. Query `status=approved` o `payment_id` no se usa como prueba.

### 6. Mis reservas y ventana

Usar `acciones` canonico del payload observado, no duplicar la politica en un reloj local. Mostrar estado reservado/confirmado/asistido/cancelado/ausente, nombres, fecha/sillon y tolerancia_min. Confirmar/cancelar llaman PATCH `/turnos/{id}/confirmar|cancelar` sin cuerpo de negocio adicional. Cancelacion pide confirmacion. No ofrecer reprogramar aunque C-07 lo indique: fuera de alcance UI C-10. Si una accion ya no es valida y servidor devuelve 422, explicar ventana minima de 2h segun contrato y reconsultar; exactamente 2h se rige por backend. Mostrar explicacion junto a cancelar no disponible. Confirmar no tiene regla 2h adicional inventada.

### 7. Visual y accesibilidad

Preservar la sencillez existente slate/celeste y Tailwind; no convertirlo en dashboard comercial. Paleta propuesta: papel #FFFFFF, texto #0F172A, texto secundario #475569, accion #0369A1, borde #CBD5E1, error #B91C1C. Tipografia system-ui local, sin fuentes remotas ni tracking. Identidad funcional: selector de fecha y lista horaria por sillon como elemento central, no hero generico ni grilla de tarjetas repetidas. Titulos 28/22px, cuerpo 16px; alineacion izquierda, formularios de ancho contenido y layout hasta 960px en desktop.

Wireframe movil: encabezado compacto -> tratamiento/fecha/sillon -> lista de horas -> resumen elegido -> accion Reservar. Desktop: filtros a izquierda, franjas y resumen a derecha; mismo orden DOM accesible. Labels persistentes, botones >=44px, foco visible, mensajes aria-live y no solo color, estados loading/vacio/error/offline por separado, reduced-motion. Revision de diseno: se descarta hero con marketing/estadisticas porque la tarea primaria es elegir una hora.

### 8. PWA y privacidad offline

Reutilizar VitePWA generateSW; manifest con icons 192/512, maskable y nombre coherente. Cambiar autoUpdate por prompt para no recargar formulario o checkout sin permiso. Precache SOLO shell/assets publicos, nada de API ni contenido personalizado. Sin runtimeCaching de APIs, sin background sync de POST/PATCH. Excluir `/auth`, `/api`, `/catalogo-publico`, `/horarios-libres`, `/turnos`, `/mis-reservas` API, `/pagos` API y `/webhooks` de interception de solicitudes API; distinguir origen y modo request para permitir navegacion HTML a rutas SPA `/mis-reservas` y `/pagos/retorno` sin interceptar fetch JSON homonimo. En origen API distinto, no cachear ninguna solicitud a ese origen.

Offline muestra shell y aviso sin turnos/datos privados persistidos; deshabilitar reserva/acciones/pago y no prometer libres actuales. Tras conexion, consultar servidor nuevamente. Nunca guardar tokens, passwords, listas de reservas ni cuerpos de pago en localStorage/IndexedDB/CacheStorage. No service worker que atienda un GET JSON con index.html. Logs y capturas solo datos ficticios; purgar estado en logout/cambio de cuenta. No agregar analytics.

### 9. Strict TDD futuro

Seams a confirmar: cliente HTTP publico, pantallas via DOM accesible/navegacion, catalogo publico HTTP, browser real contra backend para auth/cookies/reserva y browser con service worker para offline. Proponer Testing Library + jsdom y Playwright solo al aplicar, previa revision de dependencias/lockfiles; sin instalar ahora. Mockear HTTP externo para casos deterministas, no funciones internas del componente. Test de integracion final con APIs reales de C-05/C-07/C-09 y datos ficticios, no solo rutas interceptadas.

Baseline backend/frontend antes de cambios, registrar fallos preexistentes. Por comportamiento hacer RED ejecutado por fallo esperado, implementacion minima GREEN, triangulacion >=2 casos independientes, review/refactor con regresion verde. Guardar evidencia de comandos, exit/output RED/GREEN, casos, fecha, refactor y suite; agregar error de negocio y borde, no solo happy path. Ningun test se escribe en esta propuesta.

## Risks / Trade-offs

- Dependencia MP pendiente -> mocks etiquetados no habilitan aceptacion integrada; respetar gate C-09.
- Refresh rotativo y dos pestanas -> single-flight/coordinacion, reautenticar fail-safe si no se puede asegurar exclusividad; sin cambiar backend auth.
- Path API y pagina iguales -> separar origen/request.mode y probar navegaciones directas vs fetch para no devolver HTML en lugar de JSON.
- Disponibilidad obsoleta/accion fuera de ventana -> backend siempre decide 409/422; reconsulta y mensaje util.
- Respuesta de escritura perdida -> no reenvio ciego; consulta estado/Mis reservas y accion explicita.
- Cookie Secure/SameSite local vs piloto -> probar HTTPS same-site y CORS actual; no desactivar controles para hacer verde prueba.

## Migration Plan

1. Revision humana, confirmar seams y nueva solicitud apply. Baseline; aprobar dependencias de router/testing con lockfile y politica de scripts antes de instalar.
2. Implementar endpoint publico sin abrir configuracion y UI sin sena con TDD; adaptar campos de C-09 cuando este disponible. No migraciones de DB propias de C-10.
3. Integrar checkout/retorno contra C-09 verificado; verificar 360px/desktop, cookies reales, 409, 422, offline y instalabilidad en preview HTTPS/localhost. Build frontend normal si se autoriza apply; no imagenes finales.
4. Deploy conserva rutas API reales y SPA fallback para navegaciones publicas. Rollback UI mantiene API y pagos pendientes; limpiar caches antiguas sin tocar registros monetarios. No publicar MP habilitado mientras falte gate sandbox/produccion de C-09.

## Open Questions

Nombre/logo y telefono de contacto publico definitivos pueden configurarse al piloto sin cambiar contratos; no publicar datos inventados como reales. El texto final de ayuda conserva siempre la distincion entre pago y reserva.

## References

### Revision De Seguridad C10 (Apply Autorizado)

2026-11-09 local: correcciones frontend/session aprobadas expresamente. Acceso
por generaciones; logout invalida antes/despues y bloquea recuperacion; todas las
operaciones de cookie (login/refresh/logout) comparten Web Lock. El fallback
browser sin coordinacion se reemplaza por fallo cerrado, no por una cola local
que pretenda cubrir varias pestanas. /auth/me usa API directa, sin recuperacion
recursiva dentro del lock. No cambia el contrato auth backend.

Reserva directa no tiene garantia de idempotencia backend por enviar un header.
Cualquier resultado no verificable bloquea la siguiente escritura/seleccion en
la SPA hasta reconciliacion explicita por lectura propia. Ausencia/error de
lectura no demuestra no-aplicacion y conserva bloqueo. Memoria se purga en
logout; recarga no es recuperacion segura ni sustituye solucion durable backend.

Contrato de fecha BLOQUEADO: UI selecciona dia AR, backend consulta dia UTC.
Se muestra fecha completa por franja y se deshabilitan fuera de dia sin ocultar
datos. No es correccion integral ni prueba integrada; tarea4.2 reabierta.

Tooling sigue React18/Vite6/Vitest3. Override especifico Tinypool2.1.2 revisado:
Node18 removido es compatible con minimo Node20 del proyecto. Sin migraciones
mayores de Router/Vitest/Workbox. Ver verification.md para RED/GREEN y triage.

Context7 consultado: `/vite-pwa/vite-plugin-pwa`, manifest/icons, `navigateFallbackDenylist` y registerType prompt. Documentacion https://vite-pwa-org.netlify.app/guide/pwa-minimal-requirements.html y https://vite-pwa-org.netlify.app/workbox/generate-sw.html. No aplicar recetas de Background Sync a reservas ni instrucciones Vite 8 de la skill a este proyecto Vite 6.
