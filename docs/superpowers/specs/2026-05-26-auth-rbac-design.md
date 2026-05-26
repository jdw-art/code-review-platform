# Phase 1 Auth and RBAC Design

## Overview

This document defines the first implementation phase for the automated code review platform. Phase 1 focuses only on the backend authentication and authorization foundation. It does not include code review workflows, Git platform integration, project analytics, notifications, or frontend implementation.

The goal of this phase is to deliver a reusable identity and access control service that can support future admin UI work and later business modules.

## Scope

Phase 1 includes:

- Authentication with username and password
- JWT access token and refresh token flow
- Redis-backed refresh session management
- Forced password change on first login
- Self-service password change for the current user
- Admin reset password for other users
- User management
- Role management
- Permission management
- Menu management
- User-role, role-permission, and role-menu assignment
- Current user profile, permission list, and menu tree APIs
- Structured logging for auth and RBAC events

Phase 1 excludes:

- Frontend pages and components
- Git repository integration
- Pull request or diff review logic
- Project insights and reporting
- Notifications and messaging
- Advanced audit center UI
- SSO and third-party login

## Technology Stack

- Backend framework: FastAPI
- ORM and persistence: SQLAlchemy + PostgreSQL
- Cache and session state: Redis
- Authentication library: Authlib
- Password hashing: Argon2id
- Logging: Python `logging`

## Development Infrastructure Defaults

Phase 1 should assume the following local development defaults unless overridden by environment variables:

### PostgreSQL

- Host: `localhost`
- Port: `5432`
- Database: `ai_code_reviewer`
- Username: `postgres`
- Password: `postgres`

The backend should assume this database must be created explicitly for this project rather than reusing `langchain_app` or any unrelated existing database.

### Redis

- Host: `localhost`
- Port: `6379`
- DB index: `0`

Redis is already installed in the environment. The provided Docker Compose setup is the default local reference for both PostgreSQL and Redis, and the backend configuration should be compatible with it.

## Architectural Boundaries

The backend should be organized into clear modules with stable boundaries:

- `auth`: login, refresh, logout, logout all, token validation, self password change
- `users`: user CRUD, status management, admin password reset, user-role assignment
- `rbac`: role CRUD, permission CRUD, menu CRUD, role-permission assignment, role-menu assignment
- `me`: current user profile, permission list, menu tree
- `infra/security`: JWT utilities, password hashing, Redis session operations, auth dependencies, security guards

Authentication and authorization should remain separate concerns:

- Authentication answers who the current user is
- Authorization answers what the current user can access

`Menu` is only used for navigation visibility and routing metadata. It must not be used as the source of truth for API permission checks. API authorization must always rely on `Permission`.

## Login Model

The system uses `username` as the only login identifier in Phase 1.

- Open self-registration is disabled
- Users are created only by administrators
- The system auto-creates the initial super administrator on startup

Initial bootstrap account:

- Username: `admin`
- Initial password: `jdw112233`

This password must never be stored in plaintext. It is only used as an initialization input and must be hashed before persistence. The bootstrap user must be marked with `must_change_password = true`.

## Password Storage and Security

Passwords must be stored as one-way hashes using `Argon2id`.

Rules:

- Store only the encoded Argon2id hash in `users.password_hash`
- Never store plaintext passwords
- Never use reversible encryption for password storage
- Never provide a "recover original password" feature
- Password reset always writes a new Argon2id hash
- Each password set or reset should use a unique random salt embedded in the encoded hash

Operational behavior:

- First login with the bootstrap admin account requires immediate password change
- Admin reset password sets `must_change_password = true`
- Password change or reset revokes the user's existing refresh sessions

## Data Model

### Identifier Strategy

All database tables in Phase 1 must use integer-based identifiers only.

Rules:

- Every table primary key `id` must use `BIGINT`
- Every foreign key that references those primary keys must also use `BIGINT`
- Do not use UUID primary keys in Phase 1
- Do not mix `INTEGER` and `BIGINT` across related tables

