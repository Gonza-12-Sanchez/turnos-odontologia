# Evidencia final C-11

2026-11-12. 47 estados, 94 capturas, 141 comprobaciones a 360/390/1440 px. Galería: index.html. Detalles y diferencias: ../../../verification.md.

Reproducción desde frontend (dos terminales):

1. npm.cmd run build
2. npm.cmd run preview -- --host localhost --port 5195 --strictPort
3. node scripts/verify-c11-visual.cjs

Requiere Chrome local; PLAYWRIGHT_CHROME_PATH permite configurar su ejecutable. El script intercepta HTTP con datos ficticios, usa contextos aislados y comprueba layout, foco y errores. No altera la base de datos. Los estados históricos de gates tienen equivalencia documentada en matrix.json.

Las imágenes live-390.png y live-1440.png son adicionales: comprobante leído mediante API real sobre datos ficticios existentes. No forman parte de las 94 capturas controladas. La revisión visual no equivale a aprobación humana ni a certificación de accesibilidad.
