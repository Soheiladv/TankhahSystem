## ADDED Requirements

### Requirement: VAT settings managed centrally
The system SHALL store VAT configuration (percentage and enabled flag) in system settings so that all factor calculations use the configured values.

#### Scenario: VAT enabled with custom rate
- **WHEN** an admin sets VAT percentage to a positive decimal value and enables VAT in system settings
- **THEN** the value is persisted
- **AND** subsequent factor calculations use that percentage to compute VAT amounts.

#### Scenario: VAT disabled
- **WHEN** VAT enabled flag is off in system settings
- **THEN** factor calculations SHALL skip VAT (treated as zero) regardless of any default percentages in forms.

#### Scenario: Invalid VAT input rejected
- **WHEN** an admin enters a negative value or a value above a defined maximum (e.g., > 100)
- **THEN** the system SHALL reject the change and show a validation error.

### Requirement: VAT setting changes are audited
The system SHALL log every change to VAT settings including user, timestamp, old values, and new values, and display the log in the system settings UI.

#### Scenario: Change recorded
- **WHEN** a user updates VAT percentage or enabled flag
- **THEN** an audit record is created with username, datetime, previous values, and new values.

#### Scenario: Audit visible in settings
- **WHEN** viewing VAT settings in system settings
- **THEN** recent audit entries for VAT changes are listed with user, time, old/new values.

### Requirement: Historical factors keep their saved VAT
The system SHALL preserve the VAT rate/amount stored at the time of factor creation/edit so that later VAT setting changes do not alter previously saved factors or their lines.

#### Scenario: Viewing an old factor after VAT change
- **WHEN** VAT settings are changed after a factor was saved
- **THEN** displaying or editing that factor uses the VAT rate/amount stored with the factor/lines (not the new global setting), unless the user explicitly recalculates.


