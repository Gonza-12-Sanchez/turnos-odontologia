# Tasks

APPLY AUTORIZADO EN MODO PRUEBA el 2026-11-09. Aprobacion humana y pedido separado registrados en verification.md. Preparacion de dependencias locales aisladas autorizada y completada en Temp/opencode/c09-venv, sin nueva aprobacion ni cambios globales. Ruff y 29 tests existentes sin servicios pasan; baseline completo bloqueado por falta de Redis/Postgres reales aislados, NO por fallo de comportamiento demostrado. No escribir codigo, tests nuevos ni migraciones hasta baseline completo verde. Instalar servicios/sistema o tocar datos existentes NO esta autorizado. Estado CLI planning completo NO prueba implementacion.

Contrato de ejecucion para CADA tarea de comportamiento: una slice vertical por vez; test nuevo -> RED ejecutado por causa esperada -> implementacion minima -> GREEN; triangulacion >=2 casos independientes por comportamiento (feliz + error/borde), con segundo ciclo RED/GREEN si agrega comportamiento. Registrar seam, comando, salida/exit y fecha RED/GREEN en verification.md. Fallo de entorno o baseline no cuenta como RED. Review/refactor posterior con tests verdes y regresion. No escribir todos los tests primero ni implementar primero. Documentacion de cada grupo se entrega con ese grupo.

## 1. Aprobacion y baseline

- [x] 1.1 Obtener aprobacion humana explicita de design.md: politica fija por tratamiento, no-retencion, TTL 15 min, compensacion manual con responsable, persistencia y contratos; verificar acta/fecha sin casillas autoaprobadas.
- [x] 1.2 Confirmar con humano seams HTTP/RBAC, frontera HTTP MP, concurrencia Postgres y recordatorios/reconciliacion, privacidad/retencion y modos; verificar matriz escenario->seam aprobada y solicitud separada de implementacion antes de escribir tests o codigo.
- [ ] 1.3 Ejecutar baseline existente backend `pytest` y `ruff check .` desde backend y frontend `npm.cmd test` desde frontend en entorno de prueba autorizado; verificar salida/exit en verification.md, aislar fallo auth reportado C-08 si persiste y no llamarlo RED del change.
- [ ] 1.4 Verificar documentacion oficial Checkout Pro Argentina, firma/redelivery, GET payment, busqueda por external_reference y credenciales de prueba sin imprimir secretos; entregar nota de compatibilidad y fixtures ficticios definidos, volver a aprobacion si cambia contrato/materialmente diseno.

## 2. Politica y persistencia seguras

- [ ] 2.1 Aplicar ciclos TDD a politica deshabilitada/opcional/obligatoria y validacion combinada PATCH administrativa; verificar >=2 casos por regla, 401/403 intactos, centavos estrictos, auditoria y defaults deshabilitados; documentar nuevos campos junto al endpoint.
- [ ] 2.2 Aplicar ciclos TDD a intento previo sin turno, pagos externos unicos, idempotencia y auditoria con base turnos_test; solo tras RED crear modelos/migracion aditiva, verificar unicidad bajo concurrencia, rollback y TIMESTAMPTZ; documentar estados y restricciones.
- [ ] 2.3 Inspeccionar referencias MP duplicadas antes de indice unico sin borrarlas automaticamente; verificar reporte sin PII, upgrade/downgrade sobre base descartable, constraints monetarios y guardian/invariantes pertinentes sin alterar EXCLUDE; anexar evidencia al grupo.

## 3. Cobros locales

- [ ] 3.1 Aplicar TDD al POST /cobros con RBAC, medios/tipos y monto nuevo recibido; verificar >=2 casos por comportamiento, floats/bools rechazados y ejemplo 10000-3000=7000, no 13000; documentar contrato incremental y aviso sin factura.
- [ ] 3.2 Aplicar TDD a discrepancia 409 MONTO_DIFIERE, override con motivo y precio nullable; verificar warning, autor/fecha y rollback ante auditoria fallida, con >=2 casos independientes por comportamiento; documentar semantica esperado/recibido.
- [ ] 3.3 Aplicar TDD a Idempotency-Key, payload distinto y cierres concurrentes; verificar un solo cierre y una sola sena por turno incluso con distintas claves y replays, con resultados observables API; documentar replay 200 y conflicto 409.
- [ ] 3.4 Aplicar TDD a GET /cobros y distincion MP manual vs online; verificar propio/ajeno 200/404, anonimo 401 y roles, no referencias privadas para paciente ni estado aprobado falso; documentar proyecciones autorizadas.

## 4. Checkout y contrato 402

