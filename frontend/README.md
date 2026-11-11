# PWA Paciente (C10) y gestión del consultorio (C11 en progreso)

React 18 / TypeScript estricto / Vite 6. Área pública/paciente y avance incremental
del consultorio. C11 no está terminado; sin facturación electrónica.

## Desarrollo Y Verificacion

Desde frontend/, Node 20+ y npm 11.17.0:

```powershell
npm.cmd ci --ignore-scripts
npm.cmd test
npm.cmd run lint
npm.cmd run build
npx.cmd --no-install playwright install chromium
npm.cmd run test:e2e
npm.cmd run dev -- --host localhost
```

`.npmrc` bloquea scripts de dependencias. Iconos PNG generados y reproducibles
con `npm.cmd run icons`, sin descargar assets ni agregar dependencias.
E2E levanta/cierra preview automaticamente en localhost:4173 y usa Chromium
headless. Los tests interceptan HTTP con datos ficticios: NO prueban cookies
reales, Mercado Pago ni constraints del backend. Capturas publicas ficticias en
`test-results/horarios-{360,1280}.png`; reportes ignorados por git.

## Configuracion

- `VITE_API_URL`: origen API, default `http://localhost:8000`, sin `/api` global.
- `VITE_ENABLE_TEST_PAYMENTS`: `false` por defecto. Solo habilitar expresamente
  en entorno de prueba luego de verificar C09. No habilita produccion.
- Mock: solo `npm run dev`, retorno local validado y rotulo visible.
- Sandbox: solo URL HTTPS allowlist MP Argentina, con modo servidor sandbox.
- Production: rechazado siempre en esta entrega, aun con flag true.

No hay fixtures de catalogo en runtime ni UUIDs hardcodeados. Mientras falte
GET /catalogo-publico en backend, Horarios muestra el error de carga y no inventa
tratamientos/precios. Campo sena ausente o incoherente falla cerrado.

La API debe conservar su CORS/same-site y cookies HttpOnly existentes. No se
desactiva seguridad para que funcionen las pruebas. Si UI/API comparten origen,
el proxy debe distinguir navegacion HTML SPA de fetch JSON en `/mis-reservas`
y `/pagos/retorno`; no enviar index.html como respuesta API. En desarrollo,
el origen API separado evita esta ambiguedad. El SW solo aplica fallback a
request.mode=navigate para rutas SPA permitidas.

## Contratos De Integracion

| Endpoint | Contrato consumido |
| --- | --- |
| GET /catalogo-publico | `{sillones:[{id,nombre}],tratamientos:[{id,nombre,duracion_min,sena_politica,sena_centavos}]}`; anonimo, activos, orden nombre/id, sin PII |
| GET /horarios-libres | query `fecha=YYYY-MM-DD&tratamiento=UUID&sillon=UUID` (sillon opcional); lista `{sillon_id,inicio,fin}` con offsets |
| POST /auth/registro | nombre/email/telefono/password -> UserOut 201, NO token; login explicito posterior |
| POST /auth/login, /auth/refresh | TokenOut `access_token` y cookie refresh HttpOnly Path=/auth; credentials include |
| GET /auth/me | `{id,rol,nombre?}` usando Bearer; rol paciente requerido para area privada |
| POST /auth/logout | Bearer + cookie -> 204; fallo limpia vista pero advierte cierre no verificado |
| POST /turnos | `{sillon_id,tratamiento_id,inicio,sena?}`, Bearer e Idempotency-Key estable en memoria por payload; exito SOLO 201 TurnoOut |
| POST /turnos 409 | `{detail,alternativas:[{sillon_id,inicio,fin}]}`; requiere nueva eleccion explicita |
| POST /turnos 402 | `{detail,checkout:{provider:'mercadopago',status:'pendiente',intento_id,checkout_url,expires_at,monto_centavos,moneda:'ARS',modo}}` |
| POST /turnos 503 ambiguo | `{code:'CHECKOUT_NO_VERIFICADO',intento_id}` -> consultar intento, no nueva preferencia |
| GET /pagos/sena/{id} | propio: `{id,estado,monto_centavos,moneda,expires_at,turno_id,requiere_contacto}`; ajeno/inexistente 404 |
| GET /mis-reservas | lista propia con `tratamiento_nombre,sillon_nombre,inicio,fin,estado,tolerancia_min,acciones:{confirmar,cancelar,reprogramar}` |
| PATCH /turnos/{id}/confirmar o cancelar | sin cuerpo de negocio; reconsulta lista; 422 explica minimo de 2h, no inventa permisos por reloj cliente |

Catalogo backend C10 sigue delegado; C09 se integra contra su contrato
planificado, no contra una implementacion certificada. No se utiliza el antiguo
placeholder 402 como checkout. No se llama POST /pagos/sena desde retorno:
solo GET estado cada 3s, hasta 60s, luego consulta manual. Query approved no
prueba pago. Aprobado necesita turno_id; requiere_revision no ofrece otro pago.
No se retiene cupo durante checkout; sin cupo, devolucion manual del consultorio.

