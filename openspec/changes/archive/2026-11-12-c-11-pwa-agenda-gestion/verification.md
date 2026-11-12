# C-11 — Evidencia de implementación incremental

## Autorización y seams

2026-11-10 (fecha local): usuario responde «continúa» a la presentación de mockups
revisión1 y pregunta explícita de aprobación para implementar por etapas. Base
visual revisión1 ya aprobada. Se conservan los PNG originales de revisión y se
registran aprobaciones en design.md y mockups/README.md, sin alterar apariencia.

Seams confirmados antes de escribir tests: usuario eligió «Confirmar estos puntos»
para DOM/navegación accesible, HTTP simulado en frontera de API y navegador para
responsive/privacidad. Backend integrado solo en instancia nueva descartable y
con autorización; no DB existente, migraciones, pagos externos ni auth backend.

Threat model del slice: sesión→rutas privadas→API administrativa; proteger rol,
pacientes y datos de catálogo. Riesgos: fetch antes de verificar identidad, returnTo
externo, respuestas de otra cuenta, reenvío de escritura incierta y falsa aceptación
de JSON. Reutilizar Session/locks/generaciones; React escapa valores; validar DTO
unknown; nunca storage, logs privados ni mutaciones monetarias en este slice.

## Baseline y entorno

Primer intento desde `frontend/`: npm test/lint no encontraron vitest/oxlint;
`npx.cmd --no-install tsc -b` canceló por TypeScript local ausente. Ningún test se
ejecutó: preparación de entorno, no RED ni defecto de comportamiento.

Manifiesto/lockfile v3/CI confirman npm; npm local11.17.0 coincide con packageManager.
`.npmrc` ya declara ignore-scripts=true. `npm.cmd ci --ignore-scripts` exit0:
453 paquetes; lockfile y manifiesto sin modificar. Auditoría automática reporta
10 hallazgos preexistentes (2 bajos/8 moderados), no se aplicó fix ni upgrade.
Esta sesión no es aceptación de release; ver triage histórico C-10 antes del piloto.

Baseline posterior a instalación, 21:06 local, desde frontend/:

| Comando | Exit | Resultado |
|---|---|---|
| npm.cmd test -- --reporter=dot | 0 | 118/118 pruebas en 5 archivos |
| npm.cmd run lint | 0 | Sin findings |
| npx.cmd --no-install tsc -b | 0 | Typecheck correcto |

No se ejecuta backend ni E2E contra localhost existente: el slice inicial es
frontend y no hay instancia nueva descartable verificada. No se atribuye baseline
backend verde ni se alteran fixtures para evitar sus protecciones.

## Matriz de gates por slice

Referencia de contrato: código observado al iniciar apply sobre main `b1f3929`,
más specs de C04/C06/C07/C09. No hay correctivo backend aprobado/ejecutado aquí.

| Gate | Estado | Evidencia pendiente / slice afectado |
|---|---|---|
| Visual | Satisfecho rev1 | Base y mockups aprobados por usuario; comparar al verificar |
| G-fecha | No satisfecho | Agenda/disponibilidad aún delimitan UTC; falta API/navegador real en medianoche AR y cache/bloqueos |
| G-acciones | No satisfecho | Agenda no proyecta permisos/ventana staff; no hardcodear política crítica |
| G-auditoria | No satisfecho | Falta persistencia/lectura actor-fecha-origen; no fabricar historial |
| G-contexto | No satisfecho | Falta fuente autorizada de consultorio para primer sillón; no UUID manual |
| G-cobros | No satisfecho | Lectura/totales, clave requerida, replay, cierre concurrente y reconciliación de resultado |
| G-sena-config | No satisfecho | Falta aceptación de política combinada/auditoría/modos C09 |

Pueden comenzar navegación y catálogo no temporal (listas y edición de recursos
existentes, duración/precio). No marcar completos alta de primer sillón, política
de seña, agenda día AR, historial ni cobros por mostrar un fallback. Mantener
pendientes los criterios de aceptación integrados.

## TDD

Registrar cada slice RED/GREEN ejecutado, triangulación y límites antes de marcar
su task completa. No se atribuyen tests futuros ni mocks como E2E integrado.

### Slice 2.1 — Guard y navegación

Comando seam DOM+HTTP: `npm.cmd test -- src/Staff.test.tsx --reporter=dot`.

- RED21:08:14 exit1: tres rutas staff anónimas mostraban404 en vez de login.
- GREEN21:08:38 exit0: 3/3 después de RoleGuard y rutas, sin fetch privado.
- RED21:09:27 exit1: 3 casos de navegación por rol sin links Agenda/Configuración;
  denegación de paciente/odontólogo/rol desconocido y loading/503 ya pasaban.
- GREEN21:09:56 exit0: 14/14. Dos errores del harness del intento21:09:09
  (promise release aún no instalada y query alert no única) corregidos antes del
  RED contado; no son defectos de producto ni ciclos de comportamiento.
- Triangulación: anónimo401 en3 rutas, seis combinaciones prohibidas, tres
  permitidas, restauración pendiente y503 sin consultas administrativas.
- Regresión C10 DOM: `npm.cmd test -- src/App.test.tsx --reporter=dot`, exit0,
  68/68. El caso404 `/agenda` se actualizó a `/agenda/inexistente` porque C11
  introduce esa ruta intencionalmente; no se eliminó la comprobación404.
