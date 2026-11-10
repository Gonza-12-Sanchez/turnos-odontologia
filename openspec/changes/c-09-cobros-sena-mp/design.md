# Design

## Context

Ver proposal.md para motivacion. Estado observado: `ReservaService.reservar` usa `sena|requiere_sena|deposit` enviados por cliente y lanza 402 antes de verificar disponibilidad; `Tratamiento` no tiene politica de sena. `Cobro` requiere `turno_id`, almacena INTEGER centavos, permite solo pendiente/aprobado y no tiene unicidad MP. No existe implementacion en `app/cobros`. Se conserva EXCLUDE y se reutiliza el circuito C-08 de recordatorios, sin usar la reserva publica como bypass interno de pago.

Dependencias archivadas: C-05 (2026-11-04); auth C-03 con correctivo; C-06 (2026-11-04) y C-08 (2026-11-05) disponibles. No se infiere que la suite actual este verde: C-08 documenta un fallo preexistente de auth y debe revalidarse en baseline futuro.

## Goals / Non-Goals

**Goals:** separar dinero recibido de reserva efectiva, preservar centavos exactos, reconocer cada pago una sola vez y ofrecer contratos consumibles por C-10. Usar Postgres como fuente durable; Redis no decide si se cobro.

**Non-Goals:** retenciones temporales de cupo, captura de tarjetas, reembolso automatico, facturacion, ledger contable completo, UI C-11 y hardening general C-12. No cambiar las transiciones de turnos ni relajar EXCLUDE.

## Decisions

### 1. Gate de aprobacion y ownership

Estado: APROBADO PARA IMPLEMENTACION EN MODO PRUEBA por el usuario el 2026-11-09, con pedido separado de apply en esta sesion. El usuario ratifico la aprobacion explicita "apruebo procede" del diseno presentado. Alcance autorizado: backend, migraciones, tests y documentos C-09; sin pagos reales, produccion, frontend ni artifacts C-10. La compensacion es manual a cargo del consultorio, sin retencion de cupo. Ver acta y limites en verification.md. La aprobacion no sustituye baseline verde ni evidencia TDD; la activacion real y sus gates siguen pendientes.

C-09 posee politica y campos administrativos de sena, 402, intentos, webhook, cobros y lectura de incidencias. C-10 posee catalogo publico y UI; solo proyecta/consume estos campos una vez disponible el backend. Alternativa descartada: delegar politica al frontend o abrir configuracion administrativa.

### 2. Politica servidor y compatibilidad real

Proponer en Tratamiento `sena_politica=deshabilitada|opcional|obligatoria` (default deshabilitada) y `sena_centavos` nullable. En opcional/obligatoria exigir entero estricto 1..2147483647; en deshabilitada null. No usar porcentaje de precio nullable. Extender schemas POST/PATCH/GET existentes `/api/config/tratamientos`, validacion combinada de PATCH y auditoria C-04; permisos intactos. No precargar importes comerciales ni activar tratamientos sin decision del PO.

En `POST /turnos` conservar los tres flags existentes porque forman parte del contrato C-05 y tests; en modo opcional cualquiera true solicita sena. En obligatoria ni false ni omision evitan 402. En deshabilitada un true devuelve 422 (no fabricar un checkout sin precio). El frontend nuevo envia solo `sena`; los otros no se propagan a nuevos contratos. Validar existencia, actividad y hueco antes de pedir pago. Pago deshabilitado por entorno con tratamiento obligatorio devuelve 503, nunca crea turno sin cobrar.

### 3. Intento y pagos externos separados del Cobro

Proponer migracion ADITIVA posterior a aprobacion:

