# Data Model

## General Rules

- UUID primary keys.
- UTC timestamps.
- Soft delete supported.
- Audit fields on every entity.
- Optimized for SQLite.
- Future compatible with PostgreSQL.

## Common Columns

id
created_at
updated_at
deleted_at
created_by
updated_by
version
is_active