- Documentación aterrizada en frontend/README.md. No se modificó Session ni auth
  backend, no se alteraron mockups aprobados. Áreas todavía parciales no se dan
  por completas por el guard.

### Slice 2.2 — Retorno de login por rol

- RED21:11:22, comando Staff.test.tsx anterior, exit1: tres retornos internos de
  personal acababan en /mis-reservas y área paciente denegada.
- GREEN21:11:53 exit0:17/17 tras allowlist por rol y lectura de identidad confirmada
  luego de login. No cambios en locks/tokens/backend.
- Triangulación suplementaria (no se reclama RED nuevo): siete retornos externos,
  //, backslash, control y roles incompatibles; todos sin POST de negocio.
- Regresión21:12:21: `npm.cmd test -- src/Staff.test.tsx src/App.test.tsx
  --reporter=dot` exit0,92/92 (24 staff+68 App); tsc -b exit0. Flujo paciente
  conserva selección y nunca reenvía reserva tras login.
- Documentación de rutas/retorno en frontend/README.md; validación visual todavía
  pendiente junto a pantallas operativas, no se afirma coincidencia de todo C11.

### Slice 3.1 — Listas administrativas

- RED21:14:27 exit1: tratamiento real no se renderizaba; GREEN21:15:23 exit0,
  caso HTTP/DOM con Bearer, page1/activo=true y centavos12345→ARS123,45.
- RED21:16:05 exit1: faltaban tabs Sillones/Bloqueos y filtro/paginación;
  GREEN21:17:15 exit0:4/4 casos del slice con tres recursos y páginas inactivas.
- Triangulación suplementaria: DTO duración0/preciofloat/página inválida/filtro
  incorrecto, vacío frente a503+retry y respuesta vieja ignorando abort.
- Regresión21:19:07: Staff38/38 exit0; lint y tsc exit0. Se corrigieron tres usos
  de opción exact no admitida por ByRoleOptions y un warning de regex antes de
  esta regresión; no se cuentan como RED funcional ni se deshabilitó lint.
- Contratos/estados y límites documentados en frontend/README.md. No se consulta
  catálogo público ni se infiere sede/precio/paciente de datos inventados.

### Slice 2.3 — Identidad reutiliza el circuito C10

Tres pruebas HTTP/DOM adicionales verdes sin alterar Session: dos cuentas nuevas
(paciente/secretaria), salida durante lectura demorada, respuesta anterior tras
ingresar y dos GET401 que comparten un solo refresh de recuperación (dos refresh
totales contando restauración inicial). Storage permanece vacío. Aborto y cierre
del componente impiden publicar datos viejos. No se reclama RED nuevo para un
comportamiento de Session ya implementado; las rutas/layout nuevos se probaron
con RED/GREEN2.1 y se preserva el control existente. Cookies/multi-tab quedan para
verificación integrada; no son demostrados por simular Web Locks en jsdom.

### Slice 3.2 — Formularios de tratamientos

Fecha local2026-11-10. Comandos desde frontend/; cada filtro usa
`npm.cmd test -- src/Staff.test.tsx --reporter=dot -t "<filtro>"`.

| Filtro | RED exit1 y causa | GREEN exit0 |
|---|---|---|
| edita precio | 21:22:31, dos casos sin botón Editar | 21:23:50,2/2 |
| edita duración | 21:24:10, no había campo de duración | 21:24:30,5/5 incluyendo precios |
| asocia 422 | 21:24:52, sin asociación por campo y bloqueo incorrecto del rechazo | 21:25:34,2/2 |
| navegar no libera | 21:26:13, navegar permitía repetir pendiente/5xx | 21:27:22,9/9 con regresión de edición |
| edita nombre | 21:30:15, no había campo Nombre | 21:30:37,4/4 incluyendo precios |
| crea tratamiento | 21:31:21, no había alta | 21:32:03,1/1 |

Triangulación adicional sin reclamar RED nuevo: precios123,46→12346,
0,29→29,21474836,47→2147483647; null frente a0; duración1 y máximo INTEGER;
precio máximo+1centavo, tres decimales/miles/negativo; duración0, fracción y overflow;
sin cambios no envía PATCH; nombre recortado; alta sin precio y con decimal;
JSON/id/importe inesperados y fallo de red nunca anuncian éxito ni habilitan retry.
El primer typecheck adicional detectó un índice any inferido por Array.isArray
en loc del 422: se anotó unknown y se estrechó a nombres permitidos, sin any ni
deshabilitar TypeScript. No se cuenta como RED funcional.

El guard vive en Layout keyed por identidad (no en ConfigPage), se bloquea antes
del envío y conserva pending/uncertain entre rutas/filtros/reconexión. Es solo
memoria de una pestaña: no sobrevive reload/logout ni reemplaza idempotencia o
conciliación backend. Se explica este límite en frontend/README.md; no se marca
G-cobros ni G-sena-config satisfecho. No se modifica backend, sesión ni lockfiles.

Regresión21:32:16 previa al ajuste de layout:181/181 en6 archivos, lint y
`npm.cmd run build` exit0 (incluye tsc -b y generación PWA). Regresión posterior
al layout y al segundo caso de alta: ver registro final abajo.

## Inspección visual incremental (no aceptación completa)