| Persistencia | Datos y restricciones propuestas |
|---|---|
| IntentoSena | UUID opaco, paciente FK, sillon/tratamiento FK, inicio/fin TIMESTAMPTZ, snapshot duracion/monto/politica, moneda ARS, estado, preference_id nullable unico, turno_id nullable unico, expires_at y timestamps aware |
| Idempotencia de solicitud | clave de cliente acotada, usuario y operacion; UNIQUE(usuario,operacion,clave), huella canonica del payload; mismo contenido recupera resultado, distinto 409; durabilidad al menos mientras exista el intento/cobro |
| PagoMP | payment_id externo unico, intento FK, estado proveedor, monto/moneda/receptor/modo verificados, resultado aplicado o incidencia, timestamps; multiples pagos de la misma preferencia quedan trazables sin crear multiples turnos |
| Cobro existente | mantener FK turno NOT NULL y enums existentes, UNIQUE referencia_mp no null tras inspeccionar duplicados; solo pago aprobado y aplicado genera sena MP |
| AuditoriaCobro | actor autenticado o proveedor, fecha aware, accion, cobro/intento vinculado, centavos, motivo de override o incidencia, sin payload completo del proveedor |

Estados de intento publicos: `creando_checkout`, `pendiente`, `aprobado`, `rechazado`, `expirado`, `requiere_revision`. `aprobado` significa turno y cobro persistidos, no simplemente MP approved. Guardar estado proveedor separado. Rechazos de un payment_id no invalidan otro pago aprobado; reconsultar siempre el estado actual MP. No degradar aprobado a pendiente por notificaciones fuera de orden; refunded/charged_back abre revision conservando historia y no borra turno automaticamente.

Alternativa descartada: Cobro con turno nullable o JSON en Redis. El primero debilita su semantica local y el segundo pierde trazabilidad antes de crear el turno.

### 4. Contrato HTTP compartido con C-10

Rutas exactas, sin prefijo `/api` global (ver `main.py`):

| Operacion | Entrada | Resultado |
|---|---|---|
| POST /turnos | TurnoCreate actual; `Idempotency-Key` obligatorio en rama de sena | 201 TurnoOut sin sena; 402 `{detail,checkout}` si corresponde; 409 `{detail,alternativas}`; 422/503 segun causa |
| POST /pagos/sena | paciente; `{sillon_id,tratamiento_id,inicio}` y `Idempotency-Key` | 201 `{checkout}` para intento nuevo, 200 replay; solo politica opcional/obligatoria; 409 hueco ocupado o clave reutilizada con otro payload |
| GET /pagos/sena/{intento_id} | paciente propietario | 200 `{id,estado,monto_centavos,moneda,expires_at,turno_id,requiere_contacto}`; 404 si ajeno/inexistente; no PII ni tokens MP |
| POST /webhooks/mercadopago | evento payment firmado | 200 si durablemente aplicado, duplicado o incidencia registrada; 401 firma invalida; 400 formato ambiguo; 503 error transitorio para reintento MP |
| POST /cobros | secretaria; `{turno_id,monto_centavos,medio,tipo,override_motivo?}` y `Idempotency-Key` | 201 `{cobro,sena_acumulada_centavos,total_cobrado_centavos,saldo_referencia_centavos,warnings,facturacion_electronica:false}`; 200 replay |
| GET /cobros?turno_id= | secretaria/odontologo o paciente propietario | 200 lista autorizada con totales; 404 recurso ajeno; no referencias privadas del proveedor para paciente |
| GET /pagos/incidencias | solo secretaria, page/page_size 1..100 | lista minima de casos requiere_revision, estado y referencia operacional para resolver en panel MP |
| PATCH /pagos/sena/{id}/resolucion | solo secretaria; `{resolucion:reembolsado|resuelto_en_consultorio,motivo,referencia_operacion}` | audita resolucion operacional; no afirma haber llamado una API de refund ni crea turno |

`checkout` queda fijado como `{provider:"mercadopago",status:"pendiente",intento_id,checkout_url,expires_at,monto_centavos,moneda:"ARS",modo:"mock"|"sandbox"|"production"}`. La respuesta 402 persiste el intento aun cuando no crea turno; no lanzar una excepcion que revierta esa transaccion. Idempotency-Key ausente en rama de sena devuelve 422; sin sena no se agrega ese requisito al contrato existente.

