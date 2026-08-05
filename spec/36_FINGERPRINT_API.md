# Fingerprint API

Resource: /fingerprints

Purpose
Store a labeled WiFi scan associated with one Cell.

Fields
- id
- campaign_id
- cell_id
- device_id
- captured_at
- sample_number
- orientation
- notes

Rules
- Immutable after creation.
- Must belong to an active Campaign.
- Must contain at least one AccessPointObservation.

Endpoints
GET /fingerprints
GET /fingerprints/{id}
POST /fingerprints