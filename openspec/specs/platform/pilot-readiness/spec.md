# platform/pilot-readiness Specification

## Purpose

Verificar que el piloto académico de una sede arranque de forma reproducible, preserve la trazabilidad de los flujos críticos y mida el estado de la agenda con datos ficticios.

## Requirements

### Requirement: Arranque local verificable
El entorno local SHALL ejecutar las migraciones antes de aceptar solicitudes y exponer comprobaciones de salud de la API y la PWA.

#### Scenario: Inicio desde volúmenes limpios
- **WHEN** se inicia el entorno local con PostgreSQL y Redis disponibles
- **THEN** la base alcanza la última revisión y la API y la PWA responden correctamente

### Requirement: Regresión de flujos críticos
La verificación del MVP SHALL comprobar concurrencia, permisos, ventanas de tiempo, recuperación de pagos y fallos de notificación con datos ficticios.

#### Scenario: Eventos duplicados o fuera de ventana
- **WHEN** dos solicitudes compiten por un turno o se repite un evento externo
- **THEN** el sistema conserva un único efecto válido y mantiene la trazabilidad de la operación

### Requirement: Higiene y aceptación del piloto
El equipo SHALL poder medir el estado de confirmación de la agenda sin divulgar datos de pacientes y registrar decisiones comerciales antes de habilitar servicios externos.

#### Scenario: Consulta diaria autorizada
- **WHEN** el personal autorizado consulta la higiene para un día de agenda
- **THEN** recibe totales de estado y señal de turnos sin confirmar para ese día en Argentina