In Python and SQLAlchemy code, these IDs can be represented as standard Python `int` values, while the database column type remains `BIGINT`.

### `users`

Core fields:

- `id` (`BIGINT` primary key)
- `username` (unique, required)
- `password_hash` (required)
- `nickname`
- `email` (nullable)
- `phone` (nullable)
- `is_active`
- `is_superuser`
- `must_change_password`
- `last_login_at`
- `created_at`
- `updated_at`

Constraints:

- `username` must be globally unique
- Disabled users cannot authenticate
- The last superuser must not be deletable or demotable
- A user must not be able to disable their own account or remove their own superuser status through admin APIs

### `roles`

Core fields:

- `id` (`BIGINT` primary key)
- `name`
- `code` (unique)
- `description`
- `is_system`
- `created_at`
- `updated_at`

Constraints:

- Bootstrap a system role such as `super_admin`
- System roles marked with `is_system = true` must not be deletable
- System roles may update presentation fields such as `name` and `description`, but their core semantics must remain stable

### `permissions`

Core fields:

- `id` (`BIGINT` primary key)
- `name`
- `code` (unique)
- `resource`
- `action`
- `description`
- `is_system`
- `created_at`
- `updated_at`

Permission code format should follow `resource:action`, for example:

- `user:create`
- `user:update`
- `role:assign`
- `menu:read`

### `menus`

Core fields:

- `id` (`BIGINT` primary key)
- `parent_id` (`BIGINT`, nullable)
- `name`
- `path`
- `component`
- `icon`
- `sort`
- `visible`
- `redirect`
- `meta`
- `is_system`
- `created_at`
- `updated_at`

`meta` can carry frontend-facing navigation metadata such as title, cache hints, and active menu path.

Constraints:

- Menus represent navigation structure only
- Menu trees should support nested hierarchy
- Menus marked as system menus must not be deletable in Phase 1

### Join Tables

`user_roles`

- `user_id` (`BIGINT`)
- `role_id` (`BIGINT`)

`role_permissions`

- `role_id` (`BIGINT`)
- `permission_id` (`BIGINT`)

`role_menus`

- `role_id` (`BIGINT`)
- `menu_id` (`BIGINT`)

Constraints:

- Add composite unique constraints to prevent duplicate assignments

### `refresh_sessions`

Core fields:

- `id` (`BIGINT` primary key)
- `user_id` (`BIGINT`)
- `jti` (unique)
- `refresh_token_hash`
- `issued_at`
- `expires_at`
- `revoked_at`
- `replaced_by_jti`
- `user_agent`
- `ip_address`
- `created_at`
- `updated_at`

Purpose:

- Track active refresh sessions
- Support logout and logout-all flows
- Support refresh token rotation
- Support revocation after password change, password reset, or user disable

## Token Strategy

The system uses short-lived access tokens and longer-lived refresh tokens.

Recommended defaults:

- Access token TTL: 15 minutes
- Refresh token TTL: 7 days

### Access Token

Characteristics:

- JWT
- Not persisted as an active session record
- Used to access protected APIs
- Short-lived by design

Suggested claims:

- `sub` as user ID
- `username`
- `is_superuser`
- `token_type=access`
- `exp`

### Refresh Token

Characteristics:

- JWT
- Backed by Redis session state and `refresh_sessions`
- Rotated on every successful refresh

Suggested claims:

- `sub` as user ID
- `jti`
- `token_type=refresh`
- `exp`

Refresh tokens must be validated against both cryptographic claims and server-side session state.

## Redis Session Model

Redis stores short-lived auth session state for refresh tokens.

Suggested keys:

- `auth:refresh:{jti}` for refresh session state
- `auth:user_refresh_index:{user_id}` for the set of active refresh JTIs owned by a user

Stored data should allow the backend to determine:

