## Context

El MVP usa FastAPI, PostgreSQL, Redis y una PWA. C-11 está archivado y el correctivo de sede tiene su checklist completo. C-10 tiene pendiente el sandbox de pagos.

## Goals / Non-Goals

Reproducir el arranque, detectar regresiones y medir el piloto de una sede. ARCA, obras sociales, HCE y nuevas integraciones de producción quedan fuera del alcance.

## Decisions

- Compose espera a PostgreSQL y Redis sanos, ejecuta Alembic y recién entonces expone la API. La configuración base es local. Los archivos de entorno pueden suministrar credenciales sin versionarlas.
- CI separa regresión, navegador y arranque desde volúmenes limpios. Los tests con efectos se ejecutan con fixtures ficticios.
- El reporte de higiene usa fechas argentinas y solo expone métricas agregadas a personal autorizado. Las mediciones manuales se documentan para compararlas contra una línea base.
- Las decisiones comerciales y la activación de canales externos se registran con el responsable del piloto.

## Risks / Trade-offs

Los dobles de WhatsApp y Mercado Pago dan resultados reproducibles. La aceptación del proveedor real exige pruebas sandbox y decisiones operativas. El historial de turnos anteriores a una migración solo puede incluir eventos que efectivamente se registraron.