Base/mocks revisión1, modo system-and-mockups; aprobación existente conservada.
Estilos staff acotados a clases nuevas usando los valores de tokens rev1. Se
preserva C10 y no se importa CSS fuera del contexto frontend del Dockerfile.

Servidor propio Vite en127.0.0.1:5191, strictPort; HTTP externo interceptado en
Playwright con datos ficticios y respuestas sintéticas. Ninguna llamada alcanzó
backend existente. Inspeccionadas8 capturas en `mockups/verify/`:

- Lista tratamientos, edición, alta y error422, cada uno390×844 y1440×900.
- DOM y capturas sin overflow horizontal; error422 asociado al campo y sin texto
  interno; localStorage/sessionStorage vacíos. Lista a la izquierda/form a la
  derecha en desktop y apilados en móvil.
- Red revisada: GET inicial abortado por cleanup/StrictMode, GET200 posterior,
  PATCH422 deliberado en los dos viewports; consola registra ese422 esperado.
  Tras detener el servidor, Vite intentó reconectar HMR y produjo errores WS
  CONNECTION_REFUSED: son de la limpieza, no una captura operativa con backend.
- Servidor propio detenido tras comprobar commandline/PID2952; navegador cerrado.
  El comando de dev termina exit1 por esa parada intencional, no por fallo de build.

Comparación abierta con `mockups/previews/config-tratamientos-390.png` y
`config-tratamiento-formulario-1440.png`. **Visual verify: differences**:

| Prioridad | Pantalla/viewport | Mockup esperado | Observado / reproducción |
|---|---|---|---|
| major | Configuración/alta/edición, ambos | Agregar tratamiento junto al encabezado/antes de tabs | Debajo de filtros; abrir /config y comparar capturas verify |
| major | Edición, ambos | Checkbox Sin precio y política de seña deshabilitada visible | Null mediante texto vacío y aviso de política bloqueada; falta paridad de esos controles auxiliares. Abrir Editar Control |
| minor | Shell, ambos | Navegación compacta y role en línea | Cerrar sesión adicional conserva salida segura C10; en390 el rol ocupa otra línea |
| minor | Catálogo, ambos | Editar estilo enlace y badge verde | Botón con borde/badge neutro; no depende de color para estado |

Los textos de maquetación/fixtures y el banner de maqueta no se copian al runtime.
No se alteraron las maquetas aprobadas ni se solicita aprobar estas diferencias
como una revisión nueva. Corregirlas y recapturar durante la aceptación visual.
No se marca completa tarea6.3 ni se afirma coincidencia total. No inspeccionados
en browser aquí: sillones, bloqueos, todos los estados de auth, cobros/agenda,
éxito y error de transporte del formulario (estos dos últimos solo DOM/HTTP).
Pendientes también la baja/reactivación de tratamientos y demás criterios de la
spec de catálogo; alta/edición no equivalen a configuración completa ni release.

## Registro final del incremento 3.2

2026-11-10,21:39 local, desde frontend/:

| Comando | Exit | Evidencia |
|---|---|---|
| npm.cmd test -- --reporter=dot | 0 | 182/182 en6 archivos:64 Staff +118 baseline/C10 |
| npm.cmd run lint | 0 | Sin findings |
| npm.cmd run build | 0 | tsc -b y Vite6.4.6, PWA genera12 entradas; solo assets, no imagen Docker |
| openspec.cmd validate c-11-pwa-agenda-gestion --strict (desde raíz) | 0 | Change válido |
| git diff --check (desde raíz) | 0 | Sin errores de whitespace; avisos LF→CRLF según entorno Git |

Task3.2 completa en su seam funcional (alta/edición y validaciones indicadas).
Task6.3 permanece pendiente por diferencias visuales y cobertura de pantallas.
No se ejecuta backend/E2E integrado ni pruebas contra DB existente o pagos.
No commit/push/archive. Próxima task independiente:3.3, sillones; mantener
G-contexto para alta y los otros cinco gates pendientes.
`openspec.cmd instructions apply --change c-11-pwa-agenda-gestion --json` confirma
10/30 tareas completas, próxima3.3,20 pendientes. Cambios continúan sin commit.

## Incremento 3.3 — Sillones existentes

2026-11-10 local. Se preservan los seams y aprobaciones ya confirmados. Threat
boundary: formulario/lista administrativa → PATCH con Bearer de sesión existente;
validar entrada y DTO; no permitir cambiar sede, borrar históricos ni enviar
acciones de agenda. Reutilizar guard en Layout y descartar callback tras unmount.
Lectura estática `backend/app/api/config.py` y `schemas/config.py`: PATCH de
sillones acepta nombre/activo y responde200 SillonOut; no se modifica backend.

Cada ciclo desde frontend usa
`npm.cmd test -- src/Staff.test.tsx --reporter=dot -t "<filtro>"`:

| Filtro | RED exit1 | GREEN exit0 |
|---|---|---|
| edita el nombre de un sillón |21:49:49, faltaba Editar|21:50:38,1/1|
| baja lógica de sillón |21:51:21, faltaba Desactivar|21:52:04,3/3 con edición|
| reactiva sillón inactivo |21:52:41, faltaba Reactivar|21:53:16,5/5 con baja/edición|
| sillón rechazado |21:53:50,404 tratado incierto y422sin asociación|21:54:21,7/7 del slice|