## Privacidad Y Limites

Access token solo en memoria; refresh solo cookie backend. Sin localStorage,
sessionStorage, IndexedDB ni cache de API. Web Locks serializa refresh, login y
logout entre pestanas con el mismo nombre `turnos-auth-cookie`. La sesion requiere
un navegador con Web Locks en contexto seguro (HTTPS o localhost); sin soporte
falla cerrado antes de enviar operaciones de cookie. La cola local solo sirve
en ejecucion no-browser (tests Node), no se vende como coordinacion multi-tab.
Los resultados de GET/POST/PATCH de generaciones anteriores no restauran sesion
ni se entregan a la cuenta nueva. Logout bloquea refresh durante el cierre e
invalida al inicio y al finalizar. Ningun GET recuperable corre dentro del lock:
la identificacion usa el cliente HTTP directo, sin refresh recursivo.
BroadcastChannel solo invalida identidades, nunca comparte tokens ni reservas.
Cambio de cuenta remonta vistas privadas, incluido checkout en pagina publica.
Logout fallido advierte que el cierre servidor no fue verificado.

Shell y assets publicos son lo unico precacheado. No runtimeCaching de APIs,
background sync ni cola POST/PATCH. Offline no ofrece horarios actuales ni
escrituras; reconexion invalida franjas y reconsulta. Updates requieren permiso
y se pueden posponer sin perder formulario. No analytics ni logs de pacientes.

Los 5xx, timeout/transporte y respuestas de exito malformadas dejan reserva por
reconciliar. Se bloquean nuevos POST, filtros y seleccion aun navegando por la
SPA. Reconciliar solo consulta Mis reservas (o el intento conocido): encontrar
el mismo tratamiento/sillon/instante libera el bloqueo sin reenviar POST. Una
lista vacia o un error no demuestra que el intento no se aplique despues y NO
libera el bloqueo; contactar al consultorio. Idempotency-Key no garantiza soporte
del backend para reserva directa. El bloqueo es en memoria y se purga en logout;
no garantiza seguridad tras recargar/cambiar de sesion, ni sustituye idempotencia
y reconciliacion durables del servidor. No usar recarga como forma de reintento.

## Contrato Temporal Bloqueado

La seleccion es fecha de Argentina, pero disponibilidad backend usa limites de
dia UTC (hallazgo de review). No se cambio backend ni se simulo una solucion:
todas las franjas muestran fecha AR completa junto a la hora. Las de otra fecha
permanecen visibles pero deshabilitadas, incluso con seleccion precargada en URL.
No se filtran silenciosamente ni se afirma cubrir el dia AR completo. El acuerdo
semantico, endpoint y pruebas integradas siguen pendientes.

## Dependencias Revisadas

Vite 6.4.6 dentro del rango compatible 6.x, Vitest 3.2.7 y override acotado
`vitest -> tinypool 2.1.2`. El breaking de Tinypool2 elimina Node18; este proyecto
ya exigia Node20+. APIs de pools revisadas y probadas en worker_threads y
child_process. fast-uri3.1.9 y serialize-javascript7.1.4 actualizados dentro de
sus rangos. Scripts de dependencias siguen bloqueados; no audit fix --force.

Auditoria final: 10 hallazgos (8 moderados, 2 bajos), cero high/critical. Los
restantes requieren cambios mayores no aplicados de Router/Vitest/Workbox. No
SSR ni hidratacion de errores externos; returnTo estricto sin backslashes;
Vitest API deshabilitada y solo modo run, sin UI/servidor de mocks; Workbox recibe
solo configuracion y patrones estaticos controlados, no entradas de usuarios.
No es aprobacion de release. Ver C10 verification.md para triage completo y
evidencia RED/GREEN. C09 sigue bloqueado por falta de servicios reales; ningun
test con HTTP simulado acredita auth/cookies/checkout integrados.

## C11 — Rutas y autorización frontend

| Ruta | Roles UI | Estado inicial del slice |
|---|---|---|
| /agenda | secretaria, odontologo | Bloqueada la consulta del día AR hasta verificar contrato temporal |
| /config | secretaria | Configuración incremental; no implica cambiar contratos backend |
| /cobros | secretaria para registro | No habilitado hasta verificar C09; sin escrituras monetarias |

Un único SessionProvider mantiene locks/generaciones de C10. No hay peticiones
administrativas antes de verificar rol; loading y 503 de sesión no muestran área
privada. Anónimo (incluido refresh401) va a login; paciente/rol desconocido recibe
denegación; odontólogo no consulta configuración. Ocultar navegación no reemplaza
RBAC backend. La 404 continúa para rutas desconocidas, no para /agenda ya definida.

Pruebas DOM/HTTP ficticio: `npm.cmd test -- src/Staff.test.tsx`. No acreditan
cookies, CORS ni permisos del backend real. Gates y evidencia en
`../openspec/changes/c-11-pwa-agenda-gestion/verification.md`.

