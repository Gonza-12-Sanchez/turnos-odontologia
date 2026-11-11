# C-11 — Mockups de gestión del consultorio

Design system revision: 1
Mockup revision: 1
Approval: approved (2026-11-10, by user)
Preview: rendered (2026-11-10)

La base visual fue aprobada por el usuario el 2026-11-10 («si, adelante»).
Mockups revisión 1 aprobados el 2026-11-10: «continúa», en respuesta a su
presentación y a la pregunta de aprobarlos para implementar por etapas. No se
habilitan funcionalidades con gates pendientes ni pagos reales por esta aprobación.

## Abrir y revisar

Abrir [catalogo.html](catalogo.html) directamente en el navegador. Cada estado
tiene un enlace a su HTML local y a las capturas móvil y escritorio. No requiere
instalar dependencias ni levantar API, Postgres o Redis. Mantener esta carpeta y
`design-system/` en sus rutas actuales para resolver los recursos compartidos.

Se puede recorrer [index.html](index.html), con navegación local entre escenarios.
La query `scene` solo selecciona claves de la allowlist de `mockups.js`.
Los enlaces cambian de maqueta: NO confirman acciones ni simulan una transacción.
Los formularios solo ilustran entradas y no envían ni guardan datos. Las fechas
son texto de maqueta en día/mes/año y hora24 para evitar ambigüedad del control
nativo según locale del equipo; no son un parser productivo.

## Brief y fuentes

- Audiencia: secretaria y odontólogo de un consultorio argentino de una sede.
- Tarea central: leer turnos por sillón y decidir una acción explícita; no es
  una portada comercial ni un calendario de arrastrar y soltar.
- Layout: filas por sillón y panel lateral en escritorio; una columna en móvil
  con enlaces al detalle. Formularios/acciones conservan orden DOM.
- Sistema aprobado: `../../../../design-system/{README.md,tokens.css,brand.js}`.
  Sin copias de tokens, fuentes remotas, imágenes externas ni librerías nuevas.
- Logo y nombre comercial siguen (TBD), visibles como provisionales; se conserva
  el nombre funcional. Favicon usa el asset estable `design-system/assets/logo.svg`.
- Alcance y reglas: `../{proposal,design,tasks}.md`,
  `../specs/consultorio/gestion-pwa/spec.md` y KB 03/05/06/07.
- Contratos observados: schemas de turnos/config, servicios de lectura/gestión,
  rutas de cobros/seña. Sus brechas están documentadas en `../design.md`.

## Pantallas y estados

47 estados locales, todos listados con nombre en [el catálogo](catalogo.html).
Las capturas siguen `previews/<scene>-390.png` y `previews/<scene>-1440.png`.

| Familia | Cobertura |
|---|---|
| Agenda | Secretaria, odontólogo, carga, vacío, error, offline, fecha no verificada, acciones no verificadas y acceso denegado a paciente |
| Detalle | Historial ficticio futuro e historial actual no disponible; confirmar, cancelar, ventana2h, reprogramar, confirmar nuevo horario, 409 y alternativas; asistencia por ambos roles; motivo de sobreturno; resultado incierto |
| Configuración | Listas de tratamientos/sillones/bloqueos, alta/edición, duración inválida, política de seña bloqueada, sede faltante, rango inválido, guardado con advertencia, baja/reactivación, carga/vacío/error |
| Cobros | Contrato bloqueado, selección de turno, resumen incremental, precio nullable, diferencia con motivo, éxito, replay, resultado incierto y diferencia auditada |

### Vistas principales

| Vista | HTML | Móvil | Escritorio |
|---|---|---|---|
| Agenda secretaria | [Abrir](index.html?scene=agenda-secretaria) | [390](previews/agenda-secretaria-390.png) | [1440](previews/agenda-secretaria-1440.png) |
| Agenda odontólogo | [Abrir](index.html?scene=agenda-odontologo) | [390](previews/agenda-odontologo-390.png) | [1440](previews/agenda-odontologo-1440.png) |
| Configuración | [Abrir](index.html?scene=config-tratamientos) | [390](previews/config-tratamientos-390.png) | [1440](previews/config-tratamientos-1440.png) |
| Bloqueo con advertencia | [Abrir](index.html?scene=config-advertencia) | [390](previews/config-advertencia-390.png) | [1440](previews/config-advertencia-1440.png) |
| Cobros bloqueados | [Abrir](index.html?scene=cobros-bloqueados) | [390](previews/cobros-bloqueados-390.png) | [1440](previews/cobros-bloqueados-1440.png) |
| Cobro futuro con diferencia | [Abrir](index.html?scene=cobros-diferencia) | [390](previews/cobros-diferencia-390.png) | [1440](previews/cobros-diferencia-1440.png) |