Triangulación sin nuevo RED: nombre blanco/sin cambios no envía;403/404/422 de
baja no anuncia éxito ni DELETE/refresh extra; respuesta con sede distinta o
actividad incoherente y transporte perdido conservan incertidumbre al navegar.
Regresión parcial21:55:34 `npm.cmd test -- src/Staff.test.tsx --reporter=dot`:
79/79exit0; lint ytsc -b exit0. Cada PATCH solo modifica nombre o actividad, nunca
los dos al confirmar baja con texto no guardado. Pruebas ficticias verifican los
requests, no permanencia real de filas/agenda en PostgreSQL.

### Verificación browser del incremento 3.3

Playwright con todas las solicitudes externas interceptadas y estado ficticio
de un sillón; sin API/DB existente. Vite propio127.0.0.1:5191 strictPort. Abiertas
e inspeccionadas11 capturas en mockups/verify: lista, edición,422,confirmación
de baja y reactivación a390×844/1440×900, más confirmación con teclado360×844.
No overflow horizontal en estos tamaños. Se recorrieron baja→lista de inactivos
→reactivación contra fixture mutable; no equivale a persistencia backend real.

Foco con Tab: Nombre → Guardar cambios → Volver a la lista → Desactivar sillón.
Enter abre confirmación con foco seguro en Conservar activo; otro Enter cancela
sin PATCH. Confirmar explícitamente envía un PATCH por acción. Consola durante
capturas: dos422 deliberados; errores JS ninguno. Los seis requestfailed fueron
GET abortados por cleanup al cambiar recurso/filtro/StrictMode; las lecturas
vigentes respondieron200. Storage vacío en ambos viewports. Sin DELETE, escrituras
de turnos, tokens persistidos ni solicitudes a servicios reales.

Primer intento browser: locator getByLabel('Mostrar',exact:true) agotó espera
tras baja; snapshot mostraba combobox accesible Mostrar y lista correcta. Se usó
getByRole('combobox',{name:'Mostrar',exact:true}) y el recorrido pasó completo.
Es corrección del harness, no un RED de producto ni una prueba backend omitida.

Comparado con mockups/previews/config-desactivar-1440.png y patrón de formulario
aprobado: split/controles táctiles/texto de históricos y confirmación conservados.
**Visual verify: differences**, no se actualiza aprobación de maquetas:

| Prioridad | Pantalla/viewport | Esperado | Observado / reproducción |
|---|---|---|---|
| minor | Baja,390/1440 | Aviso ámbar con título y separación de encabezado | Notice rojo/rosa y espaciado de formulario; /config→Sillones→Editar→Desactivar |
| minor | Catálogo/shell,390/1440 | Badge verde, Editar enlace, nav compacta | Badge neutro/botón y Cerrar sesión añadido; mismo pendiente previo de6.3 |
| dependencia | Alta de sillón,ambos | Agregar abre explicación de contexto faltante | No implementada aún; tarea3.4 y G-contexto siguen pendientes, no se fabrica sede |

No se copian rótulos/fixtures del mockup como datos del producto. Pantallas todavía
no inspeccionadas aquí: agenda/cobros/bloqueos y resto de matriz auth/privacidad/SW;
errores404/403/transporte de sillón solo seam DOM/HTTP. No se declara6.3 completa.
Browser cerrado antes de detener el servidor propioPID15316 validando commandline.
El dev server finaliza exit1 por parada intencional, no por fallo operativo/build.

### Regresión y siguiente gate

22:00:18 local, desde frontend/:

| Comando | Exit | Resultado |
|---|---|---|
| npm.cmd test -- --reporter=dot |0|197/197,6 archivos (79Staff+118previas/C10)|
| npm.cmd run lint |0|Sin findings|
| npm.cmd run build |0|tsc -b,Vite6.4.6,PWA12 entradas; assets solamente|
| git diff --check (raíz) |0|Solo avisos LF→CRLF del entorno|

Task3.3 se completa en los seams autorizados. Próxima3.4 requiereG-contexto:
fuente autorizada de consultorio para alta; el backend observado aún no la expone.
No se deduce desde otro sillón ni se modifica backend por este apply.3.4 queda
pendiente hasta correctivo aprobado y evidencia. C11 sigue abierto, sin archivo,
commit,push,imágenes Docker ni pagos externos. Continúan los seis gates backend.
`openspec.cmd validate c-11-pwa-agenda-gestion --strict` exit0; apply refrescado
confirma11/30 completas y19 pendientes. Se retiraron solo los tres logs/snapshot
temporales generados por Playwright en esta conversación; se conservan PNG y
evidencia resumida, sin añadir ruido de HMR al repositorio.

## Inicio parcial 3.5 — Lectura de intervalos de bloqueos

2026-11-11: la lista de bloqueos mostraba solo «horario Argentina» sin horas.
Se muestran inicio y fin recibidos del servidor mediante `dateTime` existente,
explícitamente `America/Argentina/Buenos_Aires`; no se filtra ni corrige el día
de agenda en cliente. RED `npm.cmd test -- src/Staff.test.tsx --reporter=dot -t
"muestra el intervalo del bloqueo"` exit1: faltaba 13:00; GREEN exit0:16:00Z
→13:00 y17:00Z→14:00. Triangulación: bloqueo que cruza medianoche muestra
12 nov23:30 y13 nov00:30. Primer intento de ese test supuso formato sin «de»;
corregida expectativa de locale, no se cuenta como RED de producto.

