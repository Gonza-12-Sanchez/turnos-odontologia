# Tasks

Planning 2026-11-10. Apply por etapas autorizado el 2026-11-10 («continúa»). El usuario eligió
sistema y mockups; la base revisión 1 fue aprobada el 2026-11-10 («si, adelante»).
Mockups revisión1 aprobados tras presentación; seams confirmados explícitamente.
Ver verification.md. No modificar backend ni activar pagos por implicación.

Por tarea de comportamiento: seam HTTP/DOM/browser, RED ejecutado por causa
esperada, mínimo GREEN, >=2 casos independientes feliz/error/borde, refactor y
regresión. Registrar comandos/fecha/exit/resultados y límites en verification.md
durante apply. Fixtures HTTP no acreditan backend, cookies ni concurrencia real.
Los gates de design.md bloquean el slice afectado, no todo el trabajo independiente.
No marcar un gate satisfecho por el estado «archivado» de su dependencia.

## 1. Aprobación visual y preparación

- [x] 1.1 Obtener aprobación explícita de `design-system/README.md` revisión 1 mostrando HTML y capturas 390×844/1440×900; verificar acta en README y estado JSON antes de crear mockups. Aprobada 2026-11-10 por el usuario: «si, adelante».
- [x] 1.2 Crear mockups HTML locales de todas las pantallas/estados listados en `design.md`, importando tokens/brand/activos compartidos; renderizar cada uno en ambos tamaños, inspeccionar y obtener aprobación explícita registrada en design.md y mockups/README.md antes de apply. Creados/renderizados 47 estados y 94 capturas, revisión1; aprobados 2026-11-10 por el usuario («continúa»). Ver [catálogo](mockups/catalogo.html), [evidencia](mockups/README.md) y [capturas](mockups/previews/).
- [x] 1.3 Obtener revisión de propuesta/spec/design, confirmar seams y solicitar apply separadamente; verificar autorización registrada, alcance frontend y exclusión de correctivos backend no aprobados. Usuario autorizó «continúa» y confirmó seams con «Confirmar estos puntos»; acta en verification.md.
- [x] 1.4 Ejecutar baseline frontend (`npm.cmd test`, lint y `npx.cmd --no-install tsc -b`) y revisar scripts/lockfile antes de instalar; backend/regresión integrada solo en instancia nueva descartable autorizada por TRUNCATE de fixtures. Registrar comandos, exit y fallos de entorno sin llamarlos RED. Baseline frontend118/118, lint y tsc exit0; backend no ejecutado, límites en verification.md.
- [x] 1.5 Crear matriz de gates G-fecha/G-acciones/G-auditoria/G-contexto/G-cobros/G-sena-config con versión de contrato, pruebas y dependencia correctiva aprobada; verificar cuáles slices pueden comenzar y mantener no satisfechos los que no tengan evidencia. Matriz en verification.md; seis gates backend siguen no satisfechos, sin correctivo aprobado en esta sesión.

## 2. Navegación y sesión del personal

- [x] 2.1 Aplicar TDD a guard/layout de /agenda y /config con SessionProvider único: secretaria/odontólogo/paciente/anónimo, restauración loading/503 y denegación sin fetch privado; verificar casos de ruta directa y sesión expirada y documentar matriz de rutas. Staff14/14 y regresión App68/68, RED/GREEN y límites en verification.md; matriz en frontend/README.md.
- [x] 2.2 Aplicar TDD a login y returnTo para rutas staff: destino interno/externo/backslash y rol incompatible, sin reenvío de escritura al entrar; verificar regresión de selección paciente C-10 y documentar navegación por rol. Staff24/24 + App68/68, tsc correcto; evidencia RED/GREEN y retornos hostiles en verification.md.
- [x] 2.3 Aplicar TDD a limpieza por identidad y respuestas tardías en vistas staff: logout, nueva cuenta, refresh concurrente; verificar que no se filtran datos ni se persisten tokens y documentar límites del Web Lock existente sin cambiar auth backend. Regresión DOM/HTTP de dos cuentas y single-flight pasa con Session existente sin cambios; límites documentados en verification.md.

