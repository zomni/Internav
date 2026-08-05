# Backend Structure

Recommended layout

backend/
  app/
    api/
    application/
    domain/
    infrastructure/
    repositories/
    services/
    schemas/
    models/
    security/
    config/
    workers/
    tests/

Dependency direction

API
 -> Application
 -> Domain
 <- Infrastructure