- [ ] 4.1 Aplicar TDD al adaptador HTTP asincronico MP con HTTPX y mock en frontera; verificar payload ARS exacto para >=2 importes no redondos, host fijo, referencia opaca, timeouts y ausencia de PII; documentar variables env con placeholders sin secretos.
- [ ] 4.2 Aplicar TDD al POST /pagos/sena e idempotencia de creacion; verificar intento propio, checkout 201/replay 200, clave distinta de payload 409 y ausencia de turno; cubrir timeout ambiguo sin recreacion ciega y documentar recuperacion.
- [ ] 4.3 Aplicar TDD a POST /turnos: politica servidor vence flags false/omitidos, flags opcionales existentes, disponibilidad antes de pago y 402 durable; verificar >=2 casos por rama 201/402/409/422/503, Idempotency-Key y contrato checkout compartido con C-10; actualizar ejemplos API ficticios.
- [ ] 4.4 Aplicar TDD a GET /pagos/sena/{id}, vencimiento y modos disabled/mock/sandbox/production; verificar propietario/ajeno, sin secretos, fail-closed y mock imposible en produccion, >=2 casos por comportamiento; documentar estados publicos y no-store.

## 5. Webhook y aplicacion monetaria

- [ ] 5.1 Aplicar TDD a firma HMAC, formato/normalizacion/tiempo y consulta payment servidor; verificar firma valida/invalida, replay/redelivery legitimo y discrepancias id/importes/ARS/receptor/live_mode, >=2 casos por control; documentar formato admitido sin guardar payloads sensibles.
- [ ] 5.2 Aplicar TDD a aprobacion atomica Turno+Cobro+auditoria+intento; verificar approved/rejected, fallo DB reintentable y unicidad payment_id con webhook duplicado concurrente, >=2 casos por comportamiento; documentar cuando se reconoce 200/503.
- [ ] 5.3 Aplicar TDD a pago aprobado sin cupo, bloqueo, duracion cambiada, inicio pasado y aprobacion tardia; verificar EXCLUDE con carrera real entre sesiones y registro durable requiere_revision sin turno/sobreturno, >=2 casos por regla; documentar que dinero no equivale a reserva.
- [ ] 5.4 Aplicar TDD a varios payment_id del mismo intento y eventos fuera de orden/refunded/charged_back; verificar una sola reserva/sena y pagos extra o reversas conservados como incidencias sin borrar historia, >=2 casos por comportamiento; documentar transiciones.

## 6. Recuperacion e incidencias

- [ ] 6.1 Aplicar TDD al reconciliador acotado de intentos/pagos ante webhook perdido y timeout checkout; verificar mismo camino idempotente con >=2 casos y ningun segundo checkout ciego, documentar ejecucion y limites de reintentos.
- [ ] 6.2 Aplicar TDD a invalidacion de disponibilidad y recordatorio C-08 despues del commit; verificar enqueue normal y Redis caido con recuperacion durable sin duplicar turno/cobro, >=2 casos por comportamiento; documentar recuperacion y no rollback monetario.
- [ ] 6.3 Aplicar TDD a lista paginada de incidencias solo secretaria y PATCH resolucion con referencia/motivo; verificar acceso no autorizado, resolucion auditada y no refund automatico, >=2 casos por comportamiento; entregar runbook de devolucion manual y responsable antes de activar pagos reales.
- [ ] 6.4 Aplicar TDD a minimizacion de logs/respuestas privadas y purga de intentos sin pago segun retencion aprobada; verificar sin tarjetas/PII/tokens ni perdida de evidencia monetaria, con casos sin pago vs pago recibido; documentar retencion operacional.

## 7. Integracion y evidencia

- [ ] 7.1 Ejecutar review/refactor y regresion completa backend, pruebas concurrentes reales Postgres y contrato 402/estado contra consumidor C-10 cuando disponible; verificar suites y matriz >=2 casos por comportamiento con evidencia RED/GREEN/refactor, sin atribuir errores baseline a features.
- [ ] 7.2 Con autorizacion y credenciales sandbox externas al repo, verificar checkout/retorno, firma real, aprobacion/rechazo, duplicados y cupo perdido con datos ficticios; entregar evidencia sanitizada y marcar explicitamente no probado si no hay sandbox, sin sustituirlo por mock.
- [ ] 7.3 Revisar alcance, amenazas y rollback; verificar `openspec.cmd validate c-09-cobros-sena-mp --strict`, contrato C-10 sin divergencias y checklist de aprobacion; no habilitar produccion ni archivar con evidencia incompleta.

## Workflow follow-up

- Pedir revision humana de implementacion y evidencia antes de archive; ejecutar archive y actualizar CHANGES.md solo con autorizacion correspondiente, nunca en esta propuesta.
- Produccion requiere aprobacion independiente, importes por tratamiento y retencion/responsable de devoluciones; ni mock ni sandbox autorizan cobros reales.
- No tocar C-11/C-12 ni ejecutar commits, push o builds de imagenes finales.