Los rechazos de proveedor tienen estado de pago sin turno; 402 nunca es prueba de exito. En mocks `checkout_url` apunta a ruta local de retorno con modo visible, no a MP real; no hay endpoint publico que apruebe mock. En sandbox/production validar URL HTTPS de MP por allowlist, no aceptar URL de retorno desde cliente. Retornos fijados por servidor a `/pagos/retorno?intento_id=<uuid>`; MP puede agregar query params pero no son autoridad.

Si el checkout aun no existe por respuesta ambigua del proveedor, responder 503 `{detail,code:"CHECKOUT_NO_VERIFICADO",intento_id}` en lugar de fabricar checkout_url o devolver 402 incompleto. El paciente puede consultar ese intento; un replay de la misma clave conserva su identidad. Un 402 solo se emite con checkout utilizable. Registrar override que sigue a MONTO_DIFIERE requiere nueva clave porque el payload cambio; el 409 previo no representa ingreso monetario.

### 5. Checkout Pro asincronico y recuperacion

Usar HTTPX ya instalado, host fijo `https://api.mercadopago.com`, timeout connect 2s/read 5s y total acotado, sin bloquear event loop ni mantener locks durante HTTP. Crear preferencia `POST /checkout/preferences`, `external_reference=intento_id`, item generico "Sena de reserva", cantidad 1, `currency_id=ARS`, notification_url configurada y back_urls fijas. Convertir centavos mediante Decimal y serializacion decimal JSON exacta; nunca float aun si ejemplos MP lo usan.

Primero persistir intento e idempotencia, luego llamada MP y persistir preference_id/checkout. TTL propuesto 15 minutos para checkout (no retiene horario). Un timeout despues de enviar la creacion es resultado ambiguo: mantener `creando_checkout/requiere_revision`, no recrear automaticamente preferencia ni asumir que MP soporta idempotencia para esa ruta. La referencia permite reconciliar el webhook aunque la respuesta inicial se pierda. Una falla comprobada previa al envio permite reintento acotado. No usar reintentos ciegos de POST.

Webhook: parseo acotado y no ambiguo de `data.id`, tipo payment y headers `x-signature`, `x-request-id`; validar HMAC-SHA256 en tiempo constante con secreto de webhook, manifest documentado por MP y normalizacion oficial. Proponer tolerancia timestamp 5 minutos con reloj UTC; validar unidades/formato y compatibilidad con redelivery en sandbox antes de activar (no simplemente rechazar reintentos legitimos). GET `/v1/payments/{id}` con credencial backend; validar id, external_reference, collector_id esperado, live_mode, currency ARS y monto EXACTO contra snapshot. La firma no prueba estado ni importe. No seguir URLs enviadas por webhook.

Al aprobar, tomar lock de intento y registrar payment_id unico en transaccion corta. Revalidar actividad, duracion vigente vs snapshot, disponibilidad sin cache, inicio futuro y expiracion segun `date_approved` del proveedor, no hora de llegada del webhook. Si `date_approved<=expires_at` y llega tarde, se puede aplicar solo si el hueco aun es valido; si se pago despues, revision. Insertar Turno reservado + Cobro sena aprobado + referencia_mp=payment_id + auditoria y marcar intento aprobado en UNA transaccion. Mantener EXCLUDE como arbitro final; manejar exclusion_violation especificamente con savepoint o transaccion de recuperacion para registrar incidencia. No capturar cualquier error como conflicto de negocio.

Tras commit invalidar disponibilidad y usar circuito C-08 de recordatorios idempotente. Una falla Redis no deshace dinero/turno; recuperacion durable de recordatorio, no perdida silenciosa. Un reconciliador acotado recupera intentos pendientes ante webhook perdido consultando pagos por referencia/IDs en proveedor; usa la misma aplicacion idempotente que webhook, sin generar un segundo checkout. No mantener transacciones abiertas durante consultas MP.

### 6. Cupo no retenido y compensacion explicita

