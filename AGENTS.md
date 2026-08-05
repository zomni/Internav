# AGENTS

## Mission

Implement the specification exactly as documented.

## Rules

- Read the specification before coding.
- Never invent requirements.
- Never change architecture without documentation.
- Keep documentation synchronized with implementation.
- Complete one task at a time.
- Keep everything domain-independent unless explicitly required.

## Python version

Use Python **3.11** or **3.12** for development. Python ≥3.13 has
compatibility issues with the ML stack (numpy, scikit-learn, joblib)
on Windows (`OverflowError: cannot convert longdouble infinity to
integer`). The `requires-python` in `pyproject.toml` is capped at
`<3.13` to prevent accidental installation on unsupported versions.

When creating the virtual environment, always specify the version:
```
py -3.12 -m venv .venv
.venv\Scripts\activate
```
Do **not** use bare `python -m venv .venv` — that picks the system
default, which may be 3.13+ and silently broken.

## Continuidad entre sesiones

Antes de empezar cualquier tarea, verifica si existe PROGRESS.md en la
raíz. Si existe, léelo primero — indica en qué fase del proyecto se
quedó el trabajo anterior y qué queda pendiente.

Al terminar tu sesión (o si detectas que te estás quedando sin contexto),
actualiza PROGRESS.md con el estado actual antes de finalizar.
