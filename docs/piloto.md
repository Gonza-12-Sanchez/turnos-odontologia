# Piloto Odonto v1

## Puesta en marcha local

Desde la raíz, con Docker Compose 2.24 o posterior:

```sh
docker compose up --build --wait
```

La PWA queda en http://localhost:4173 y la salud de la API en http://localhost:8000/api/health. Compose aplica las migraciones. La base inicial está vacía. Usá únicamente fixtures ficticios en validación. Este archivo Compose publica los puertos en loopback y está orientado al desarrollo y la aceptación local.

Las integraciones externas quedan deshabilitadas sin configuración. Para un entorno del consultorio, definí HTTPS, acceso, copias de seguridad y secretos mediante su configuración de despliegue. Las variables de ejemplo viven en `backend/.env.example` y `frontend/.env.example`.

## Decisiones del piloto académico

La aceptación académica se evalúa en una sede ficticia, con pacientes de prueba y sin transacciones externas.

| Tema | Decisión académica | Responsable ficticio |
| --- | --- | --- |
| Proveedor de WhatsApp | Simulador local con resultados de envío exitoso y caída del proveedor en pruebas. Los mensajes usan teléfonos ficticios. | Equipo técnico |
| Pago de mensajes | El consultorio ficticio asume el costo presupuestado. En la demo el gasto es ARS 0. | Administración |
| Seña por tratamiento | Control sin seña. Limpieza con seña opcional de ARS 3.000. Endodoncia con seña obligatoria de ARS 10.000. Son valores de demostración. | Consultorio |
| Mercado Pago | Usar el modo mock para mostrar aprobación y rechazo. La validación separada de C-10 requiere el sandbox de Mercado Pago. | Equipo técnico |

Para la demo de agenda, mantener deshabilitados los pagos externos y preparar tratamientos y turnos de una sede ficticia. Para checkout, aprobación y rechazo, usar las pruebas de integración `tests/test_c09_sena_api.py` y `tests/test_c09_webhook.py`, que sustituyen el adaptador externo. Configurar `MP_MODE=mock` por sí solo no sustituye el adaptador. La caída de WhatsApp se demostró con un proveedor ficticio que falló en el primer intento y permitió verificar el reencolado en Redis.

La demo se considera aceptada cuando secretaría confirma un turno, odontología registra asistencia, el reporte refleja los conteos del día y el equipo puede mostrar la reserva con y sin seña, el rechazo de pago simulado y el reintento de un recordatorio ante una falla simulada. Registrar el resultado de la ejecución en la evidencia de C-12.

## Mediciones

Secretaría y odontología pueden consultar `GET /agenda/higiene?fecha=AAAA-MM-DD` con su sesión. La API devuelve totales agregados y una alerta si quedan turnos reservados sin confirmar. Si PostgreSQL o Redis ya usan los puertos locales, configurá `POSTGRES_HOST_PORT` o `REDIS_HOST_PORT` antes de arrancar.

- Dobles reservas por sillón. Registrar solapamientos de turnos activos por día. El objetivo es cero.
- Confirmaciones. Dividir los turnos confirmados por los turnos reservados más confirmados en un corte fijo previo a la jornada. Registrar el horario del corte y omitir el porcentaje cuando no hay turnos.
- Inasistencias. Comparar la proporción de ausentes sobre asistidos más ausentes con el registro previo del consultorio. Mantener la misma ventana de observación.
- Tiempo de secretaría. Registrar los minutos diarios dedicados a confirmaciones manuales y comparar la mediana semanal con la línea base previa al piloto.
- Trazabilidad. Muestrear turnos gestionados y comprobar acción, fecha y origen en el historial. El histórico previo a su incorporación puede estar incompleto.

## Alcance excluido

- ARCA y facturación electrónica quedan para fase 2.
- Obras sociales, liquidaciones, HCE y odontograma quedan para fase 3 o posterior.
- El MVP cubre una sede. Quedan fuera las campañas, el marketplace y la sincronización bidireccional con calendarios.