Regresión `npm.cmd test -- --reporter=dot` exit0:199/199; lint y tsc -b exit0.
Es un avance parcial de lectura; no implementa formulario ni modifica el gate
temporal. Task3.5 sigue pendiente y no se reclama verificación visual browser.

## Sesión de apply — tareas procedentes (sin gate bloqueante)

Fecha: 2026-11-11. Alcance: solo frontend (`frontend/src/features/agenda/`), sin modificar backend, migraciones, pagos ni auth. Se instaló `node_modules` desde `package-lock.json` (`npm.cmd ci --ignore-scripts`, 453 paquetes, lockfile sin modificar) para ejecutar suites.

### Tarea 4.3 — Señales de sobreturnos y conflictos [x]
Módulos: `features/agenda/SobreturnoSignal.tsx`, `features/agenda/Conflict409.tsx`.
- SobreturnoSignal muestra "Sobreturno" + motivo como TEXTO (independiente del color); no renderiza cuando no es sobreturno.
- Conflict409 explica el conflicto, lista alternativas como botones, no selecciona ninguna automáticamente, sin sobreturno automático ni bypass de EXCLUDE.
- Pruebas (Agenda.test.tsx): 5 casos, RED (módulo inexistente) → GREEN → triangulación (con/sin sobreturno, con/sin alternativas, elección notifica `onSelect`).
- Comando: `npm.cmd test -- src/features/agenda/Agenda.test.tsx --reporter=dot`, exit0, 5/5.

### Tarea 4.6 — Asistencia y sobreturno explícito [x]
Módulo: `features/agenda/TurnoActions.tsx`.
- Marcar asistido/ausente: secretaria y odontólogo; motivo obligatorio; PATCH `/turnos/{id}/marcar-asistencia {estado, motivo, origen: 'mostrador'}`; 403/422/404 con mensaje autoritativo, sin éxito falso.
- Marcar sobreturno existente: solo secretaria + motivo; odontólogo/paciente no ven la acción.
- Pruebas: 9 casos (roles, motivo obligatorio, 403/422/404, éxito, sobreturno solo secretaria).
- RED/GREEN confirmado; refactor (canal `escribir` compartido) mantiene 14/14.

### Tarea 4.8 — Recuperación de escrituras inciertas [x]
Integrado en TurnoActions: estado `incierto` bloquea repetición tras transporte perdido/respuesta ambigua; no reenvía POST/PATCH solo; se desbloquea únicamente con consulta explícita ("Consultar el turno y limpiar resultado incierto"). No se crean ausencias automáticas ni turnos solapados.
- Pruebas: 2 casos (transporte caída bloquea repetición y requiere recuperación explícita; navegación no reenvía ni desbloquea).

### Tarea 6.1 — PWA SW/privacidad (parcial; matriz de browser pendiente)
- Verificado por pruebas: las acciones de agenda no escriben turnos, cobros ni tokens en `localStorage`/`sessionStorage` (longitud 0 tras uso).
- Revisión estática de `vite.config.ts` (workbox): `runtimeCaching: []` (ninguna API cached) y `navigateFallbackAllowlist` excluye `/agenda`, `/config`, `/cobros` (solo rutas públicas/paciente), por lo que el SW no sirve fallback privado ni cachea APIs de gestión.
- Pendiente: recorrer matriz de browser (offline/reconexión, dos cuentas, capturas 390×844/1440×900) con Playwright.

### Tarea 6.3 — Comparar con mockups aprobados (parcial; visual verify real pendiente)
- Los componentes nuevos usan los tokens de design-system rev1 (`success`, `notice`, `actions`, `muted`) y las clases de `index.css` sección C11, sin fuentes remotas ni activos externos.
- Comparación de código contra mockups rev1 (agenda/detalle, cobros, config) realizada; no se detectaron diferencias blocker a nivel de código.
- Pendiente: capturas browser 390×844/1440×900 y 360px/teclado/foco/consola/red para cada pantalla/estado, y registro de diferencias blocker/major/minor en design.md. Las diferencias previas de rev1 (config: posición "Agregar tratamiento", checkbox Sin precio/política de seña deshabilitada, shell nav) permanecen abiertas.

### Regresión y estado de gates
| Comando | Exit | Resultado |
|---|---|---|
| `npm.cmd test -- --reporter=dot` | 0 | 216/216 en 7 archivos (199 baseline C-10 + 17 nuevos agenda) |
| `npm.cmd run lint` | 0 | Sin findings |
| `npx.cmd --no-install tsc -b` | 0 | Typecheck correcto |
| `openspec validate c-11-pwa-agenda-gestion --strict` | — | pendiente al cerrar la sesión |

Gates backend: los seis siguen NO satisfechos (G-fecha, G-acciones, G-auditoria, G-contexto, G-cobros, G-sena-config); sin correctivo aprobado en esta sesión. No se marca aceptación de agenda diaria, reprogramar, acciones de ventana, historial, cobros ni alta integrada de sillón.

