# Design

## Context

Ver proposal.md. Inspección estática 2026-11-10, sin suites ejecutadas, servicios
de aplicación iniciados ni datos reales:

- `frontend/src/App.tsx` solo tiene rutas públicas/paciente; `PatientOnly` no sirve
  para staff. `AuthPage.safeReturn` excluye /agenda, /config y /cobros.
- Sesión C-10 en memoria con generaciones y Web Locks: reutilizar sin debilitar
  logout/refresh. `shared/api/client.ts` tiene GET/POST/PATCH, no DELETE.
- `GET /agenda?fecha=&sillon=&estado=` devuelve `AgendaSillonOut[]`, no Page.
  `AgendaTurnoOut` incluye nombres/estado/origen/tolerancia/sobreturno, pero no
  acciones permitidas ni historial de actor/fecha.
- `AgendaLecturaRepository` usa medianoche UTC, al igual que disponibilidad;
  mostrar horas AR no soluciona selección del día. No mezclar correcciones
  silenciosas de fechas C-05/C-07 con presentación.
- `GestionTurnosService` cambia estado/origen y updated_at sin persistir una
  secuencia explícita actor/fecha. No se observó endpoint de historial.
- PATCH confirmar/cancelar/reprogramar: secretaria/paciente; marcar-asistencia:
  secretaria/odontólogo según API/spec existente. Conservar permiso efectivo,
  sin redefinir al odontólogo como solo lectura donde el backend permite asistencia.
- Catálogo C-04: Page con activo true/false, soft delete, warnings de bloqueos.
  POST sillón exige consultorio_id; no hay contexto administrativo de consultorio
  accesible identificado para el primer sillón. No hardcodear UUID ni elegir
  consultorio desde un registro arbitrario.
- Cobros C-09: GET lista sin totales, clave de POST opcional, replay con totales
  cero y ausencia de rechazo de segundo cierre. La UI no arregla estas garantías.
  API de incidencias montada bajo /webhooks; no consumir una ruta planificada
  inexistente ni ampliar este change a integraciones MP.

## Goals / Non-Goals

**Goals:** una sola sesión por identidad, contratos tipados, formularios concretos,
estados verificables y entrega incremental sin ocultar gates pendientes.

**Non-Goals:** modificar backend/migraciones en este apply sin propuesta y
aprobación específicas; activar MP, fabricar auditoría, aceptar C-11 parcial,
crear usuarios staff o reservas de mostrador sin contrato existente aprobado.

## Decisions

### 1. Fronteras y orden por slice

Dependencias archivadas no implican aceptación funcional. No se reabre, modifica
ni desarchiva C-09/C-10 en este planning. El correctivo deberá acordarse por separado.

| Gate | Evidencia que falta | Bloquea | Trabajo independiente permitido tras aprobación visual y apply |
|---|---|---|---|
| G-visual | Sistema rev1 y mockups rev1 aprobados por usuario 2026-11-10 | Satisfecho para revisión1; no satisface gates backend | Apply frontend por etapas autorizado |
| G-fecha | Día AR coherente en agenda/disponibilidad; medianoche, bloqueos e invalidación probados | Aceptación de agenda diaria y reprogramar | Contratos/DOM con fixtures frontera, navegación, config no temporal |
| G-acciones | Proyección o contrato aprobado de acciones/ventana configurada para staff | Aceptación de controles y ventana en agenda | Lectura de agenda, no calcular política crítica con reloj cliente |
| G-auditoria | Persistencia actor/fecha/origen y lectura autenticada real | Historial y aceptación de gestión auditable | Presentar indisponibilidad sin inventar eventos |
| G-contexto | Contexto seguro de sede y consultorio_id para primer sillón | Alta integrada de sillón | Listar/editar/desactivar recursos existentes, tratamientos y bloqueos |
| G-cobros | Contrato verificado de lectura/totales, clave requerida, replay, único cierre concurrente, resolución de timeout | Escrituras y aceptación integrada de /cobros | Diseño y pruebas de contrato UI con HTTP ficticio claramente identificado |
| G-sena-config | Política C-09 combinada, auditoría y separación disabled/sandbox verificadas | Edición de política/importes de seña | Resto de catálogo, mostrar política actual sin editar |

No reemplazar gates por «ocultar botón» y marcar terminado. Cobros no se habilita
con un simple env booleano: el despliegue necesita evidencia de versión backend
y contrato validado, sin endpoint/capability ficticio. Si falta, no se libera el slice.
Alternativa rechazada: exigir terminar todo C-10 antes de cualquier C-11. Tampoco
se acepta tomar MP sandbox como requisito de catálogo/agenda o de efectivo local.

### 2. Arquitectura frontend y sesión

Mantener React18/Router6/Vite6 y lockfile. Guard/layout anidado para personal;
SessionProvider único, rutas existentes intactas. /agenda secretaria/odontólogo;
/config y registro de /cobros secretaria. Acceso paciente no dispara consultas
administrativas. 401 restaura/solicita login según sesión; 403 no refresca permisos.
ReturnTo allowlist exacta incorpora rutas staff, rechaza destinos externos,
backslashes y //; tras login se verifica rol antes del retorno. Sin mutar auth backend.

