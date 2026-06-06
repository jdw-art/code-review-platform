import { http } from "../../lib/api/http";
import type {
  AuditLogResponse,
  MenuNode,
  PageResponse,
  PermissionResponse,
  RoleResponse,
  UserResponse,
} from "../../lib/api/types";

export interface UserCreatePayload {
  username: string;
  password: string;
  nickname: string | null;
  email: string | null;
  phone: string | null;
  is_superuser: boolean;
  role_ids: number[];
}

export interface UserUpdatePayload {
  nickname: string | null;
  email: string | null;
  phone: string | null;
  is_superuser: boolean;
}

export interface RoleCreatePayload {
  name: string;
  code: string;
  description: string | null;
}

export interface RoleUpdatePayload {
  name: string;
  description: string | null;
}

/**
 * 查询后台审计日志列表。
 */
export async function listAuditLogs() {
  const response = await http.get<PageResponse<AuditLogResponse>>("/audit-logs", {
    params: { page: 1, page_size: 20 },
  });
  return response.data;
}

/**
 * 清理业务审计日志，保留系统安全日志。
 */
export async function purgeAuditLogs() {
  const response = await http.post<{ purged_count: number }>("/audit-logs/purge");
  return response.data;
}

/**
 * 查询系统用户列表。
 */
export async function listUsers() {
  const response = await http.get<UserResponse[]>("/users");
  return response.data;
}

/**
 * 创建后台用户。
 */
export async function createUser(payload: UserCreatePayload) {
  const response = await http.post<UserResponse>("/users", payload);
  return response.data;
}

/**
 * 更新后台用户资料。
 */
export async function updateUser(userId: number, payload: UserUpdatePayload) {
  const response = await http.patch<UserResponse>(`/users/${userId}`, payload);
  return response.data;
}

/**
 * 删除后台用户。
 */
export async function deleteUser(userId: number) {
  await http.delete(`/users/${userId}`);
}

/**
 * 更新后台用户启停状态。
 */
export async function updateUserStatus(userId: number, isActive: boolean) {
  const response = await http.patch<UserResponse>(`/users/${userId}/status`, {
    is_active: isActive,
  });
  return response.data;
}

/**
 * 管理员重置后台用户密码。
 */
export async function resetUserPassword(userId: number, newPassword: string) {
  await http.post(`/users/${userId}/reset-password`, {
    new_password: newPassword,
  });
}

/**
 * 覆盖后台用户角色集合。
 */
export async function assignUserRoles(userId: number, roleIds: number[]) {
  const response = await http.put<UserResponse>(`/users/${userId}/roles`, {
    role_ids: roleIds,
  });
  return response.data;
}

/**
 * 查询系统角色列表。
 */
export async function listRoles() {
  const response = await http.get<RoleResponse[]>("/roles");
  return response.data;
}

/**
 * 创建角色。
 */
export async function createRole(payload: RoleCreatePayload) {
  const response = await http.post<RoleResponse>("/roles", payload);
  return response.data;
}

/**
 * 更新角色基础信息。
 */
export async function updateRole(roleId: number, payload: RoleUpdatePayload) {
  const response = await http.patch<RoleResponse>(`/roles/${roleId}`, payload);
  return response.data;
}

/**
 * 删除角色。
 */
export async function deleteRole(roleId: number) {
  await http.delete(`/roles/${roleId}`);
}

/**
 * 覆盖角色权限集合。
 */
export async function assignRolePermissions(roleId: number, permissionIds: number[]) {
  const response = await http.put<RoleResponse>(`/roles/${roleId}/permissions`, {
    permission_ids: permissionIds,
  });
  return response.data;
}

/**
 * 覆盖角色菜单集合。
 */
export async function assignRoleMenus(roleId: number, menuIds: number[]) {
  const response = await http.put<RoleResponse>(`/roles/${roleId}/menus`, {
    menu_ids: menuIds,
  });
  return response.data;
}

/**
 * 查询权限定义列表。
 */
export async function listPermissions() {
  const response = await http.get<PermissionResponse[]>("/permissions");
  return response.data;
}

/**
 * 查询菜单平铺列表。
 */
export async function listMenus() {
  const response = await http.get<MenuNode[]>("/menus");
  return response.data;
}