## 3. Configuración independiente de cobros

- [x] 3.1 Implementar contratos runtime y listas paginadas de tres recursos mediante TDD HTTP/DOM: activo/inactivo, vacío/error, páginas y respuesta tardía; verificar rechazo de payload inválido y que odontólogo/paciente no consultan /api/config, documentar Page y filtros exactos. RED/GREEN y triangulación en verification.md; Staff38/38, lint/tsc exit0.
- [x] 3.2 Implementar formularios de tratamientos con TDD: duración positiva, precio decimal textual a centavos exactos o null, PATCH de campos cambiados y 422 por campo; verificar dos importes no redondos y límites INTEGER, documentar conversión sin float y política de seña bloqueada hasta G-sena-config. Alta/edición verificadas en DOM/HTTP,182/182 regresión+lint+build exit0; ciclos y bloqueo incierto en verification.md. No equivale a aceptación visual6.3 (hay diferencias) ni catálogo completo.
- [x] 3.3 Implementar edición/baja/reactivación de sillones con TDD: PATCH activo y preservación de históricos; verificar confirmación/cancelación de baja y errores 404/422, documentar que no se elimina físicamente ni se modifica agenda histórica. RED/GREEN y triangulación en verification.md;197/197 regresión+lint+build exit0;11 capturas y teclado360 verificados con HTTP ficticio. Sin DELETE ni requests de agenda, no acredita DB real ni cierre visual6.3.
- [ ] 3.4 Tras G-contexto, implementar alta de primer sillón desde contexto autorizado con TDD; verificar éxito y falta de contexto sin UUID hardcodeado/manual, documentar fuente real y mantener alta integrada pendiente si el gate no está satisfecho.
- [ ] 3.5 Implementar bloqueos con TDD: alcance general/específico, null explícito, fechas AR convertidas a aware, rango inválido y TURNOS_SOLAPADOS; verificar guardado con warning sin alterar turnos y documentar zona y advertencias. La aceptación temporal requiere G-fecha.
- [ ] 3.6 Tras G-sena-config, implementar política deshabilitada/opcional/obligatoria y monto combinado mediante TDD contra contrato verificado; probar PATCH coherente/incoherente y auditoría con datos ficticios, documentar que configurar política no activa pagos reales.

## 4. Agenda y gestión con gates específicos

- [ ] 4.1 Implementar DTO y vista de GET /agenda con TDD: grupos por sillón, filtros, orden, estado/tolerancia, carga/vacío/error y lectura abortada; verificar al menos dos sillones y filtros cambiados sin PII fuera de memoria, documentar shape real y falta de grupos vacíos.
- [ ] 4.2 Satisfacer G-fecha mediante evidencia del correctivo aprobado antes de aceptar agenda/reprogramación; verificar API real y navegador alrededor de 00:00 AR, franjas 21:00–24:00 y bloqueos/cache del mismo día, documentar que no se usa filtro cliente ni unión de días UTC como sustituto.
- [ ] 4.3 Implementar señales de sobreturnos y conflictos con TDD: flag/motivo y 409 con/sin alternativas; verificar texto independiente de color y elección explícita, documentar que no hay bypass EXCLUDE ni sobreturno automático.
- [ ] 4.4 Tras G-acciones, implementar confirmar/cancelar con TDD: permisos staff, confirmación, exactamente ventana configurada y ventana vencida/estado cambiado; verificar 422 sin éxito falso y ausencia de excepción por secretaria, documentar autoridad servidor.
- [ ] 4.5 Tras G-fecha/G-acciones, implementar reprogramación con TDD: nuevo hueco/sillón, 409 alternativas y 422 ventana; verificar original conservado ante fallo y fin servidor, documentar ausencia de retry automático y preservación de invariantes.
- [ ] 4.6 Implementar asistencia y marca explícita de sobreturno existente mediante TDD: secretaria/odontólogo según permiso de asistencia, motivo obligatorio y solo secretaria para sobreturno; verificar 403/422 y respuesta autoritativa, documentar que no se crean turnos solapados ni ausencias automáticas.
- [ ] 4.7 Tras G-auditoria, implementar historial con TDD desde contrato real autorizado: actor/fecha/origen, orden y error/indisponibilidad; verificar eventos persistidos contra backend y rechazo de datos inventados desde updated_at, documentar fuente y límites de lectura. No aceptar historial solo por mostrar fallback.
- [ ] 4.8 Implementar recuperación de escrituras inciertas mediante TDD: resultado perdido, lectura positiva/vacía/fallida y nueva identidad; verificar bloqueo de repetición y ausencia de reenvío al refresh/reconexión, documentar recuperación y escalamiento sin afirmar no-aplicación por ausencia.