### Tareas documentadas como BLOQUEADAS (no forzadas)
- 3.4 Alta primer sillón → G-contexto no satisfecho: no hay fuente autorizada de `consultorio_id`; no se hardcodea UUID ni se elige un registro arbitrario.
- 3.5 Bloqueos (aceptación temporal) → G-fecha no satisfecho: día AR/disponibilidad aún delimitan UTC; falta API/navegador real en medianoche AR.
- 3.6 Política de seña → G-sena-config no satisfecho: falta aceptación de política combinada/auditoría C-09.
- 4.1 DTO/vista GET /agenda → G-fecha no satisfecho (aceptación de agenda diaria).
- 4.2 Satisfacer G-fecha → falta correctivo backend aprobado (medianoche AR, franjas 21:00–24:00, bloqueos/cache).
- 4.4 Confirmar/cancelar → G-acciones no satisfecho (proyección/contrato de acciones y ventana para staff).
- 4.5 Reprogramación → G-fecha + G-acciones no satisfechos.
- 4.7 Historial → G-auditoria no satisfecho (falta persistencia/lectura actor-fecha-origen; no se fabrica historial).
- 5.1 a 5.4 Escrituras de cobros → G-cobros no satisfecho (totales, clave requerida, replay, cierre concurrente, resolución de timeout).
- 6.2 E2E integrado → todos los gates no satisfechos.

No se archiva C-11 ni se declara completo mientras queden tareas o criterios pendientes. No hay commit/push/imágenes Docker/pagos externos en esta sesión.

## Revisión del clon e implementación — 2026-11-12

- El código de agenda citado en las notas previas no estaba en ninguna referencia local. Se implementó y conectó la vista privada, con filtros y límites de día argentino en el servidor. Las operaciones de agenda usan permisos proyectados por la API y la ventana configurada.
- La migración 005 incorpora eventos de gestión. La asistencia admite el motivo y origen del formulario, conservando el contrato anterior de estado para los clientes existentes. El historial muestra únicamente eventos persistidos desde la migración.
- Configuración incorpora alta de sillón con contexto autorizado, edición conjunta de política e importe de seña y formularios de bloqueos. Se invalidan los resultados de disponibilidad al confirmar los cambios de catálogo y al cancelar, reprogramar o marcar ausencia por la API.
- La pantalla de cobros se abre desde un turno autorizado y conserva la selección en memoria. El servidor exige clave, guarda el resultado, serializa el cierre y expone un resumen y una consulta de conciliación. La PWA usa esta última tras un resultado incierto.
- Pruebas HTTP con PostgreSQL descartable y Redis simulado, y pruebas de interfaz con API interceptada. Continúan pendientes la matriz visual completa, Redis real, E2E de navegador integrado y el sandbox de Mercado Pago de C-10. C-11 sigue abierto.

### Resultado de la regresión

- Backend completo: 324 pruebas aprobadas con PostgreSQL 18 descartable y Redis simulado por TCP. Alembic aplicó la migración 005 en ese clúster, que se detuvo al finalizar. Ruff y comprobación de formato aprobados.
- Frontend: 205 pruebas aprobadas, lint sin hallazgos y build de la PWA correcto.
- Chrome, 360/390/1440 px con API interceptada: recorrido de agenda a cobros y configuración, activación por teclado, pérdida y recuperación de conexión, cambio de secretaria a odontólogo, ausencia de overflow horizontal, storage vacío y sin excepciones JavaScript. Queda pendiente la comparación visual de todos los estados y el E2E con servicios reales.

## Verificación local con Docker Compose (2026-11-12)

Entorno `odonto-c12` con PostgreSQL y Redis reales y migración 005. Se usaron tres cuentas ficticias y turnos de Control en dos sillones. Pruebas exploratorias en Chrome sobre la PWA publicada por Compose, sin interceptar la API, y comprobaciones HTTP contra esa misma instancia.

| Superficie | Resultado observado |
| --- | --- |
| Agenda | Chrome mostró turnos de los dos sillones a las 22:00 y 22:30 de Argentina. Se comprobó ausencia de desborde horizontal a 390 y 1440 px. |
| Gestión e historial | Secretaría confirmó un turno desde Chrome. Odontología marcó asistencia con motivo desde Chrome. La API devolvió los eventos persistidos con acción, actor, origen mostrador y fecha. |
| Permisos y privacidad | La API rechazó agenda a paciente y cobros a odontología con 403. La PWA ocultó la agenda tras desconectar la red, recuperó los datos al reconectar y denegó la agenda al cambiar a la cuenta de paciente. localStorage y sessionStorage estaban vacíos durante la comprobación. |
| Reprogramación y cancelación | Por HTTP, intentar mover un turno a un hueco ocupado devolvió 409. Moverlo a un hueco libre en el otro sillón y luego cancelarlo devolvió 200. |
| Cobros | La PWA registró una seña ficticia de ARS 100. Por HTTP, el cierre por ARS 2.400 dejó el saldo en cero. Repetir el cierre con la misma clave devolvió 200 y el mismo recibo, con total de ARS 2.500. |
| Configuración | Chrome guardó una política de seña opcional y un bloqueo general a las 23:00 de Argentina. El servidor devolvió la fecha con el instante UTC esperado y sillón nulo. El contexto de consultorio respondió 200 para secretaría y 403 para odontología. |

Sigue pendiente la comparación de todas las pantallas y estados con los mockups aprobados, y la cobertura integral del checklist de navegador, incluido CacheStorage, alta del primer sillón en sede vacía y casos de error de configuración. Los flujos que se probaron por HTTP cuentan como evidencia del contrato del servidor. C-11 queda abierto.

Regresión frontend local: `npm.cmd test`, 205/205. OpenSpec validó C-11 y C-12 en modo estricto. `git diff --check` sin errores. La nueva ejecución de la suite de backend se interrumpió antes de iniciar porque el entorno virtual temporal anterior ya no estaba disponible.