Propuesta a aprobar: NO retener cupo antes de pago, consistente con C-05 que no crea turno. Mostrar antes de pagar que la disponibilidad se vuelve a verificar. Si llega pago aprobado con hueco ocupado, bloqueo, duracion cambiada, inicio pasado, expiracion o segundo pago aprobado del mismo intento: registrar PagoMP e incidencia `requiere_revision`, no crear turno/sobreturno ni segundo Cobro. Paciente ve "Pago recibido, reserva no confirmada; contactar consultorio". Secretaria resuelve reembolso desde panel MP y deja referencia/motivo en endpoint auditado. No se habilita produccion sin responsable y procedimiento de devolucion aprobados. Alternativa retencion con EXCLUDE compartido entre intents y turnos requiere nuevo diseno de concurrencia y no se agrega implicitamente.

### 7. Cobro local y conciliacion sin duplicacion

`monto_centavos` es SIEMPRE dinero NUEVO recibido, entero estricto positivo dentro de INTEGER; `tipo=total` significa cierre local, no volver a cobrar el precio bruto. Ejemplo ficticio: precio 10000, sena aprobada 3000, nuevo cobro total 7000 -> total_cobrado=10000, saldo=0, dos filas, nunca 13000. Lock de turno serializa conciliacion y doble cierre; un replay devuelve mismo cobro, otra clave despues de cierre devuelve 409.

Precio_referencia es orientativo: para cierre se compara suma previa + nuevo monto con precio actual. Si difiere, primera peticion sin override devuelve 409 `{code:"MONTO_DIFIERE",esperado_centavos,recibido_centavos}` sin persistir; repetir con motivo no vacio permite y devuelve warning auditado. Precio null produce warning PRECIO_SIN_REFERENCIA sin inventar saldo (`null`). `saldo_referencia` minimo cero con diferencia/excedente visible, no dinero negativo oculto. Una sena duplicada para el mismo turno se rechaza, un cierre por cero no crea movimiento. Mercado Pago manual en mostrador es registro declarado por secretaria (`estado_mp=null`), no se finge webhook verificado; sena online usa referencia unica y estado aprobado. No se modifica estado de Turno para indicar cobrado: su maquina no contiene ese estado.

### 8. Threat model, privacidad y modos

Fronteras: paciente->API, secretaria->cobros, MP->webhook, API->MP, Postgres/Redis->worker, backend->PWA. Riesgos: omitir pago con false, IDOR de intentos, replay/firma falsa, doble pago, importe/moneda/receptor alterados, SSRF, filtracion de tratamiento o tokens. Controles: ownership por paciente derivado de JWT, RBAC, constraints unicos, locks cortos, verificacion de firma y GET servidor, HTTPS y host fijo, limites de payload y reintentos, no-store en respuestas privadas, logs solo IDs operacionales y codigos, sin tarjetas, nombres de tratamiento ni notas clinicas en MP.

Variables nuevas propuestas: MP_MODE=disabled|mock|sandbox|production (default disabled), MP_WEBHOOK_SECRET, MP_COLLECTOR_ID, MP_NOTIFICATION_URL; reutilizar MP_ACCESS_TOKEN y FRONTEND_URL. Secretos solo env, sin leer ni imprimir valores reales en esta propuesta. Mock solo entornos no productivos, etiquetado visible y sin bypass de webhook desplegado. Sandbox requiere cuenta/app AR y usuarios/tarjetas de prueba segun MP, receptor esperado, endpoint HTTPS y firma real. Production requiere credenciales productivas separadas y acta de aprobacion; fallo de configuracion debe ser fail-closed.

Minimizar a IDs, montos/estado y fechas; no persistir payloads completos, PAN, documentos ni payer innecesario. Purga propuesta de intentos sin pago a 30 dias; para pagos/auditoria se requiere retencion legal/comercial aprobada y acceso restringido antes del piloto. No borrar evidencia de dinero al expirar checkout. Ni PII ni token en checkout metadata, telemetry, URL de retorno o CacheStorage.

### 9. Strict TDD y evidencia futura

Seams propuestos para confirmacion humana: HTTP API (auth/RBAC, cuerpos/errores), adaptador MP en frontera HTTP, persistencia Postgres con concurrencia observable, worker/reconciliacion y enqueue C-08. Simular proveedor/clock en fronteras, NO repositorios internos para sustituir constraints. Baseline backend completo y frontend existente antes de cambios; cada fallo preexistente debe tener evidencia y no contarse como RED.

