# Spec Delta

## MODIFIED Requirements

### Requirement: Deposit requirement returns 402 without creating a turno

When the treatment requires a deposit, or the patient elects an enabled optional deposit, the system SHALL validate the slot and respond 402 with checkout details without persisting a turno until a verified payment is approved and the slot revalidated. The server treatment policy SHALL override omitted or false client flags. Checkout SHALL include provider, status, intento_id, checkout_url, expires_at, monto_centavos, moneda and modo.

#### Scenario: Treatment requiring deposit returns checkout (feliz)

- **GIVEN** a treatment that requires a deposit
- **WHEN** an authenticated patient submits `POST /turnos` with Idempotency-Key
- **THEN** the system responds 402 with checkout information and a durable payment attempt and no turno is created

#### Scenario: False flags cannot bypass required deposit

- **GIVEN** a treatment with mandatory server deposit policy
- **WHEN** the patient submits false or omitted sena, requiere_sena and deposit flags
- **THEN** the same deposit policy applies and no unpaid turno is created

#### Scenario: Optional deposit elected or declined

- **GIVEN** a treatment with optional deposit and valid server amount
- **WHEN** the patient elects deposit using an existing flag or declines it with all flags false
- **THEN** election returns 402 with checkout and decline preserves the ordinary 201 reservation flow

#### Scenario: Payment disabled or deposit unavailable

- **WHEN** the patient elects deposit on a treatment with deposit disabled, or a mandatory deposit cannot be processed because the payment integration is unavailable
- **THEN** the first case returns 422 and the second 503 without creating an unpaid turno

#### Scenario: Deposit idempotency key required

- **WHEN** a deposit branch is submitted without Idempotency-Key
- **THEN** the system returns 422 without starting checkout, while ordinary no-deposit reservations retain their existing contract

#### Scenario: Occupied slot is not sent to checkout

- **WHEN** a deposit reservation is submitted for a slot already occupied or blocked
- **THEN** the system returns 409 with alternatives and does not offer checkout for that slot
