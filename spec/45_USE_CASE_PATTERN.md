# Use Case Pattern

Each use case exposes:

execute(command)

Responsibilities

- validate input
- load entities
- enforce business rules
- persist changes
- emit events
- return DTO

Use cases never expose ORM models.