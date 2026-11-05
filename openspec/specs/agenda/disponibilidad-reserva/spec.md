# agenda/disponibilidad-reserva Specification

## Purpose
Provide public availability calculation by treatment duration and authenticated patient reservation with engine-level anti-overlap, concurrency handling, and contracts for deposit and WhatsApp reminder.

## Requirements

### Requirement: Public availability calculation excludes occupied and blocked slots

The system SHALL expose `GET /horarios-libres` without authentication and return free slots for a given date and treatment, considering only active sillones, active turnos and active bloqueos, expanding each slot by the treatment duration. It SHALL NOT expose patient data.

#### Scenario: Free slots exclude occupied and blocked ranges (feliz)

- **GIVEN** an active sillón with an active turno and an active bloqueo overlapping part of the date
- **WHEN** a client requests `GET /horarios-libres` for that date and treatment
- **THEN** the response lists only slots that do not overlap any active turno or bloqueo and each slot spans the treatment duration

#### Scenario: Sillón filter restricts results (borde)

- **GIVEN** free slots in two active sillones
- **WHEN** the request includes a valid `sillon` filter
- **THEN** only slots for that sillón are returned

#### Scenario: Inactive sillones or treatments are excluded (borde)

- **GIVEN** an inactive sillón or treatment
- **WHEN** availability is calculated
- **THEN** that sillón is not offered and an inactive treatment is rejected with 422

### Requirement: Availability responses are cached briefly and invalidated on reservation

The system SHALL cache availability results in Redis with a short TTL and invalidate affected cache entries when a turno is created.

#### Scenario: Cached availability is reused (feliz)

- **GIVEN** a previous identical availability request
- **WHEN** the same request is repeated within the TTL
- **THEN** the result is served from cache without recomputing

#### Scenario: Reservation invalidates cache (borde)

- **GIVEN** cached availability for a date and sillón
- **WHEN** a turno is created for that date and sillón
- **THEN** subsequent availability requests recompute instead of using stale cache

### Requirement: Reservation requires an authenticated patient

The system SHALL require a valid access token for a user with role `paciente` to create a turno via `POST /turnos`; anonymous requests SHALL receive 401 and other roles 403.

#### Scenario: Anonymous reservation is rejected (error de negocio)

- **GIVEN** a request without a valid Bearer token
- **WHEN** `POST /turnos` is submitted
- **THEN** the system responds 401 and no turno is created

#### Scenario: Non-patient role is rejected (borde)

- **GIVEN** an authenticated user with role `odontologo` or `secretaria`
- **WHEN** `POST /turnos` is submitted
- **THEN** the system responds 403

### Requirement: Reservation validates the slot and computes fin from treatment duration

The system SHALL validate that the requested sillón and inicio form a free slot for the treatment duration, compute `fin = inicio + duracion_min` on the server and reject a client-supplied `fin`; an occupied or blocked slot SHALL respond 409 with alternative slots.

#### Scenario: Valid reservation computes fin (feliz)

- **GIVEN** a free slot for the requested treatment
- **WHEN** an authenticated patient submits `POST /turnos` with sillón, tratamiento and inicio
- **THEN** the system creates the turno with `fin = inicio + duracion_min` and responds 201

#### Scenario: Occupied slot returns alternatives (error de negocio)

- **GIVEN** the requested slot overlaps an active turno or bloqueo
- **WHEN** `POST /turnos` is submitted
- **THEN** the system responds 409 and includes `alternativas` with available slots

### Requirement: Anti-overlap is enforced at the database engine on reservation

The system SHALL rely on the partial EXCLUDE constraint on `turno` to reject concurrent or conflicting inserts; an `exclusion_violation` SHALL be translated to 409 with alternative slots without creating the turno.

#### Scenario: Concurrent reservations yield one success (borde)

- **GIVEN** two simultaneous requests for the same free slot
- **WHEN** both are processed
- **THEN** exactly one responds 201 and the other responds 409 with alternatives

### Requirement: Deposit requirement returns 402 without creating a turno

When the selected treatment requires a deposit (seña), the system SHALL respond 402 with checkout details and SHALL NOT persist a turno until the payment webhook approves it.

#### Scenario: Treatment requiring deposit returns checkout (feliz)

- **GIVEN** a treatment that requires a deposit
- **WHEN** an authenticated patient submits `POST /turnos`
- **THEN** the system responds 402 with checkout information and no turno is created

### Requirement: Reservation enqueues a WhatsApp reminder job

On successful reservation the system SHALL enqueue a WhatsApp reminder job in Redis; enqueue failure SHALL NOT invalidate the already created turno and SHALL schedule a retry.

#### Scenario: Reminder job enqueued on reservation (feliz)

- **GIVEN** a successfully created turno
- **WHEN** the reservation completes
- **THEN** a reminder job is enqueued in Redis for that turno

### Requirement: Reservation preserves timezone-aware timestamps and centavos

The system SHALL store `inicio` and `fin` as TIMESTAMPTZ and SHALL NOT accept naive timestamps; monetary references SHALL remain in centavos ARS.

#### Scenario: Naive timestamp is rejected (borde)

- **GIVEN** a reservation request with a naive `inicio`
- **WHEN** `POST /turnos` is submitted
- **THEN** the system responds 422 and no turno is created
