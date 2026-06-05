import type {
  AuditLogResponse,
  PermissionResponse,
  RoleResponse,
  UserResponse,
} from "../../lib/api/types";

export function toConsoleUser(user: UserResponse) {
  const roles = Array.isArray(user.roles) ? user.roles : [];

  return {
    id: user.id,
    username: user.username,
    nickname: user.nickname,
    email: user.email,
    enabled: user.is_active,
    isSuperuser: user.is_superuser,
    roles: roles
      .map((role) => role?.name)
      .filter((roleName): roleName is string => typeof roleName === "string"),
  };
}

export function toConsoleRole(role: RoleResponse) {
  const permissions = Array.isArray(role.permissions) ? role.permissions : [];
  const menus = Array.isArray(role.menus) ? role.menus : [];

  return {
    id: role.id,
    name: role.name,
    code: role.code,
    description: role.description,
    isSystem: role.is_system,
    permissionCount: permissions.length,
    menuCount: menus.length,
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
