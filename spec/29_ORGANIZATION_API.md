# Organization API

Resource: /organizations

Fields
- id (UUID)
- name
- code
- description
- is_active
- created_at
- updated_at

POST
Required:
- name
- code

Validation
- code unique
- name required

GET /organizations
Supports:
- pagination
- sorting
- filtering by code, name, active

DELETE
Soft delete only.