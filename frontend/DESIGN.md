# Diseño de la aplicación

La fuente visual mantenida es [sistema revisión 1](../design-system/README.md). El alcance de esta revisión es C-11, documentado en [design.md](../openspec/changes/c-11-pwa-agenda-gestion/design.md). No cambia tokens ni la identidad aprobada.

`src/index.css` es el dueño runtime de colores, espaciado, foco y variantes staff. Replica los tokens portables de `design-system/tokens.css` dentro del contexto de build Docker. Los mensajes reutilizan `src/shared/ui.tsx`.

Select y Date son controles nativos, como los controles existentes del producto. Se acepta la geometría y calendario del navegador/sistema; etiquetas en español y fechas de negocio en America/Argentina/Buenos_Aires mediante `src/shared/time.ts`. No se cambia el huso según el dispositivo. Formularios staff usan validación de aplicación y comprobación autoritativa del servidor.

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Select/Listbox | select nativo | sistema rev1 y contratos API | filtros y campos staff | verify-c11-visual.cjs y Staff.test.tsx |
| Date | input date/datetime-local y shared/time.ts | reglas RN-TU y design C-11 | día y rango AR | matriz visual y regresión backend |
| Form | editores staff y contratos runtime | design C-11 | alta, edición y confirmación | Staff.test.tsx |
| Toast | shared/ui.tsx Notice | sistema rev1 | aviso inline persistente | DOM y navegador |
| CRUD | SessionProvider y guard de escrituras | contratos API y RN-GL | consulta, edición, baja lógica | verification.md C-11 |
