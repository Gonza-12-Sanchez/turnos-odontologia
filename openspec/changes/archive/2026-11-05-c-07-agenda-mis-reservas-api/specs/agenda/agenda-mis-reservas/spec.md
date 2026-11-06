# Spec Delta

## Purpose

Provides authenticated read endpoints for the daily agenda by sillón and for a patient's own reservations, with role-based access, filters, compact mobile-friendly payloads and permitted-action hints.

## ADDED Requirements

### Requirement: Daily agenda is available to odontólogo and secretaria
The system SHALL expose GET /agenda requiring an authenticated user with role odontólogo or secretaria, returning the turnos of the requested date grouped by sillón, including paciente, tratamiento, estado, tolerancia_min and sobreturno flag. Anonymous requests SHALL receive 401 and paciente SHALL receive 403.

#### Scenario: Odontólogo ve agenda del día (feliz)
- **WHEN** an authenticated odontólogo requests GET /agenda?fecha=hoy
- **THEN** the system responds 200 with turnos grouped by sillón including paciente, tratamiento, estado and tolerancia_min

#### Scenario: Paciente no accede a agenda (borde)
- **WHEN** an authenticated paciente requests GET /agenda
- **THEN** the system responds 403 and no agenda data is returned

#### Scenario: Anónimo no accede a agenda (error)
- **WHEN** a request without a valid Bearer token calls GET /agenda
- **THEN** the system responds 401

### Requirement: Agenda supports filters by sillón and estado
The system SHALL accept optional sillon and estado query parameters on GET /agenda and return only turnos matching all provided filters.

#### Scenario: Filtro por sillón (feliz)
- **WHEN** GET /agenda is called with a valid sillon filter
- **THEN** only turnos for that sillón are returned

#### Scenario: Filtro por estado (borde)
- **WHEN** GET /agenda is called with estado=confirmado
- **THEN** only turnos in that state are returned

### Requirement: Mis reservas returns only the patient's own turnos
The system SHALL expose GET /mis-reservas requiring an authenticated paciente and return only turnos whose paciente_id matches the authenticated patient, ordered by inicio ascending, with estado and permitted actions. Other patients' turnos SHALL NOT be included.

#### Scenario: Paciente ve solo lo propio (feliz)
- **WHEN** an authenticated paciente requests GET /mis-reservas
- **THEN** the response contains only that patient's turnos ordered by fecha

#### Scenario: Aislamiento entre pacientes (borde)
- **GIVEN** turnos belonging to two different patients
- **WHEN** one patient requests GET /mis-reservas
- **THEN** turnos of the other patient are absent from the response

### Requirement: Permitted actions reflect the 2-hour window
Each turno returned by GET /mis-reservas SHALL include an acciones (or acciones_permitidas) object indicating whether cancelar and reprogramar are allowed according to RN-TU-02: allowed only when inicio is at least APPOINTMENT_CANCEL_MINUTES in the future. A turno starting in less than 2 hours SHALL NOT offer cancelar.

#### Scenario: Turno lejano permite cancelar (feliz)
- **WHEN** a turno starts in more than 2 hours
- **THEN** acciones.cancelar is true

#### Scenario: Turno próximo no ofrece cancelar (borde)
- **WHEN** a turno starts in less than 2 hours
- **THEN** acciones.cancelar is false

### Requirement: Tolerance is visible in read responses
The system SHALL include tolerancia_min (default 5, from LATE_TOLERANCE_MINUTES) in every turno returned by GET /agenda and GET /mis-reservas.

#### Scenario: Tolerancia visible (feliz)
- **WHEN** a read endpoint returns a turno
- **THEN** the payload includes tolerancia_min equal to the configured value

### Requirement: Sobreturno is flagged in agenda
The system SHALL include es_sobreturno and motivo_sobreturno in agenda responses so the client can show a visual warning of sobreturnos.

#### Scenario: Sobreturno visible (feliz)
- **GIVEN** a turno marked as sobreturno
- **WHEN** it is returned by GET /agenda
- **THEN** es_sobreturno is true and motivo_sobreturno is present

### Requirement: Read responses are compact and avoid N+1
The system SHALL eager-load paciente, tratamiento and sillón in a single query per request and SHALL return compact payloads suitable for mobile clients, without large nested objects beyond the needed fields.

#### Scenario: Sin N+1 (borde)
- **WHEN** GET /agenda returns multiple turnos across sillones
- **THEN** paciente, tratamiento and sillón data are present without additional queries

### Requirement: Date scoping and ordering
GET /agenda SHALL require fecha. GET /mis-reservas SHALL accept optional desde/hasta date filters and SHALL order results by inicio ascending.

#### Scenario: Agenda requiere fecha (error)
- **WHEN** GET /agenda is called without fecha
- **THEN** the system responds 422

#### Scenario: Mis reservas ordenadas (feliz)
- **WHEN** a paciente has multiple turnos
- **THEN** GET /mis-reservas returns them ordered by inicio ascending