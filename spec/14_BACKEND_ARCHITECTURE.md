# Backend Architecture

Presentation Layer
↓

API Layer

↓

Application Layer

↓

Domain Layer

↓

Repository Layer

↓

Persistence Layer

Rules:

- Domain never depends on FastAPI.
- Repository hides database implementation.
- DTOs isolate API from domain.
- Services orchestrate use cases.