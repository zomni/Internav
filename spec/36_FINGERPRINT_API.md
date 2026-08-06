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
GET /campaigns/{campaign_id}/fingerprints
  List fingerprints for a campaign (no observations).
GET /campaigns/{campaign_id}/fingerprints/count
  Count fingerprints for a campaign.
GET /fingerprints/{id}
  Get one fingerprint including observations.
POST /campaigns/{campaign_id}/fingerprints
  Create a fingerprint (Operator+). Requires campaign Collecting or Paused.
DELETE /fingerprints/{id}
  Soft-delete a fingerprint (Operator+). Rejected (409) when the campaign
  is Completed or Archived.