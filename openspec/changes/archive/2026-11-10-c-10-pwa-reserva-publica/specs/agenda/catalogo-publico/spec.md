# Spec Delta

## Purpose

Ofrecer al paciente los sillones y tratamientos activos necesarios para elegir horarios, sin exponer configuracion administrativa ni datos de pacientes.

## ADDED Requirements

### Requirement: Catalogo publico minimo de recursos activos
GET /catalogo-publico SHALL permitir lectura anonima y devolver sillones con id/nombre y tratamientos con id/nombre/duracion_min/sena_politica/sena_centavos. Solo SHALL incluir recursos activos en orden estable nombre/id, sin campos administrativos, pacientes ni precio de referencia. No SHALL permitir consultar inactivos mediante parametros.

#### Scenario: Cargar filtros sin login
- **WHEN** un anonimo consulta catalogo con recursos activos e inactivos
- **THEN** recibe 200 con solo activos y campos permitidos para construir filtros y mostrar politica de sena servidor

#### Scenario: Catalogo vacio
- **WHEN** no hay recursos activos disponibles
- **THEN** recibe 200 con listas vacias, sin valores ficticios ni recursos inactivos

### Requirement: Catalogo publico no habilita administracion
La nueva lectura SHALL NOT cambiar los permisos de /api/config ni exponer bloqueos, auditoria o datos personales. Campos de sena SHALL reflejar la politica del backend de C-09, sin valores o importes inventados por el cliente.

#### Scenario: Anonimo intenta configuracion
- **WHEN** un anonimo consulta o modifica /api/config/tratamientos tras usar catalogo publico
- **THEN** sigue recibiendo 401 sin acceso administrativo

#### Scenario: Error del catalogo
- **WHEN** el servicio no puede consultar el catalogo
- **THEN** devuelve error controlado sin pacientes ni datos internos y el consumidor no recibe fixtures como si fueran recursos reales
