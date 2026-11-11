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
