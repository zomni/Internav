# Entity Contracts

## Common Invariants

- Every entity has a UUID.
- Every entity has created_at and updated_at.
- Active records use is_active=true.
- Soft deletion sets deleted_at.

---

## Organization

Purpose:
Top-level owner of all data.

Required
- id
- name
- code

Constraints
- code unique
- name required
- cannot be deleted while child Sites exist

---

## Site

Represents a physical location.

Constraints
- belongs to one Organization
- unique name within Organization

---

## Building

Constraints
- belongs to one Site
- unique code inside Site

---

## Floor

Constraints
- belongs to one Building
- level unique inside Building
- exactly zero or one active FloorPlan

---

## Grid

Constraints
- belongs to one Floor
- exactly one active Grid per Floor

---

## Cell

Constraints
- belongs to one Grid
- row/column unique
- walkable immutable while Campaign is active

---

## Campaign

States

Draft
Ready
Collecting
Paused
Completed
Archived

Transitions

Draft -> Ready
Ready -> Collecting
Collecting -> Paused
Paused -> Collecting
Collecting -> Completed
Completed -> Archived

---

## Fingerprint

Immutable after creation.

---

## Dataset

Immutable snapshot.

---

## ModelVersion

States

Training
Failed
Ready
Published
Archived

Only one Published model per Floor.