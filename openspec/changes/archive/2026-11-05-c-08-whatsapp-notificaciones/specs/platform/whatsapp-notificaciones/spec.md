# Spec Delta

## Purpose

Automate WhatsApp reminders and patient confirmations/cancellations via a Meta template provider, a Redis-backed worker with retries, and a signed idempotent webhook, reducing no-shows without manual work.

## ADDED Requirements

### Requirement: Worker consumes queued reminder jobs and sends a Meta template

The system SHALL consume turno ids enqueued in the Redis list `wa:reminders` and send a WhatsApp reminder using the configured Meta template for each turno. Send failures SHALL be retried with backoff and the job re-enqueued; a failed send SHALL NOT invalidate the already created turno.

#### Scenario: Enqueued turno generates a reminder (feliz)

- **GIVEN** a turno id present in `wa:reminders`
- **WHEN** the worker processes the job
- **THEN** a reminder is sent via the configured provider and a `RecordatorioWA` with tipo `recordatorio` and estado `enviado` is persisted

#### Scenario: Provider failure keeps turno and re-enqueues (error de negocio)

- **GIVEN** the provider is unavailable while processing a job
- **WHEN** the send fails
- **THEN** the turno remains created, the job is re-enqueued for retry and a `RecordatorioWA` with estado `fallido` is persisted

### Requirement: Provider is selected from environment variables

The system SHALL select the WhatsApp provider from `WHATSAPP_PROVIDER` and authenticate with `WHATSAPP_API_KEY`, both sourced only from environment variables. In test mode a mock provider SHALL be usable without real credentials.

#### Scenario: Missing credentials do not crash reservation (borde)

- **GIVEN** `WHATSAPP_PROVIDER` is empty
- **WHEN** a reminder job is processed
- **THEN** the worker uses the mock provider and records the attempt without raising an unhandled error

### Requirement: Webhook receives patient responses with signature verification

The system SHALL expose `POST /webhooks/whatsapp` accepting a payload with a response (`confirmo` or `cancelo`) and a `message_id`, and SHALL reject requests whose signature does not verify with 401.

#### Scenario: Valid signed webhook is accepted (feliz)

- **GIVEN** a correctly signed webhook payload with `confirmo` and a `message_id`
- **WHEN** `POST /webhooks/whatsapp` is called
- **THEN** the system responds 2xx and processes the response

#### Scenario: Invalid signature is rejected (error de negocio)

- **GIVEN** a webhook payload with a bad or missing signature
- **WHEN** `POST /webhooks/whatsapp` is called
- **THEN** the system responds 401 and no state changes

### Requirement: Webhook is idempotent by message_id

The system SHALL process a given `message_id` at most once; a duplicate `message_id` SHALL NOT duplicate effects and SHALL return a successful response.

#### Scenario: Duplicate message_id is idempotent (borde)

- **GIVEN** a `message_id` already processed
- **WHEN** the same payload is received again
- **THEN** no additional state change occurs and the response is successful

### Requirement: Confirmo updates the turno to confirmed

The system SHALL, on a verified `confirmo` response, match the turno from the `message_id` and set its state to `confirmado`, recording the response in `RecordatorioWA`.

#### Scenario: Confirmo confirms turno (feliz)

- **GIVEN** a valid `message_id` linked to a `reservado` turno
- **WHEN** the webhook receives `confirmo`
- **THEN** the turno becomes `confirmado` and the linked `RecordatorioWA` has respuesta `confirmo` and estado `respondido`

### Requirement: Cancelo respects the 2-hour window

The system SHALL, on a verified `cancelo` response, cancel the turno only if it starts in at least `APPOINTMENT_CANCEL_MINUTES` (default 120) minutes; otherwise it SHALL reject with a message telling the patient to call the consultorio, leaving the turno unchanged.

#### Scenario: Cancelo with more than 2 h cancels turno (feliz)

- **GIVEN** a valid `message_id` linked to a turno starting in more than 2 hours
- **WHEN** the webhook receives `cancelo`
- **THEN** the turno becomes `cancelado` and the linked `RecordatorioWA` has respuesta `cancelo` and estado `respondido`

#### Scenario: Cancelo with less than 2 h is rejected (error de negocio)

- **GIVEN** a valid `message_id` linked to a turno starting in less than 2 hours
- **WHEN** the webhook receives `cancelo`
- **THEN** the turno remains unchanged and the response includes a message to call the consultorio

### Requirement: Every send and response is recorded in RecordatorioWA

The system SHALL persist each reminder send and each patient response in `RecordatorioWA`, including tipo, plantilla, `message_id`, estado (`enviado|entregado|leido|respondido|fallido`) and respuesta (`confirmo|cancelo|null`).

#### Scenario: Response recorded (feliz)

- **GIVEN** a processed webhook response
- **WHEN** it completes
- **THEN** a `RecordatorioWA` row exists with the provider `message_id`, the response value and estado `respondido`

### Requirement: Turno state changes via webhook set origin to whatsapp

The system SHALL update turno state through `GestionTurnosService` with origin `whatsapp` for audit purposes (RN-GL-03).

#### Scenario: Origin whatsapp persisted (borde)

- **GIVEN** a webhook that confirms or cancels a turno
- **WHEN** the state change is persisted
- **THEN** the turno's origen is `whatsapp`