## Comprobaciones adicionales de aceptación

- Chrome sobre la PWA de Compose, con el service worker activo. `CacheStorage` tuvo diez recursos públicos, incluido el manifiesto, antes y después de cerrar sesión. No se encontraron rutas de API privada, datos del paciente de prueba ni tokens. `localStorage` y `sessionStorage` vacíos. La agenda ocultó datos al quedar offline, los recuperó al reconectar y pidió autenticación después de cerrar sesión.
- Alta del primer sillón en una base independiente recién migrada, con una sede activa y cero sillones. Chrome usó la PWA de Compose y redirigió las solicitudes al backend local aislado, sin respuestas simuladas. Contexto 200 con el nombre de la sede, alta 201 con el ID del contexto y primer sillón visible en la lista.
- Comparación visual exploratoria a 390×844 y 1440×900. Se revisaron agenda de secretaría, resumen de cobros, alta de sillón y edición de tratamiento. No se detectó desborde horizontal. Diferencias: la agenda presenta acciones dentro de la lista y no tiene el panel de detalle del mockup. Cobros usa un formulario en columna y no muestra el bloque de movimientos del diseño. Los formularios de configuración conservan panel lateral en escritorio, con botones y encabezados en otra posición. La comparación exhaustiva de estados de 6.3 sigue abierta.

La regresión de backend posterior pasó con 325 pruebas en base separada con PostgreSQL y Redis reales. Después pasaron los cinco casos de contexto, incluido el nuevo error de lectura. También pasaron el lint, TypeScript y el build de frontend.

## Detalle de agenda y movimientos de cobros

- Agenda usa una lista por sillón y un panel de detalle con selección explícita. Los permisos de acción siguen llegando con el turno. Cobros consulta el resumen y el listado filtrado por turno, valida que cada movimiento pertenezca a la selección y mantiene el identificador fuera de la URL de la PWA. El listado tiene Cache-Control: no-store.
- Chrome con la PWA actualizada, backend real y PostgreSQL/Redis de Docker: selección por teclado, detalle, seña y cierre ya persistidos, URL limpia y ausencia de desborde a 360, 390 y 1440 px. Cobros y configuración ocultan sus datos al quedar offline. Cobros los recupera al reconectar. El acceso directo a Cobros muestra la selección vacía.
- `pytest -q tests/test_config.py tests/test_c09_cobros.py tests/test_gestion_turnos.py tests/test_disponibilidad.py`: 155 aprobadas en base separada. Incluye alcance y advertencias de bloqueos, clave de cobro obligatoria, repetición, cierre concurrente y consulta de operación.
- Las pruebas DOM confirman que una diferencia requiere motivo, nueva confirmación y nueva clave. Una respuesta perdida se concilia consultando la operación con la clave original y una sola escritura. Los contratos de rechazo, autorización de diferencia y lectura del recibo se comprobaron también por API contra PostgreSQL.
- Frontend: 206 pruebas aprobadas, lint y build aprobados. Playwright de personal con HTTP interceptado: dos casos aprobados a 360 y 1440 px. Ruff y OpenSpec estricto aprobados.
- Compose dejó de responder tras estas comprobaciones. La repetición separada de política de seña no inició porque PostgreSQL rechazó la conexión. Sigue pendiente el recorrido completo de aceptación de navegador y la comparación de todos los estados con los mockups.

## Verificación con Compose restablecido

- Seña: 11 pruebas de política aprobadas en base separada. En la API publicada se hicieron PATCH obligatoria y opcional con 3005 centavos y deshabilitada con monto nulo. Un PATCH incoherente devolvió 422 y conservó el estado anterior. Se restauró la política ficticia y PostgreSQL confirmó las cuatro entradas de auditoría.
- Fecha argentina: Chrome mostró el turno de las 23:45 solo en el día consultado y el de las 00:15 solo en el siguiente. La regresión de disponibilidad comprueba agenda, bloqueo e invalidación de Redis alrededor de medianoche.
- Gestión: Chrome confirmó y canceló un turno, mostró ambos eventos persistidos y reprogramó otro usando un horario disponible. El servidor calculó la duración de 15 minutos. Las variantes de conflicto y ventana se siguen evaluando para aceptación integral.
- Privacidad: la PWA de Compose ocultó datos de agenda, cobros y configuración al quedar offline. Se verificó recuperación de datos al reconectar, sin escrituras de negocio. CacheStorage solo contenía recursos públicos y Web Storage estaba vacío antes y después del cierre. La sesión de paciente recibió denegación en las tres rutas de personal.

## Regresión funcional y recorrido integrado

