# Tasks

APPLY FRONTEND autorizado 2026-11-09. Ownership exclusivo frontend/ y artifacts C10; backend C09 concurrente y catalogo backend C10 delegado. Mocks no acreditan integracion. Ver verification.md. No C11/C12.

Strict TDD obligatorio por CADA comportamiento: confirmar seam, test nuevo y RED ejecutado por causa esperada, minimo GREEN, triangulacion >=2 casos independientes (feliz + error/borde), segundo RED/GREEN si agrega comportamiento, review/refactor posterior y regresion verde. Trabajar slices verticales, no tests masivos ni codigo antes de RED. verification.md registra caso/seam/comando/fecha/salida y exit RED/GREEN, refactor y regresion; errores de entorno/baseline no cuentan como RED. Tests y docs de cada grupo se entregan con ese grupo.

## 1. Gates y preparacion

- [x] 1.1 Obtener revision humana y confirmar seams cliente HTTP, DOM/navegacion, catalogo HTTP, browser con backend y service worker; verificar matriz escenario->seam aprobada y solicitud separada de implementacion antes de codigo/tests.
- [x] 1.2 Reconfirmar C-05/C-07 archivados y estado de C-09; verificar contrato 402/checkout/GET estado con design C-09 y registrar gate de aceptacion MP pendiente hasta backend aprobado e implementado/verificado, sin confundir mocks con integracion.
- [ ] 1.3 Ejecutar baseline `npm.cmd test`, `npm.cmd run lint` y `npx.cmd tsc -b` desde frontend y `pytest` desde backend en entorno autorizado; verificar salidas/exit en verification.md, registrar fallos preexistentes sin llamarlos RED C-10.
- [x] 1.4 Revisar lockfile/gestor y compatibilidad React 18/Vite 6 de router, Testing Library/jsdom y Playwright; verificar politica de scripts y revision de nuevas dependencias antes de instalar en apply, documentar versiones elegidas sin migrar stack.

## 2. Catalogo publico

- [ ] 2.1 Aplicar TDD a GET /catalogo-publico usando datos ficticios: activos vs inactivos y vacio, orden estable y allowlist sin PII; verificar >=2 casos por comportamiento y que /api/config sigue 401/403, documentar respuesta exacta.
- [ ] 2.2 Integrar proyeccion sena_politica/sena_centavos solo despues de campos backend C-09; verificar opcional vs obligatoria reflejan servidor sin defaults comerciales inventados, >=2 casos y contrato documentado; no crear migracion de pagos en C-10.

## 3. Cliente y sesion

- [x] 3.1 Aplicar TDD al cliente con PATCH, credentials auth y errores body unknown tipados; verificar >=2 casos por comportamiento incluyendo 409 alternativas, 402 checkout, 422 string/lista y error no JSON, sin filtrar HTML interno; documentar prefijos reales API.
- [x] 3.2 Aplicar TDD al proveedor de sesion en memoria, login/registro y /auth/me; verificar registro no emite sesion y login exitoso vs credenciales invalidas/429, >=2 casos por comportamiento; documentar politica password/tel AR existente sin OTP nuevo.
- [x] 3.3 Aplicar TDD a refresh coordinado y restauracion, error 401 vs 503 y logout; verificar single-flight y dos pestanas sin reutilizacion ciega, cambio de cuenta limpia vista, sin storage de tokens ni password y fallo de logout informado; documentar fallback seguro y evidencia >=2 casos por comportamiento.

## 4. Navegacion y consulta de horarios

- [x] 4.1 Aplicar TDD a rutas publicas y guard paciente, 404, returnTo allowlist y seleccion preservada; verificar anonimo vs paciente/otro rol, destinos externos rechazados y ninguna reserva enviada automaticamente tras login; documentar tabla de rutas sin C-11.
- [ ] 4.2 Aplicar TDD a filtros fecha/tratamiento/sillon desde catalogo real y GET /horarios-libres; verificar >=2 casos por filtro, zona AR cerca de cambio de dia, cargas/vacio/error y respuesta vieja abortada/ignorada; documentar mensajes y zona visible.
- [x] 4.3 Aplicar diseno responsive existente con foco/labels y botones tactiles mediante ciclos DOM; verificar >=2 recorridos teclado y movil 360px/desktop sin scroll horizontal, documentar tokens visuales y capturas ficticias sin redisenar dashboard.

## 5. Reserva y sena

- [x] 5.1 Aplicar TDD a resumen y POST /turnos autenticado con exito 201 y conflicto 409 con/sin alternativas; verificar >=2 casos por comportamiento, nueva seleccion explicita y consulta Mis reservas ante respuesta perdida sin reenvio ciego; documentar estados de negocio.
- [x] 5.2 Aplicar TDD a politica sena y 402 tipado con Idempotency-Key estable por accion/payload; verificar opcional/obligatoria, importe exacto ARS, destino seguro y modo mock visible solo desarrollo, >=2 casos por comportamiento; documentar dependencia C-09 y advertencia de cupo no retenido.
- [x] 5.3 Aplicar TDD a /pagos/retorno y consulta estado propia con polling acotado; verificar pendiente vs aprobado con turno_id, query approved falsificada, rechazo/expiracion/revision y ownership 404, >=2 casos por comportamiento; documentar no volver a cobrar en revision.
- [x] 5.4 Aplicar TDD a errores 401/403/422/503 y abort/offline en reserva/pago; verificar mensajes utiles sin exito falso ni retry automatico de escrituras, >=2 casos por comportamiento; documentar recuperacion de resultado ambiguo.