Por comportamiento: ejecutar un test nuevo y observar RED por causa esperada; implementar minimo GREEN; agregar segundo caso independiente (triangulacion >=2) y ejecutar su RED/GREEN si requiere comportamiento adicional. Nunca escribir todos los tests de golpe ni implementar antes de RED. Despues review/refactor manteniendo verdes y ejecutar regresion completa. Evidencia por ciclo: seam, caso, comando, fecha, salida/exit RED y GREEN, dos entradas/resultados independientes, refactor y regresion. Los scenarios de specs son aceptacion, NO tests escritos ahora.

## Risks / Trade-offs

- Pago sin cupo -> incidencia durable y devolucion manual; requiere aceptar expresamente este costo frente a agregar retenciones.
- Preferencia creada pero respuesta perdida -> no reintentar POST a ciegas; preservar intento y reconciliar referencia.
- Eventos duplicados/fuera de orden y multiples payment_id -> unicidad por pago mas lock de intento, no solo message_id.
- Fallo DB tras approved MP -> no enviar 200 hasta persistencia durable; reintento y reconciliacion sin duplicados.
- Ventana de firma vs redelivery legitimo -> verificar comportamiento Checkout Pro AR en sandbox; si exige cambiar politica, revisar diseno antes de activar.
- KB abierta password/OTP -> C-03 ya resolvio password; no redisenar auth en C-09.

## Migration Plan

1. Obtener aprobacion del diseno y seams, solicitud separada apply y baseline. Cargar skills de esquema/guardian antes de escribir migraciones; este documento no es una migracion.
2. Inspeccionar duplicados de referencia_mp en desarrollo sin exponer datos, disenar resolucion sin borrado automatico y crear cambios aditivos con defaults deshabilitados. Verificar upgrade/downgrade solo en base de prueba, constraints monetarios, TIMESTAMPTZ e indices.
3. Completar ciclos TDD mock y regresion. Configurar sandbox por env y validar firma/redirect, pagos aprobados/rechazados, duplicados y pago sin cupo con dinero ficticio.
4. Activar produccion solo con autorizacion separada, importes por tratamiento, responsable de devoluciones, retencion aprobada y evidencia sandbox. No ejecutar estos pasos en planning.
5. Rollback operacional: detener nuevos checkouts por feature flag, mantener webhooks/reconciliacion de pagos emitidos e incidencias; no volver a backend que permita bypass de sena. No downgrade destructivo ni borrar cobros. Restaurar UI sin perder registros.

## Approval Checklist

- [ ] PO aprueba modo deshabilitada/opcional/obligatoria y monto fijo por tratamiento; importes se configuran despues, nunca inferidos de precio.
- [ ] PO acepta no-retencion, TTL 15 min, aprobacion por fecha proveedor y compensacion manual; designa responsable de incidencias/devoluciones.
- [ ] Equipo aprueba contratos 402/checkout/estado, semantica de monto incremental, override 409 auditado y persistencia propuesta.
- [ ] Equipo confirma seams TDD, privacidad/retencion y estrategia mock primero, sandbox despues, produccion solo autorizada.

## References

Context7 consultado para documentacion oficial MP Checkout Pro (`POST /checkout/preferences`, external_reference/back_urls/notification_url) y notificaciones (`x-signature`, manifest HMAC). Fuentes devueltas: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/how-tos/improve-payment-approval/industry-data y https://www.mercadopago.com.br/developers/pt/docs/wallet-connect/notifications. Los resultados disponibles incluyen ejemplos BR y otros productos: no copiar campos CPF/BRL ni asumir equivalencia de producto. El intento de acceso directo a la URL AR `checkout-pro/additional-content/notifications/webhooks` devolvio 404; no se verifico end-to-end Checkout Pro AR ni sandbox en planning. Revalidar la documentacion especifica antes de escribir el adaptador y luego contrastar con sandbox; cualquier divergencia material vuelve a aprobacion, nunca desactivar firma.
