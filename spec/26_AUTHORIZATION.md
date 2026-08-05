# Authentication

JWT Bearer Token

Access Token
Refresh Token

Authorization:
Bearer <token>

Role-Based Authorization

Roles

Administrator
Operator
Viewer

Permissions are evaluated per endpoint.

## Decisiones de implementación — Fase 2

### Identidad de acceso

- El login local utiliza `email`, nunca `username`.
- Las cuentas se almacenan localmente en SQLite.
- Las contraseñas se almacenan exclusivamente como hash bcrypt; nunca se persisten ni registran en texto plano.

### Administrador inicial

- Al iniciar la aplicación, si no existe ningún usuario con rol `Administrator`, se crea uno usando `ADMIN_EMAIL` y `ADMIN_PASSWORD` desde el archivo `.env` o las variables de entorno.
- La aplicación debe fallar al iniciar si no existe Administrator y faltan dichas variables, para evitar una instalación sin administración controlada.
- El primer Administrator puede existir sin una Organization asignada porque se crea antes de la primera Organization. Los demás usuarios pertenecen a una Organization.

### Política RBAC MVP

- `Administrator`: acceso completo, incluida eliminación.
- `Operator`: lectura, creación y actualización de la jerarquía operativa; no eliminación.
- `Viewer`: solo lectura.