## 5. Cobros condicionados a C-09

- [ ] 5.1 Antes de escrituras monetarias, satisfacer G-cobros con evidencia del correctivo aprobado: totales de lectura, clave requerida, replay estable, cierre único bajo concurrencia y consulta de resultado ambiguo; verificar casos con Postgres real aislado y registrar contrato. Sin gate, mantener envío bloqueado, sin marcar aceptado el flujo.
- [ ] 5.2 Aplicar TDD a selección autorizada de turno y resumen de /cobros: seña/total/saldo/precio null, payload inválido y acceso directo sin selección; verificar no PII en URL ni datos inventados desde catálogo público, documentar contrato de consulta y permisos.
- [ ] 5.3 Tras G-cobros, implementar registro incremental con TDD HTTP/DOM: efectivo/transferencia/MP manual, decimal textual exacto, clave estable y ejemplo 10000-3000=7000; verificar replay sin duplicación y 403/422, documentar dinero nuevo y aviso sin factura electrónica.
- [ ] 5.4 Tras G-cobros, implementar MONTO_DIFIERE/override y resultado incierto con TDD: motivo/nueva clave/nueva confirmación, rechazo sin efecto y timeout sin segundo cobro; verificar consulta real de resultado y evidencia auditada, documentar que MP manual no equivale a pago online verificado.

## 6. PWA, integración y aceptación

- [ ] 6.1 Probar durante cada slice y cerrar matriz browser SW/privacidad de /agenda, /cobros y /config: HTML vs API JSON por origen/modo, offline/reconexión, no queue, logout y dos cuentas; verificar CacheStorage/storage sin turnos/cobros/tokens y documentar capturas solo ficticias.
- [ ] 6.2 Ejecutar E2E integrado con UI real, API/DB/Redis aisladas y datos ficticios tras gates: navegación por tres roles, cookies/refresh/CORS, agenda día AR, 409/422, catálogo con warnings y cobro incremental/replay; registrar comandos y resultados sin contar skips, page.request ni mocks como recorrido completo.
- [ ] 6.3 Comparar implementación con mockups aprobados de la misma revisión: capturar cada pantalla/estado a 390×844 y 1440×900 y revisar 360px/teclado/foco/errores consola/red; registrar diferencias blocker/major/minor, pantallas verificadas/no verificadas y Visual verify real en design.md.
- [ ] 6.4 Ejecutar regresión frontend/C-10, lint/tsc/build de assets y backend cuando corresponda en entorno seguro; verificar `openspec.cmd validate c-11-pwa-agenda-gestion --strict`, revisar alcance/gates y entregar evidence final sin declarar completo mientras haya tareas o criterios pendientes.

## Workflow follow-up

- No archivar ni marcar C-11 completo hasta aceptación integral y revisión humana;
  cobros bloqueados o historial inexistente no equivalen a scope terminado.
- Si se decide separar funcionalidades bloqueadas, revisar alcance y artefactos
  explícitamente con el usuario; no eliminar tareas para lograr cierre.
- No modificar C-09/C-10, iniciar C-12, commitear/pushear, desplegar ni construir
  imágenes finales por implicación de este plan.
