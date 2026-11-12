## 1. Arranque y CI

- [x] 1.1 Configurar Compose local con migraciones y checks de salud de las cuatro capas.
- [x] 1.2 Incorporar smoke de Compose y navegador a CI con volúmenes aislados.
- [x] 1.3 Ejecutar CI y Compose limpios con PostgreSQL y Redis reales y documentar evidencia. Compose local verificado con volúmenes nuevos y Playwright contra la API real. GitHub Actions #43298806887 pasó en los tres jobs.

## 2. Flujos críticos

- [x] 2.1 Verificar doble reserva concurrente, cancelación en el límite de dos horas y agenda del día con varios sillones.
- [x] 2.2 Verificar webhook duplicado, pago rechazado y proveedor de WhatsApp caído.
- [x] 2.3 Verificar la trazabilidad de las transiciones del piloto académico y resolver las dependencias de C-10 y C-11 aplicables a ese alcance. Trazabilidad verificada con 338 pruebas, C-11 archivado y pagos comprobados con el adaptador simulado. El sandbox sigue en C-10 (tarea 8.2), fuera del cierre académico aprobado.

## 3. Aceptación del piloto

- [x] 3.1 Exponer un reporte autorizado de higiene de agenda y comprobar métricas y aislamiento.
- [x] 3.2 Documentar alcance, procedimiento de medición, manejo de credenciales y responsables de decisiones abiertas.
- [x] 3.3 Acordar proveedor y pagador de WhatsApp, política de seña por tratamiento y aceptación del piloto. Las decisiones académicas están en `docs/piloto.md`. La demo de agenda, los casos de pago simulado y el reintento de WhatsApp quedaron registrados en verification.md.