Login valida returnTo con allowlist exacta y con el rol autenticado: secretaria
puede volver a /agenda, /config y /cobros; odontólogo a /agenda; paciente mantiene
sus destinos C10. Destino externo, //, backslash, controles o ruta incompatible
vuelven al inicio privado del rol (/agenda staff, /mis-reservas paciente). No se
envía ninguna escritura de negocio automáticamente al completar login.

Configuración consulta exclusivamente GET `/api/config/{tratamientos|sillones|bloqueos}`
con `page`, `page_size=20` y `activo=true|false` (false significa solo inactivos).
Valida DTOs unknown, tipos/cotas, UUIDs, política seña y coincidencia de página/filtro;
un JSON incoherente es error, no una lista vacía. Cambiar recurso/página/filtro
remonta la lectura, aborta y descarta respuestas tardías. Offline no conserva
recursos visibles ni hace escrituras; no se cargan fixtures en runtime.

Identidad y refresh de C10 siguen sin cambios: los tests de C11 verifican dos
cuentas y respuestas demoradas al cerrar/volver a entrar, y refresh único compartido
por lecturas vencidas. Esto no acredita cookies ni concurrencia multi-tab real.

### C11 — Tratamientos (slice 3.2)

Alta: POST `/api/config/tratamientos`, espera 201 y usa el UUID recibido. Edición:
PATCH `/api/config/tratamientos/{id}`, espera 200 y envía únicamente nombre,
duración y/o precio modificados. Ambos validan el DTO y los valores confirmados
antes de anunciar éxito. Crear usa la política deshabilitada por defecto del
backend; la UI no envía ni permite editar `sena_politica`/`sena_centavos`.

Precio: texto ARS con coma o punto decimal, sin miles, máximo dos decimales;
conversión con BigInt (entero×100 + fracción), sin parseFloat ni redondeos. Vacío
envía null explícito; cero envía 0. Cota: 2147483647 centavos (21474836,47 ARS).
Duración: entero 1–2147483647; nombre recortado, 1–120 caracteres. El backend
continúa siendo la autoridad de las reglas. Los 422 se asocian a campos conocidos
mediante aria-invalid/aria-describedby; nunca se muestra el detalle interno crudo.

Escritura con límite de 15s y sin reintento automático. Un bloqueo en memoria del
Layout de la cuenta comienza antes del envío: mientras está pendiente, impide
otra escritura; ante transporte/5xx/DTO inesperado conserva la incertidumbre.
Navegar, reconsultar o reconectar no lo libera. Una respuesta tardía tras desmontar
el formulario tampoco habilita repetirlo. Solo un 422 o un éxito validado con el
formulario aún presente termina normalmente el ciclo. No existe conciliación
automática: consultar una lista no prueba que el comando no se aplicó.

Límite importante: el bloqueo no sobrevive recarga/cierre de sesión ni coordina
pestañas. No es idempotencia backend ni acredita seguridad de reintentos tras
reiniciar; el resultado incierto requiere conciliación operativa antes de repetir.
No se almacenan tokens, datos de catálogo ni comandos en storage/caché/colas.

Estilos staff reflejan la base revisión1 sin importarla desde fuera del contexto
Docker `frontend/`. Capturas HTTP ficticio y diferencias visuales pendientes:
`../openspec/changes/c-11-pwa-agenda-gestion/mockups/verify/`.

### C11 — Sillones existentes (slice 3.3)

Desde Sillones → Editar se puede cambiar el nombre (1–80 caracteres). El PATCH
solo envía `nombre` si cambió; no permite ingresar ni modificar consultorio_id.
Desactivar/Reactivar abre una confirmación separada: solo al confirmarla envía
`{activo:false}`/`{activo:true}`, sin incorporar cambios de nombre no guardados.
Cancelar no envía solicitudes. No hay DELETE ni cambios/cancelaciones de turnos:
desactivar es baja lógica, no borra históricos. El servidor sigue siendo la
autoridad; las pruebas HTTP simuladas no acreditan persistencia de históricos.

Antes de mostrar éxito valida DTO, id, sede, nombre y actividad confirmados.
Después de baja/reactivación reconsulta la página con el filtro activo/inactivo
vigente; el recurso deja de aparecer en el filtro anterior. No se reconstruye
una lista ficticia ni se altera la agenda desde el cliente.

422 asocia errores conocidos a Nombre y conserva el valor. 403/404 informan
permiso/recurso no disponible, sin afirmar que fue borrado ni refrescar permisos;
se debe volver a consultar antes de otro intento. Fallos de transporte/5xx/DTO
inesperado mantienen el guard de incertidumbre del Layout; mismo límite de15s,
sin retry/replay automático. El alta sigue pendiente de G-contexto: no se obtiene
la sede desde otro sillón ni se pide un UUID manual.
