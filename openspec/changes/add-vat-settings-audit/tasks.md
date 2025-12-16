## 1. Specification
- [ ] 1.1 Review current factor/VAT behavior and inputs.
- [ ] 1.2 Define data model/fields for VAT settings and audit log.
- [ ] 1.3 Confirm UI placement/behavior in `system-settings`.

## 2. Implementation
- [ ] 2.1 Add backend model/storage for VAT settings (rate, enabled).
- [ ] 2.2 Add audit logging for VAT changes (user, before/after, timestamp).
- [ ] 2.3 Expose VAT settings in system settings page with toggle and rate input.
- [ ] 2.4 Wire factor calculation to use VAT setting when enabled; respect disable.
- [ ] 2.5 Show VAT rate/enable state in relevant UIs; fall back safely when missing.
- [ ] 2.6 Persist VAT snapshot per factor and per line so later setting changes don’t alter stored factors; keep display/edit using saved values unless user recalculates.

## 3. Quality
- [ ] 3.1 Add tests for settings CRUD, audit log, and calculation toggle.
- [ ] 3.2 Validate `openspec` for this change.