- Whether the refresh session exists
- Whether it has been revoked
- Which user owns it
- When it expires
- Whether it has been rotated

Redis TTL should match refresh token expiration.

## Authentication Flows

### Login

1. Accept `username` and `password`
2. Load the user
3. Reject if the user does not exist or is disabled
4. Verify the password with Argon2id
5. Issue a new access token and refresh token
6. Create a `refresh_sessions` record
7. Store refresh session state in Redis
8. Update `last_login_at`

Login response should include:

- `access_token`
- `refresh_token`
- `token_type`
- `expires_in`
- `must_change_password`

If `must_change_password = true`, the user may log in successfully, but access should be limited to safe endpoints until the password is changed.

### Protected API Access

Protected APIs validate:

- JWT signature
- Token type
- Token expiration

Then authorization dependencies validate required permissions.

If `must_change_password = true`, only these endpoints remain allowed:

- `GET /api/v1/me/profile`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`

All other protected endpoints should return `403` with a dedicated business code such as `PASSWORD_CHANGE_REQUIRED`.

### Refresh

1. Accept a refresh token
2. Validate JWT structure, signature, type, and expiration
3. Resolve `jti`
4. Check Redis and persisted session state
5. Reject if revoked, missing, expired, or already rotated
6. Issue a new access token
7. Issue a new refresh token with a new `jti`
8. Mark the previous refresh session as replaced
9. Persist the new refresh session
10. Update Redis session records

This is mandatory refresh token rotation, not optional rotation.

### Logout

Logout revokes the current refresh session:

1. Accept the current refresh token
2. Resolve its `jti`
3. Mark the session revoked in persistence
4. Remove or invalidate the Redis entry
5. Remove the `jti` from the user's refresh index

### Logout All

Logout-all revokes every active refresh session for the current user.

This flow reads the user's active refresh index from Redis and invalidates each known refresh session. Persistent state should be updated as well for auditability and consistency.

### Self Password Change

1. Require the current password
2. Verify the current password
3. Validate the new password against configured rules
4. Replace `password_hash`
5. Set `must_change_password = false`
6. Revoke the user's other refresh sessions

The current session may either remain active or be revoked as well. To keep the system behavior simple and secure in Phase 1, revoke all refresh sessions and require re-login after success.

### Admin Reset Password

1. Admin resets another user's password
2. Persist the new password hash
3. Set `must_change_password = true`
4. Revoke all active refresh sessions for that user

## Authorization Model

Authorization follows:

- User -> Role -> Permission
- Role -> Menu

Rules:

- Users do not directly hold permissions in Phase 1
- Users do not directly hold menus in Phase 1
- `is_superuser = true` implies full permission access
- The superuser should also receive the full menu tree
- A user is authorized if any assigned role grants the requested permission

FastAPI endpoints should use explicit permission guards such as:

- `require_permission("user:create")`
- `require_permission("role:update")`
- `require_permission("menu:read")`

The backend remains the final authority even if a future frontend hides buttons based on permission data.

## Current User Context

Phase 1 should expose a stable current-user contract for future frontend use.

### `GET /api/v1/me/profile`

Returns:

- User ID
- Username
- Nickname
- Email
- Phone
- `is_active`
- `is_superuser`
- `must_change_password`
- Role summary

### `GET /api/v1/me/access-context`

Returns:

- User profile summary
- Role list
- Permission code list
- Menu tree
- `must_change_password`

The backend should assemble the menu tree server-side rather than returning a flat list.

## RBAC Management APIs

### Authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`
- `POST /api/v1/auth/change-password`

### Current User

- `GET /api/v1/me/profile`
- `GET /api/v1/me/access-context`

### User Management

- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}/status`
- `POST /api/v1/users/{user_id}/reset-password`
- `PUT /api/v1/users/{user_id}/roles`

### Role Management

- `GET /api/v1/roles`
- `GET /api/v1/roles/{role_id}`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `DELETE /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`
- `PUT /api/v1/roles/{role_id}/menus`

### Permission Management

- `GET /api/v1/permissions`
- `POST /api/v1/permissions`
- `PATCH /api/v1/permissions/{permission_id}`
- `DELETE /api/v1/permissions/{permission_id}`

### Menu Management

- `GET /api/v1/menus`
- `GET /api/v1/menus/tree`
- `POST /api/v1/menus`
- `PATCH /api/v1/menus/{menu_id}`
- `DELETE /api/v1/menus/{menu_id}`

## Safety Rules and Invariants

Phase 1 should enforce these invariants:

- The bootstrap super administrator is auto-created on startup if missing
- The bootstrap password is hashed before persistence
- First login with the bootstrap account requires password change
- The last superuser cannot be deleted or stripped of superuser status
- A user cannot accidentally disable their own account through admin flows
- Disabling a user revokes all active refresh sessions
- Password change revokes all active refresh sessions
- Admin password reset revokes all active refresh sessions and forces password change
- Core system roles, permissions, and menus marked as system-managed resources must not be deletable

## Error Handling

Use a structured error response format:

- `code`
- `message`
- `details`
- `request_id`

HTTP semantics:

- `401 Unauthorized` for missing, invalid, or expired authentication
- `403 Forbidden` for authenticated users without required permission
- `403 Forbidden` with business code `PASSWORD_CHANGE_REQUIRED` when access is blocked pending password change
- `404 Not Found` for unknown resources
- `400 Bad Request` for invalid payloads or illegal transitions
- `409 Conflict` for uniqueness conflicts or protected resource operations where conflict semantics are clearer

## Logging

Use built-in Python `logging` for structured application logging.

At minimum, log:

- Login success
- Login failure
- Token refresh success
- Token refresh failure
- Logout
- Logout all
- Self password change
- Admin password reset
- User create, update, status change
- Role create, update, delete
- Permission create, update, delete
- Menu create, update, delete
- User-role assignment
- Role-permission assignment
- Role-menu assignment

Sensitive fields such as plaintext passwords and raw token values must never be logged.

## Testing Strategy

### Unit Tests

Cover:

- Argon2id hashing and verification helpers
- JWT creation and parsing
- Permission aggregation
- Menu tree assembly
- Refresh rotation logic

### Integration Tests

Cover:

- Login success and failure
- Refresh success and reuse rejection
- Logout and logout-all
- Bootstrap admin first-login forced password change
- Self password change
- Admin reset password
- User creation and role assignment
- Role-permission and role-menu assignment
- Protected route permission enforcement

### Authorization Matrix Tests

Cover:

- User without permission is rejected
- User with permission is accepted
- Superuser bypass works
- Disabled user sessions are invalidated

### Security Regression Tests

Cover:

- Bootstrap password is not stored in plaintext
- Old refresh token cannot be reused after rotation
- Password reset invalidates prior sessions
- Password change required state blocks protected management APIs

## Recommended Implementation Shape

This phase should be implemented as the standard Phase 1 backend, not a lighter auth-only skeleton and not a heavier operations-first platform.

Why this shape:

- It gives the project a complete and reusable access-control foundation
- It supports future frontend work without redesigning backend contracts
- It avoids early overreach into audit-heavy or enterprise-hardening features

Items intentionally deferred to later phases:

- Full audit log center
- Account lockout policies
- Password complexity administration
- SSO
- MFA
- Git provider integrations
- Review workflows and code intelligence modules

## Success Criteria

Phase 1 is successful when:

- The system boots and creates the initial `admin` account if it does not exist
- The initial admin can log in and is forced to change the default password
- Administrators can create and manage users, roles, permissions, and menus
- Role assignments drive both API authorization and menu visibility context
- Refresh tokens support rotation, logout, and logout-all via Redis-backed session control
- Disabled users and reset-password users lose active refresh sessions
- Future frontend work can consume stable `me` and RBAC APIs without backend redesign