Módulos previstos: `features/agenda/{AgendaPage,TurnoActions,...}`,
`features/config/{ConfigPage,...}`, `features/cobros/{CobrosPage,...}` y contratos
en `shared/api`. Mantener estado local, sin estado global ni librería de calendario
nuevos. Lecturas independientes paralelas, AbortController y clave de filtros/
identidad para ignorar resultados tardíos. No confiar en el parámetro genérico
del cliente como validación runtime: leer unknown y validar DTOs en frontera.

Alternativa rechazada: otro proveedor de sesión o tokens persistentes para staff.
Context7 consultado: React Router 6.30.3, layouts/Outlet/Navigate; no router7 ni RSC.

### 3. Agenda y gestión

Vista de listas por sillón, no drag-and-drop: en móvil una columna, escritorio
grupos legibles con filas de hora/paciente/tratamiento/estado. Filtros fecha/sillón/
estado. Los grupos de GET agenda solo contienen sillones con turnos; vacío no
significa sillón inexistente. Usar catálogo público para nombres activos cuando
sea suficiente; odontólogo no llama `/api/config`, reservado a secretaria.

Cada turno conserva inicio/fin servidor. Zona AR explícita; no sumar dos días UTC
en cliente ni filtrar silenciosamente para fingir día correcto. G-fecha impide
aceptación hasta contrato compartido corregido. Reprogramar presenta huecos de
tratamiento vigente y nueva selección explícita; backend decide fin y conflicto.

Acciones sin optimismo en escrituras: confirmar/cancelar/reprogramar/marcar
asistencia usan PATCH existente. Confirmar cambio con respuesta válida, reconsultar
vista afectada. 422 puede ser transición o ventana: no rotular todo como «2h».
409 ofrece alternativas, no un sobreturno automático. Marcar un sobreturno
existente exige secretaria+motivo; no crear solapamientos ni modificar EXCLUDE.

G-acciones debe resolverse antes de UI funcional de ventana: no hardcodear 120
como fuente de verdad ni consultar /mis-reservas como secretaria. Se conserva el
scope de UI; contrato adicional backend se aprueba antes del slice correspondiente.

### 4. Configuración

Tres secciones: sillones, tratamientos y bloqueos. GET Page, activo/inactivo
explícito (no asumir activo=false significa «todos»), navegación de páginas sin
descargar todo. Formulario por recurso con labels, errores 422 asociados y
confirmación de desactivación. Preferir PATCH `{activo:false}` y reactivación
`{activo:true}`; evita ampliar cliente con DELETE solo para una operación ya
soportada. Nunca DELETE físico ni borrado de turnos.

PATCH solo campos modificados; null explícito para quitar precio o hacer bloqueo
general. Input decimal se convierte por texto a centavos enteros sin operaciones
en float; límites INTEGER, duración positiva. Fechas de bloqueo locales AR se
convierten explícitamente a timestamps aware, no zona del equipo del usuario.
TURNOS_SOLAPADOS confirma guardado y muestra advertencia/cantidad, no rollback.
Edición de política de seña permanece condicionada por G-sena-config, sin activar
tratamientos con montos sugeridos. Consultorio_id solo de contexto autorizado;
primer alta sin contexto se explica y queda pendiente G-contexto, sin UUID manual.

### 5. Cobros locales, sin checkout

/cobros abre un turno elegido desde agenda; al entrar directamente pide seleccionar
uno de datos autorizados. Precio nullable no se infiere de catálogo público.
No usar query string para paciente/nombre/importes; turno_id se valida y no sustituye
autorización. Lectura de totales autoritativos es dependencia G-cobros; no prometer
que el GET actual ya los entrega ni reconstruir movimientos ignorando estados.

Monto es dinero nuevo: precio ficticio 10000, seña3000 y efectivo7000, no13000.
Campo decimal por texto, validación de centavos estrictos. Clave en memoria estable
por acción/payload, huella al cambiar payload; override motivo cambia payload y
clave. MONTO_DIFIERE abre confirmación con esperado/recibido; no auto-override.
No reenviar una escritura tras 401 o timeout; consulta por identidad verificable
de operación y asistencia humana si backend no puede resolver. Recarga no prueba
que no hubo ingreso, clave de frontend no garantiza unicidad en backend.

Lectura de cobros del odontólogo sigue el contrato RBAC backend de KB/C09; no
abrir el formulario de registro a ese rol ni recortar permisos backend por la UI.
El flujo completo de incidencias MP queda fuera de C-11, sin activar devoluciones.

### 6. Historial y privacidad

Mostrar evento real con quién/cuándo/origen solo tras G-auditoria. No hay endpoint
descubierto que pueda elegirse hoy como fuente; este plan no inventa uno. Contrato
read-only y persistencia requieren correctivo aprobado, con RBAC/allowlist/retención.
updated_at de Turno no acredita quién ni secuencia. No fabricar historial local
después de un PATCH ni confundir ConfigAudit con auditoría del turno.