## 6. Mis reservas

- [x] 6.1 Aplicar TDD a lista propia, orden/estados/nombres y tolerancia desde /mis-reservas; verificar lista poblada/vacia y cambio de cuenta sin datos anteriores, >=2 casos por comportamiento; documentar que no se implementa agenda profesional.
- [x] 6.2 Aplicar TDD a confirmar/cancelar con PATCH y acciones servidor; verificar permiso true/false, exactamente 2h vs menos de 2h, estado actualizado y 422 por ventana vencida tras cargar, >=2 casos por comportamiento; documentar explicacion y confirmacion de cancelar sin UI reprogramar.

## 7. PWA y privacidad

- [x] 7.1 Aplicar TDD browser a manifest/iconos 192/512/maskable y actualizacion prompt; verificar instalabilidad/recarga directa y actualizacion diferida sin perder formulario, >=2 casos por comportamiento; documentar prueba localhost/HTTPS sin imagen Docker final.
- [ ] 7.2 Aplicar TDD browser service worker a shell offline, no-cache API y ausencia de cola POST/PATCH; verificar online/offline/reconexion, CacheStorage sin datos privados y navegacion HTML vs fetch JSON homonimo en origenes previstos, >=2 casos por comportamiento; documentar limites offline.
- [x] 7.3 Aplicar TDD a logout/cambio de cuenta y privacidad del almacenamiento; verificar memoria/cache tras dos pacientes ficticios, ausencia de tokens/PII en persistencia/logs/capturas y destino checkout validado, >=2 casos por control; documentar checklist de privacidad.

## 8. Integracion y evidencia

- [ ] 8.1 Ejecutar E2E contra backend real: anonimo ve libres, login obligatorio, reserva sin sena, Mis reservas, conflicto 409 y cancelar 422; verificar movil/desktop y cookies refresh reales, sin usar mocks como unica evidencia; adjuntar comandos/salidas sanitizados.
- [ ] 8.2 Tras gate C-09, ejecutar flujo integrado mock controlado y sandbox autorizado de checkout/retorno/estado con rechazo y pago sin cupo; verificar que nunca se confirma por redirect y documentar explicitamente si falta sandbox/credenciales, sin aprobar integracion con placeholder.
- [ ] 8.3 Hacer review/refactor y regresion frontend/backend, `npm.cmd test`, `npm.cmd run lint`, `npm.cmd run build` y E2E acordados; verificar matriz de >=2 casos por comportamiento y evidencia RED/GREEN/refactor completa, sin tocar C-11/C-12.
- [ ] 8.4 Verificar `openspec.cmd validate c-10-pwa-reserva-publica --strict`, contratos coordinados con C-09 y alcance final; entregar evidencia de accesibilidad/offline/privacidad sin dar por aprobada produccion ni tareas pendientes.

## Workflow follow-up

Revision ALTOS 2026-11-09 local (2026-11-10 UTC): 4.2 reabierta por contrato
backend de dia UTC vs seleccion AR. UI protegida y testeada, sin corregir ni
ocultar backend. Progreso conservador 16/25; gates integrados previos intactos.

| Hallazgo | Estado frontend | Evidencia |
| --- | --- | --- |
| H1 GET anterior recupera sesion al cerrar | Corregido | Generaciones, closing, invalidacion final; ambas ordenaciones diferidas y lecturas tardias |
| H2 Cookie refresh/login/logout fuera de lock comun | Corregido | Web Lock compartido; cola Node; browser sin Web Locks falla cerrado; 2 casos Chromium cross-tab, sin cookies backend reales |
| H3 500/503 permite repetir reserva directa | Corregido | Bloqueo de accion/seleccion a traves de navegacion; reconciliacion GET explicita; lista vacia no desbloquea; sin garantia por header |
| H4 Dia UTC vs AR | Proteccion UI verificada, contrato BLOQUEADO | Fecha completa; franjas fuera de dia visibles/deshabilitadas; 4.2 y aceptacion real abiertas |
| H5 Vite Windows / critical tooling | Parches compatibles verificados | Vite6.4.6, Vitest3.2.7, override Tinypool2.1.2 revisado; audit cero high/critical; 10 moderados/bajos documentados |

- Revisar evidencia con humano antes de archive y actualizar roadmap solo al cierre autorizado; este encargo no archiva ni marca changes implementados.
- Confirmar identidad/contacto publico reales al piloto sin introducir datos reales de pacientes en repo.
- No commits/push ni builds de imagenes finales; no C-11/C-12.