## Límites de los estados futuros

- «Agenda poblada» ilustra presentación esperada tras G-fecha; no acredita que
  la consulta UTC actual ya entregue el día argentino completo.
- Acciones habilitadas ilustran el contrato esperado tras G-acciones. La variante
  `agenda-acciones-bloqueadas` muestra la alternativa mientras no se verifique.
- Historial con actor/fecha es ficticio y está etiquetado como resultado futuro;
  el backend actual aún no lo entrega. No inventar ese historial al implementar.
- Alta de sillón con sede muestra el resultado futuro de G-contexto; también se
  incluye la falta de sede sin UUID manual. Editar señas espera G-sena-config.
- Cobros de éxito/replay/motivo son futuros y ficticios tras G-cobros. Por defecto
  la navegación lleva a `cobros-bloqueados`. No se hicieron pagos ni llamadas MP.
- Aprobar apariencia NO satisface gates backend, no autoriza correctivos C-09/C-10,
  ni implica aceptación integrada o producción.

## Preview e inspección

2026-11-10, Playwright/Chromium, locale es-AR, zona America/Argentina/Buenos_Aires:

- 47 estados × 2 tamaños = **94 capturas full-page**: 390×844 y 1440×900.
- Comprobación adicional de todos los estados a 360×844, sin overflow horizontal.
- 141 combinaciones estado/ancho: sin pageerror, respuestas HTTP >=400 ni recursos
  externos. Botones/campos/enlaces principales >=44px; el checkbox visual de22px
  tiene etiqueta clicable de46px. No es auditoría completa de accesibilidad.
- Smoke local: catálogo con47 entradas, foco visible en «Saltar al contenido»,
  navegación odontólogo sin acciones de cobros/config, selección de09:30 en
  confirmación de reprogramación y total ficticio90,00 tras override de60,00.
  Son comprobaciones de maqueta, no pruebas de RBAC ni persistencia backend.
- Capturas revisadas en ocho hojas de inspección, con revisión a tamaño completo
  adicional de agenda y formularios/configuración/cobros representativos.
  [01](previews/revision-01.png), [02](previews/revision-02.png),
  [03](previews/revision-03.png), [04](previews/revision-04.png),
  [05](previews/revision-05.png), [06](previews/revision-06.png),
  [07](previews/revision-07.png), [08](previews/revision-08.png).
- Correcciones antes de presentar revisión1: campo fecha inequívoco, etiqueta
  checkbox táctil, contexto de rol en asistencia, confirmación específica de
  reprogramación y resultado de override con diferencia monetaria visible.
- Servidor temporal propio: solo loopback y dos raíces públicas allowlist
  (`design-system/` y esta carpeta), sin acceso al resto del repo. Detenido tras revisión.

No se ejecutaron suites funcionales, migraciones, credenciales, pagos, llamadas
a API ni cambios en `frontend/src`/`backend`. Capturas no equivalen a E2E.

## Aprobación y reemplazos

Revisión1 aprobada por el usuario. Sus capturas son criterios de aceptación en
tasks.md y design.md. Si se solicita cambiar apariencia, registrar nueva revisión,
restablecer Approval pending y volver a mostrar las capturas afectadas. No editar
silenciosamente una maqueta aprobada. Las leyendas «aprobación pendiente» en las
capturas originales reflejan su momento de presentación; se conservan sin alterarlas.

Marca se reemplaza en `design-system/brand.js`; logo en `design-system/assets/logo.svg`.
No modificar tokens de la base aprobada sin incrementar revisión y renovar aprobación.