- `pytest -q tests/test_gestion_turnos.py` sobre PostgreSQL y Redis reales en base separada: 15 aprobadas. Cancelar y reprogramar desde secretaría devuelven 422 a 119:59 y se permiten a 120:00. Se verificó que el 409 ofrece alternativas y que 409/422 conservan la cita original. El fin nuevo se calcula en servidor.
- `pytest -q tests/test_c09_cobros.py`: 19 aprobadas. Se comprobaron tres medios de pago, cierre de 7000 centavos después de una seña de 3000, replay con la misma clave, 403/422 y saldo cero. La API sigue siendo la fuente del resumen y los movimientos.
- Chrome con preview de producción, API de trabajo actualizada y PostgreSQL/Redis de Compose. Se combinaron recorridos de los tres roles, restauración de cookies por refresh, consulta entre orígenes, agenda en fecha argentina, reprogramación real, conflicto 409 provocado por un segundo cliente, transición 422 con recarga, historial ordenado con actor y origen, y bloqueo guardado con TURNOS_SOLAPADOS sin cancelar la cita. En otro recorrido de Chrome se registró seña y cierre por transferencia. Se repitió la petición de cierre por HTTP con la clave capturada para verificar el mismo recibo y dos movimientos. La repetición por HTTP acredita el contrato de idempotencia.
- `vitest run`: 209 aprobadas. Se agregó cobertura DOM para 422 y actualización de acciones, error de historial sin eventos inventados y resumen nullable/inválido. Pasaron lint, TypeScript, build, Ruff y dos pruebas Playwright de personal con HTTP interceptado.
- Se compararon nueve estados adicionales en 390×844 y 1440×900 y se revisó teclado a 360 px. Diferencias y cobertura de revisión en design.md. La tarea 6.3 sigue abierta.

## Cierre técnico de implementación — 2026-11-12

Esta revisión sustituye el estado visual parcial 12/47 y 29/30 de las entradas anteriores. Las 30 tareas de implementación/verificación están ejecutadas. El archivo formal del change sigue sujeto a revisión humana del resultado, como establece tasks.md; no se inventa esa aceptación.

### Cambios finales

- Reprogramación: selector por sillón, nombres legibles, limpieza de elección al cambiar fecha/sillón y resumen explícito de horario antes de aplicar. El original se conserva hasta confirmación del servidor.
- Cierre de cobro: comprobante de solo lectura con operación, importe nuevo, fecha y medio reales; no ofrece un segundo cierre y aclara la seña ya incluida. Conserva la diferencia respecto del precio de referencia.
- Formularios C-11: validación propia visible y coherente, sin mensajes nativos que oculten la validación de la aplicación. Permisos y datos faltantes se explican sin inventar motivos del backend.

### Verificación final ejecutada

| Control | Resultado |
|---|---|
| Vitest frontend completo, incluido C-10 | 212/212, exit 0 |
| Nuevos casos Staff antes/después del cambio | RED: 3 fallos esperados por selector/recibo ausentes; GREEN: pasan |
| TypeScript tsc -b y Vite build | exit 0 ambos |
| Oxlint src | 0 errores, 0 warnings, exit 0 |
| pytest test_gestion_turnos.py | 15 passed, exit 0 |
| pytest test_c09_cobros.py | 19 passed, exit 0 |
| Playwright staff.spec.ts, 360 y 1440 px | 2 passed, exit 0; HTTP simulado |
| Matriz Chrome/React de 47 estados × 3 anchos | 141/141, exit 0 |
| Capturas de los 47 estados | 94: 390×844 y 1440×900, página completa |
| Auditoría estática UI acotada a C-11 | 0 hallazgos; ui-audit.json |
| OpenSpec validate c-11-pwa-agenda-gestion --strict | válido, exit 0 |
| git diff --check | exit 0 |

Backend ejecutado secuencialmente en turnos_test aislada, PostgreSQL 55432 y Redis 56379/15. Persisten 15 avisos de deprecación redis.close; no son fallos. La matriz visual usa fixtures HTTP explícitos y no acredita cookies, concurrencia ni persistencia. Esos puntos tienen evidencia integrada en las secciones anteriores.

Comprobación adicional con Chrome y API real en 8002 (PostgreSQL/Redis del entorno ficticio): login de secretaria, consulta de agenda del 18/11, apertura de reprogramación y consulta de disponibilidad, selector visible, consulta del cierre existente y comprobante visible en 390 y 1440 px. Sin mutaciones monetarias/de turnos, sin desbordes y sin errores JavaScript. No se afirma haber elegido un nuevo horario en este recorrido: esa selección está cubierta por DOM y matriz controlada.

### Visual verify final

Se inspeccionaron las comparaciones de los 47 estados contra revisión 1, móvil y escritorio. Sin pantallas pendientes de comparación. Se verificaron 360 px, selección por teclado y foco visible; la matriz registra errores HTTP esperados en escenarios de error y rechaza rutas/errores de consola inesperados. No es una certificación exhaustiva WCAG.

- Blocker: ninguno detectado.
- Major corregidos: faltaban filtro/confirmación explícita de nuevo sillón y comprobante persistente del cierre.
- Minor documentados: listas ficticias de distinta longitud; formularios solo abiertos al solicitarlos; carga textual sin skeleton; mensajes usan Notice compartido (incluido fondo rosado para éxito); orden/copy de botones distinto; sin repetir ficha completa del paciente en cobros; motivo auditado no repetido en recibo; ausencia de checkbox de precio sustituida por campo vacío explicado. Son diferencias visibles, no equivalencia pixel a pixel.
- Gates históricos: agenda-fecha-bloqueada y config-sena-bloqueada muestran su función habilitada tras verificación del contrato; cobros-bloqueados prueba rechazo seguro de resumen inválido. No se reinstala un bloqueo artificial para copiar el mockup.

Evidencia: [galería comparativa](mockups/verify/final/index.html), [matriz](mockups/verify/final/matrix.json), [instrucciones](mockups/verify/final/README.md).
