# Sistema visual — Turnos odontología

Mode: system-and-mockups
Revision: 1
Approval: approved (2026-11-10, by user)

Política elegida explícitamente por el usuario el 2026-11-10: sistema y mockups.
Base revisión 1 aprobada explícitamente el 2026-11-10: «si, adelante», en respuesta
a la presentación de HTML y capturas. Esta aprobación permite preparar mockups;
no aprueba las pantallas específicas de C-11 ni autoriza todavía su implementación.

## Propósito y brief

Documentar y reutilizar el estilo existente, sin rebranding: una herramienta de
trabajo móvil para pacientes, secretaria y odontólogo de una sola sede argentina.
Prioridad: leer horarios/estados, decidir acciones y reconocer restricciones sin
confundir pago con reserva. Escritorio 1440×900 y móvil 390×844; comprobar también
360px al implementar. Sin fuentes remotas, bibliotecas visuales ni cuentas externas.

## Fuentes y auditoría del producto existente

- `frontend/src/index.css`: fondo slate claro, texto #0F172A, acción #0369A1,
  bordes #CBD5E1, radio de botones 8px, campos de 46px, foco visible.
- `frontend/src/App.tsx`: marca textual «Turnos odontologia», navegación simple.
- `frontend/src/shared/ui.tsx`: mensajes de error/éxito y etiquetas de estado.
- `knowledge-base/01_vision_y_objetivos.md`, `03_actores_y_roles.md`,
  `05_reglas_de_negocio.md`, `06_funcionalidades.md`: tareas, privacidad y roles.
- No se encontró un logo de marca aprobado. Los iconos PWA existentes son assets
  de instalación, no prueba de identidad comercial. Nombre comercial/logo/contacto: (TBD).

## Archivos y reemplazos

- `brand.js`: modificar solo `BRAND_NAME` para cambiar todos los elementos
  `[data-brand-name]` de las vistas HTML. Texto insertado mediante `textContent`.
- `assets/logo.svg`: sustituir en esta ruta estable por el logo aprobado, con
  `viewBox` y título accesible. Hoy muestra «LOGO PROVISIONAL (TBD)» deliberadamente.
- `brand.md`: fuentes, tono e identidad pendiente; actualizar al confirmar marca.
- `tokens.css`: fuente única de valores visuales compartidos en previews/mockups.
- `components.html`: referencia local de componentes, no mockup de una pantalla
  ni UI conectada. Datos e importes ilustrativos ficticios, no tarifas.
- `previews/`: capturas móvil y escritorio; se registran tras renderizar.

Abrir `components.html` en navegador, o servir solo esta carpeta en localhost.
No necesita build ni acceso a API/DB. Los cambios de tokens/activos tras aprobación
incrementan Revision, invalidan Approval y requieren revisar las pantallas afectadas.
Esta base no cambia todavía `frontend/src/index.css`.

## Decisiones abiertas

- Nombre comercial y logo: (TBD); se conserva el nombre funcional existente.
- Imágenes: no necesarias para operaciones; cualquier fotografía futura: (TBD).
- Revisión explícita de esta base antes de mockups: aprobada por el usuario.

## Preview

Renderizado e inspección visual realizados el 2026-11-10 con Playwright:

- [Escritorio 1440×900](previews/components-desktop-1440.png), captura full page.
- [Móvil 390×844](previews/components-mobile-390.png), captura full page.
- Sin overflow horizontal, assets rotos ni recursos externos en ambos tamaños;
  controles comprobados de 47,58 px de alto en escritorio. Texto/error/estados
  inspeccionados en ambas capturas. No es auditoría completa de accesibilidad.
- Comprobación adicional de ancho 360px sin overflow horizontal.
- Vista HTML: [components.html](components.html). Servidor temporal solo loopback;
  se detiene después de las capturas. Se puede abrir el HTML local directamente.

Las capturas no representan verificación funcional. La aprobación visual del
usuario corresponde solo a esta base revisión 1, no a mockups posteriores.
