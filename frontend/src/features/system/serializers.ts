import type {
  AuditLogResponse,
  PermissionResponse,
  RoleResponse,
  UserResponse,
} from "../../lib/api/types";

export function toConsoleUser(user: UserResponse) {
  return {
    id: user.id,
    username: user.username,
    nickname: user.nickname,
    email: user.email,
    enabled: user.is_active,
    isSuperuser: user.is_superuser,
    roles: user.roles.map((role) => role.name),
  };
}

export function toConsoleRole(role: RoleResponse) {
  return {
    id: role.id,
    name: role.name,
    code: role.code,
    description: role.description,
    isSystem: role.is_system,
    permissionCount: role.permissions.length,
    menuCount: role.menus.length,
  };
}

export function toConsolePermission(permission: PermissionResponse) {
  return {
    id: permission.id,
    name: permission.name,
    code: permission.code,
    resource: permission.resource,
    action: permission.action,
    isSystem: permission.is_system,
  };
}

export function toConsoleAuditLog(log: AuditLogResponse) {
  return {
    id: log.id,
    actor: log.username_snapshot ?? "system",
    action: log.action,
    resourceType: log.resource_type,
    result: log.result,
    createdAt: log.created_at,
  };
}