No CacheStorage/localStorage/IndexedDB ni offline queue de agenda/pacientes/cobros.
Purgar formularios privados al cambiar identidad y bloquear respuestas viejas.
SW distingue navegación HTML de GET JSON `/agenda` y `/cobros` por origen/modo;
`/config` HTML no es `/api/config`. No cachear estas APIs por agregar nuevas rutas.

### 7. Validación y TDD

Baseline en entorno aislado autorizado; fixtures backend hacen TRUNCATE: comprobar
instancia nueva descartable, no solo nombre turnos_test. Por comportamiento: RED
observable en seam HTTP/DOM, mínimo GREEN, >=2 casos independientes feliz/error o
borde, refactor y regresión. Mocks solo HTTP frontera, no evidencia de invariantes
Postgres, idempotencia concurrente, cookies ni CORS. No ejecutar pagos externos.

E2E integrado con UI real y fixtures ficticios: secretaria/odontólogo/paciente,
direct links, 401/403, medianoche AR, cambio de cuenta, 409/422, bloqueo warning,
offline, cobro incremental/replay tras G-cobros. `page.request` solo acredita HTTP,
no completa un recorrido de navegador. Runner actual incluye tests real-backend
con escrituras: no ejecutarlo contra el localhost existente por rutina.

## UI Mockups

- Design system revision: 1 (approved 2026-11-10, by user).
- Mockup revision: 1.
- Decision: yes (2026-11-10, elección explícita del usuario).
- Mockups: [mockups/README.md](mockups/README.md), [catálogo HTML](mockups/catalogo.html).
- Approval: approved (2026-11-10, by user; «continúa» tras presentación de mockups revisión1).
- Preview: rendered (2026-11-10, `mockups/previews/<scene>-390.png` y `<scene>-1440.png`; 47 estados, 94 capturas).
- Visual verify: differences (2026-11-10, parcial: tratamientos lista/alta/edición/422 y sillones lista/edición/422/baja/reactivación a390×844 y1440×900, teclado sillones360 en `mockups/verify/`; diferencias y pantallas no inspeccionadas en `verification.md`). No es aceptación de C11 ni de todos los estados.

Brief: personal de consultorio chico; tareas repetidas de consulta y gestión.
Conservar paleta slate/celeste, system-ui y controles 46px de la UI existente.
Referencias: `design-system/README.md`, `tokens.css`, `brand.js`, assets locales.
No branding comercial inventado; nombre/logo (TBD) visibles en previews.

Base revisión 1 aprobada explícitamente por el usuario el 2026-11-10: «si, adelante».
Esto autoriza preparar mockups, no aprueba por anticipado sus pantallas ni apply.
Mockups revisión 1 aprobados y apply por etapas autorizado el 2026-11-10. Seams
DOM accesible, HTTP simulado solo en frontera y navegador confirmados con la
respuesta «Confirmar estos puntos». No se autorizan correctivos backend implícitos.
Mockups creados con HTML/CSS/JS local por pantalla/estado: agenda por rol
(carga/vacío/error/poblada/sobreturno), detalle/historial disponible e indisponible,
confirmar/cancelar/reprogramar/conflicto/ventana/asistencia, config tres recursos
(lista/form/validación/warnings/baja/reactivación/contexto faltante) y cobros
(gate bloqueado, resumen, override, éxito/replay y resultado incierto).
Capturas 390×844 y 1440×900 para cada estado y chequeo 360px realizados. Sin
overflow horizontal, errores de JavaScript, recursos externos o respuestas >=400
en la matriz. Ocho hojas de inspección y capturas originales enlazadas desde
mockups/README.md. Mostrar al usuario y esperar aprobación antes de apply.
Importan tokens y brand compartidos sin modificar la revisión1 aprobada. Vistas
futuras de historial/cobros están marcadas ficticias y no satisfacen gates backend.

## Risks / Trade-offs

- Backend archivado incompleto → gates específicos, nunca mocks como aceptación.
- Scope conserva cobros/auditoría aunque bloqueados → entrega incremental no
  habilita archive parcial; pedir decisión explícita si se quiere dividir alcance.
- Nombre y logo pendientes → rutas estables y placeholders claramente señalados.
- Rollout mezclado C10/C11 → una sesión y regresión paciente obligatoria.
- Día/calendario incorrecto → no workaround visual; corregir contrato antes de aceptar.

## Migration Plan

1. Aprobar base visual, generar/aprobar mockups y revisar contratos/seams.
2. Solicitud separada de apply; baseline seguro; navegación y configuración no
   bloqueada primero, agenda/actions con gates correspondientes, cobros al final.
3. Gates backend se satisfacen por cambios correctivos aprobados separadamente,
   sin ampliar implementación frontend por implicación. Adjuntar evidencia aquí.
4. Regresión + validación OpenSpec + verificación visual de todos los estados.
   Mantener C11 abierto hasta satisfacer todo el alcance y obtener revisión humana.
5. Rollback de UI restaura navegación sin borrar registros ni revertir pagos;
   no downgrade DB ni cambio de reglas backend. No build de imagen final ni deploy.
