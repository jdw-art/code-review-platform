import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import * as LucideIcons from "lucide-react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  KeyRound,
  Layers,
  PlusCircle,
  ShieldCheck,
  X,
} from "lucide-react";

import {
  assignRoleMenus,
  assignRolePermissions,
  createRole,
  deleteRole,
  listMenus,
  listPermissions,
  listRoles,
  updateRole,
} from "../../features/system/api";
import { normalizeOptionalText } from "../../lib/forms/serializers";
import type { MenuNode, PermissionResponse, RoleResponse } from "../../lib/api/types";

interface RoleFormState {
  name: string;
  code: string;
  description: string;
  permission_ids: number[];
  menu_ids: number[];
}

const emptyRoleForm: RoleFormState = {
  name: "",
  code: "",
  description: "",
  permission_ids: [],
  menu_ids: [],
};

function collectMenuIds(menus?: MenuNode[] | null): number[] {
  if (menus === undefined || menus === null) {
    return [];
  }

  return menus.flatMap((item) => [item.id, ...collectMenuIds(item.children)]);
}

function flattenMenus(
  menus: MenuNode[],
  level = 0
): Array<{
  id: number;
  name: string;
  path: string;
  icon: string | null;
  level: number;
}> {
  return menus.flatMap((menu) => [
    {
      id: menu.id,
      name: menu.name,
      path: menu.path,
      icon: menu.icon,
      level,
    },
    ...flattenMenus(menu.children, level + 1),
  ]);
}

function buildRoleForm(role: RoleResponse): RoleFormState {
  return {
    name: role.name,
    code: role.code,
    description: role.description ?? "",
    permission_ids: (role.permissions ?? []).map((item) => item.id),
    menu_ids: collectMenuIds(role.menus),
  };
}

function buildRolePayload(form: RoleFormState) {
  return {
    name: form.name.trim(),
    code: form.code.trim(),
    description: normalizeOptionalText(form.description),
  };
}

function buildRoleUpdatePayload(form: RoleFormState) {
  return {
    name: form.name.trim(),
    description: normalizeOptionalText(form.description),
  };
}

function renderMenuIcon(iconName: string | null) {
  if (iconName === null) {
    return <ShieldCheck className="w-4 h-4 text-indigo-500" />;
  }

  const iconMap = LucideIcons as unknown as Record<string, typeof ShieldCheck>;
  const IconComponent = iconMap[iconName] ?? ShieldCheck;

  return <IconComponent className="w-4 h-4 text-indigo-500" />;
}

function groupPermissionsByResource(permissions: PermissionResponse[]) {
  return permissions.reduce<Record<string, PermissionResponse[]>>((groups, permission) => {
    const groupKey = permission.resource;
    const group = groups[groupKey] ?? [];
    group.push(permission);
    groups[groupKey] = group;
    return groups;
  }, {});
}

export function RoleListPage() {
  const queryClient = useQueryClient();
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [editingRole, setEditingRole] = useState<RoleResponse | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [form, setForm] = useState<RoleFormState>(emptyRoleForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: rolesPage } = useQuery({
    queryKey: ["roles", "list", currentPage, pageSize],
    queryFn: () => listRoles({ page: currentPage, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
  const { data: permissions = [] } = useQuery({
    queryKey: ["permissions", "list"],
    queryFn: () => listPermissions(),
  });
  const { data: menuTree = [] } = useQuery({
    queryKey: ["menus", "list"],
    queryFn: () => listMenus(),
  });

  const roles = rolesPage?.items ?? [];
  const menuOptions = useMemo(() => flattenMenus(menuTree), [menuTree]);
  const groupedPermissions = useMemo(
    () => Object.entries(groupPermissionsByResource(permissions)),
    [permissions]
  );

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingRole === null) {
        const createdRole = await createRole(buildRolePayload(form));

        if (form.permission_ids.length > 0) {
          await assignRolePermissions(createdRole.id, form.permission_ids);
        }

        if (form.menu_ids.length > 0) {
          await assignRoleMenus(createdRole.id, form.menu_ids);
        }

        return createdRole;
      }

      const savedRole = await updateRole(editingRole.id, buildRoleUpdatePayload(form));
      await assignRolePermissions(savedRole.id, form.permission_ids);
      await assignRoleMenus(savedRole.id, form.menu_ids);
      return savedRole;
    },
    onSuccess: async () => {
      closeModal();
      await queryClient.invalidateQueries({ queryKey: ["roles", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存角色失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (role: RoleResponse) => deleteRole(role.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["roles", "list"] });
    },
  });

  const totalRoles = rolesPage?.total ?? 0;
  const totalPages = Math.max(rolesPage?.total_pages ?? 0, 1);
  const indexOfFirstRole = totalRoles === 0 ? 0 : (currentPage - 1) * pageSize;
  const indexOfLastRole = totalRoles === 0 ? 0 : indexOfFirstRole + roles.length;
  const currentRoles = useMemo(() => roles, [roles]);

  useEffect(() => {
    if (rolesPage !== undefined && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, rolesPage, totalPages]);

  function closeModal() {
    setEditingRole(null);
    setIsCreateOpen(false);
    setForm(emptyRoleForm);
    setErrorMessage(null);
  }

  function openCreateModal() {
    setEditingRole(null);
    setIsCreateOpen(true);
    setForm(emptyRoleForm);
    setErrorMessage(null);
  }

  function openEditModal(role: RoleResponse) {
    setEditingRole(role);
    setIsCreateOpen(false);
    setForm(buildRoleForm(role));
    setErrorMessage(null);
  }

  function updateField<KeyT extends keyof RoleFormState>(
    field: KeyT,
    value: RoleFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function toggleCheckedItem(field: "permission_ids" | "menu_ids", checkedId: number) {
    setForm((current) => {
      const exists = current[field].includes(checkedId);
      return {
        ...current,
        [field]: exists
          ? current[field].filter((item) => item !== checkedId)
          : [...current[field], checkedId],
      };
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    try {
      await saveMutation.mutateAsync();
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存角色失败。");
      }
    }
  }

  async function handleDelete(role: RoleResponse) {
    if (role.is_system) {
      return;
    }

    const confirmed = window.confirm(`确认删除角色 ${role.name} 吗？`);
    if (!confirmed) {
      return;
    }

    await deleteMutation.mutateAsync(role);
  }

  const modalVisible = editingRole !== null || isCreateOpen;
  const isSystemRole = editingRole?.is_system ?? false;
  const modalTitle =
    editingRole === null
      ? "创建全新系统角色"
      : `编辑角色 - [${form.name || editingRole.name}] 权限及菜单管控分配`;

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <h2 className="sr-only">角色权限矩阵</h2>

      <div className="bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs">
        <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
          <KeyRound className="w-4 h-4 text-indigo-500 shrink-0" />
          <span>RBAC 角色权限与路由控制模块</span>
        </h3>
        <p className="text-[11px] text-slate-500 mt-0.5">
          管控系统的准入规则。数据列约束和唯一索引等已在 PostgreSQL SQL 等效实体中严格确立：
        </p>
      </div>

      <div className="space-y-6">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
            <div className="space-y-0.5">
              <h3 className="text-xs font-bold text-slate-800 font-mono uppercase">
                全局角色配置表 (roles)
              </h3>
              <p className="text-[10px] text-slate-400">
                唯一代码映射 code 关联功能权限与动态菜单路由
              </p>
            </div>

            <button
              type="button"
              onClick={openCreateModal}
              className="px-3.5 py-1.5 bg-[#0b0c16] hover:bg-[#181a2e] text-[#93c5fd] border border-[#232b4b] rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              <span>新增系统角色</span>
            </button>
          </div>

          <div className="overflow-x-auto scrollbar-none">
            <table className="w-full text-left border-collapse whitespace-nowrap text-xs">
              <thead>
                <tr className="bg-slate-50/50 text-slate-400 font-bold border-b border-slate-100">
                  <th className="py-3 px-6">ID</th>
                  <th className="py-3 px-6">角色标签 (name)</th>
                  <th className="py-3 px-6">唯一代码标识 (code)</th>
                  <th className="py-3 px-6">功能权限数</th>
                  <th className="py-3 px-6">展示菜单数</th>
                  <th className="py-3 px-6">预设系统(is_system)</th>
                  <th className="py-3 px-6">规则详情 / 描述 (description)</th>
                  <th className="py-3 px-6 text-right">管理操作</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {currentRoles.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-10 text-center text-xs text-slate-400">
                      暂无角色数据
                    </td>
                  </tr>
                ) : (
                  currentRoles.map((role) => {
                    const permissionCount = (role.permissions ?? []).length;
                    const menuCount = collectMenuIds(role.menus).length;

                    return (
                      <tr key={role.id} className="hover:bg-slate-50/40">
                        <td className="py-3.5 px-6 font-mono text-slate-500">{role.id}</td>
                        <td className="py-3.5 px-6 font-bold text-slate-800">{role.name}</td>
                        <td className="py-3.5 px-6 font-semibold font-mono text-indigo-700">
                          <span className="bg-slate-100 px-2 py-0.5 rounded text-[10.5px]">
                            {role.code}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono">
                          <span className="bg-emerald-50 text-emerald-800 border border-emerald-100 px-2 py-0.5 rounded font-bold text-[10.5px]">
                            {permissionCount} / {permissions.length || 38} 项
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono">
                          <span className="bg-blue-50 text-blue-800 border border-blue-100 px-2 py-0.5 rounded font-bold text-[10.5px]">
                            {menuCount} / {menuOptions.length || 11} 个
                          </span>
                        </td>
                        <td className="py-3.5 px-6">
                          <span
                            className={`px-2 py-0.5 rounded-sm font-bold text-[9px] uppercase ${
                              role.is_system
                                ? "bg-indigo-50 text-indigo-600 border border-indigo-100"
                                : "bg-slate-100 text-slate-400"
                            }`}
                          >
                            {role.is_system ? "SYSTEM" : "CUSTOM"}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 text-slate-600 max-w-xs font-light text-[11.5px] whitespace-normal leading-relaxed">
                          {role.description ?? "未填写角色说明"}
                        </td>
                        <td className="py-3.5 px-6 text-right space-x-2">
                          <button
                            type="button"
                            onClick={() => openEditModal(role)}
                            className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 border border-slate-200 rounded-lg text-[11px] font-semibold transition-all shadow-3xs cursor-pointer"
                          >
                            控制分配
                          </button>

                          <button
                            type="button"
                            onClick={() => void handleDelete(role)}
                            disabled={role.is_system || deleteMutation.isPending}
                            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all ${
                              role.is_system
                                ? "bg-slate-50 text-slate-300 border-slate-100 cursor-not-allowed"
                                : "bg-red-50 hover:bg-red-100 text-red-600 border-red-200 cursor-pointer"
                            }`}
                          >
                            删除
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {totalRoles > 0 ? (
            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
              <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                <div>
                  显示 <span className="font-semibold text-slate-800">{indexOfFirstRole + 1}</span>{" "}
                  至{" "}
                  <span className="font-semibold text-slate-800">
                    {indexOfLastRole}
                  </span>{" "}
                  条，共 <span className="font-semibold text-slate-800">{totalRoles}</span> 个角色
                </div>

                <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                  <span>每页显示:</span>
                  <select
                    value={pageSize}
                    onChange={(event) => {
                      setPageSize(Number(event.target.value));
                      setCurrentPage(1);
                    }}
                    className="border border-slate-200 bg-slate-50 text-slate-800 rounded-md px-1.5 py-0.5 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
                  >
                    <option value={3}>3 条</option>
                    <option value={5}>5 条</option>
                    <option value={10}>10 条</option>
                    <option value={20}>20 条</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage((page) => Math.max(page - 1, 1))}
                  disabled={currentPage === 1}
                  className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>上一页</span>
                </button>

                <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                  <span className="font-bold text-indigo-600">{currentPage}</span>
                  <span className="text-slate-300">/</span>
                  <span>{totalPages}</span>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentPage((page) => Math.min(page + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
                >
                  <span>下一页</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <AnimatePresence>
        {modalVisible ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.button
              type="button"
              aria-label="关闭角色编辑弹窗"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeModal}
              className="absolute inset-0 bg-slate-900/45 backdrop-blur-xs"
            />

            <motion.div
              role="dialog"
              aria-modal="true"
              initial={{ scale: 0.96, y: 12, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.96, y: 12, opacity: 0 }}
              transition={{ type: "spring", duration: 0.35, bounce: 0.1 }}
              className="relative w-full max-w-4xl bg-white rounded-2xl border border-slate-200/80 shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]"
            >
              <div className="px-6 py-4.5 border-b border-slate-100 flex justify-between items-center bg-slate-50/65">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <h3 className="text-sm font-bold text-slate-800">{modalTitle}</h3>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-normal">
                    维护该系统安全角色的元信息，并精准定制其受控的 38 项核心功能点与 11 个左侧导航菜单
                  </p>
                </div>

                <button
                  type="button"
                  onClick={closeModal}
                  className="p-1.5 hover:bg-slate-100 text-slate-400 hover:text-slate-600 rounded-lg transition-all cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="contents">
                <div className="p-6 space-y-6 overflow-y-auto max-h-[65vh] scrollbar-thin text-left">
                  {errorMessage ? (
                    <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-red-700 text-xs font-semibold flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                      <span>{errorMessage}</span>
                    </div>
                  ) : null}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label htmlFor="role-name" className="text-[10.5px] font-bold text-slate-700 block">
                        角色名称 (name)
                      </label>
                      <input
                        id="role-name"
                        aria-label="角色名称 (name)"
                        type="text"
                        required
                        value={form.name}
                        onChange={(event) => updateField("name", event.target.value)}
                        placeholder="例如：高级审查官"
                        className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all font-semibold"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label htmlFor="role-code" className="text-[10.5px] font-bold text-slate-700 block">
                        唯一英文代码标识 (code)
                      </label>
                      <input
                        id="role-code"
                        aria-label="唯一英文代码标识 (code)"
                        type="text"
                        required
                        value={form.code}
                        disabled={isSystemRole}
                        onChange={(event) => updateField("code", event.target.value)}
                        placeholder="例如：SENIOR_REVIEWER"
                        className={`w-full px-3.5 py-2.5 border rounded-xl text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all font-mono font-bold uppercase ${
                          isSystemRole
                            ? "bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed select-all"
                            : "bg-slate-50 border-slate-200 focus:bg-white text-indigo-700"
                        }`}
                      />
                    </div>

                    <div className="md:col-span-2 space-y-1.5">
                      <label htmlFor="role-description" className="text-[10.5px] font-bold text-slate-700 block">
                        职责要旨及描述说明 (description)
                      </label>
                      <textarea
                        id="role-description"
                        aria-label="职责要旨及描述说明 (description)"
                        rows={2}
                        value={form.description}
                        onChange={(event) => updateField("description", event.target.value)}
                        placeholder="简述该角色的工作内容与安全范围要求，对运营人员可见。"
                        className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all leading-relaxed font-light"
                      />
                    </div>
                  </div>

                  <div className="border-t border-slate-100 pt-5 space-y-3">
                    <div className="flex justify-between items-center bg-slate-50/70 p-3 rounded-xl border border-slate-200">
                      <div className="space-y-0.5">
                        <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                          <Layers className="w-4 h-4 text-indigo-500" />
                          <span>1. 后台左侧系统菜单分配</span>
                        </label>
                        <p className="text-[10px] text-slate-400">
                          勾选本角色在左侧 Sidebar 导航区中有权点击和访问的页面模块列表
                        </p>
                      </div>

                      <div className="space-x-1.5">
                        <button
                          type="button"
                          onClick={() => updateField("menu_ids", menuOptions.map((item) => item.id))}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-indigo-600 shadow-3xs cursor-pointer"
                        >
                          集成全选
                        </button>
                        <button
                          type="button"
                          onClick={() => updateField("menu_ids", [])}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-slate-600 shadow-3xs cursor-pointer"
                        >
                          全部排空
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
                      {menuOptions.length === 0 ? (
                        <p className="text-[11px] text-slate-400">暂无可分配菜单</p>
                      ) : (
                        menuOptions.map((menu) => {
                          const isSelected = form.menu_ids.includes(menu.id);

                          return (
                            <label
                              key={menu.id}
                              className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer select-none ${
                                isSelected
                                  ? "bg-indigo-50/50 border-indigo-200 ring-1 ring-indigo-500/5"
                                  : "bg-slate-50/30 border-slate-200/80 hover:bg-slate-50/50"
                              }`}
                              style={{ marginLeft: `${menu.level * 10}px` }}
                            >
                              <input
                                type="checkbox"
                                aria-label={`菜单 ${menu.name}`}
                                checked={isSelected}
                                onChange={() => toggleCheckedItem("menu_ids", menu.id)}
                                className="w-4 h-4 text-indigo-700 border-slate-300 focus:ring-indigo-500 rounded cursor-pointer"
                              />

                              <div className="flex items-center gap-2 font-medium">
                                <span className="p-1.5 bg-white border border-slate-200 rounded-lg shadow-3xs">
                                  {renderMenuIcon(menu.icon)}
                                </span>
                                <div className="space-y-0.5">
                                  <span className="text-xs font-bold text-slate-800 block">
                                    {menu.name}
                                  </span>
                                  <span className="text-[9.5px] font-mono text-slate-400 block">
                                    {menu.path}
                                  </span>
                                </div>
                              </div>
                            </label>
                          );
                        })
                      )}
                    </div>
                  </div>

                  <div className="border-t border-slate-100 pt-5 space-y-4">
                    <div className="flex justify-between items-center bg-slate-50/70 p-3 rounded-xl border border-slate-200">
                      <div className="space-y-0.5">
                        <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                          <ShieldCheck className="w-4 h-4 text-emerald-500" />
                          <span>2. 后台 38 项精细功能点准入权限分配</span>
                        </label>
                        <p className="text-[10px] text-slate-400">
                          基于 resource:action 颗粒度控制后台数据查询、创建、编辑与路由跳转能力
                        </p>
                      </div>

                      <div className="space-x-1.5">
                        <button
                          type="button"
                          onClick={() => updateField("permission_ids", permissions.map((item) => item.id))}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-emerald-600 shadow-3xs cursor-pointer"
                        >
                          权限全选
                        </button>
                        <button
                          type="button"
                          onClick={() => updateField("permission_ids", [])}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-bold text-slate-600 shadow-3xs cursor-pointer"
                        >
                          全部排空
                        </button>
                      </div>
                    </div>

                    <div className="space-y-4">
                      {groupedPermissions.length === 0 ? (
                        <p className="text-[11px] text-slate-400">暂无可分配权限</p>
                      ) : (
                        groupedPermissions.map(([resource, items]) => (
                          <div key={resource} className="rounded-xl border border-slate-200 bg-slate-50/30 p-3.5 space-y-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-[11px] font-bold text-slate-800 uppercase">
                                  {resource}
                                </p>
                                <p className="text-[10px] text-slate-400 font-mono">
                                  {items.length} 项权限定义
                                </p>
                              </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                              {items.map((permission) => {
                                const isSelected = form.permission_ids.includes(permission.id);

                                return (
                                  <label
                                    key={permission.id}
                                    className={`flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer select-none ${
                                      isSelected
                                        ? "bg-emerald-50/60 border-emerald-200 ring-1 ring-emerald-500/5"
                                        : "bg-white border-slate-200 hover:bg-slate-50/50"
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      aria-label={`权限 ${permission.code}`}
                                      checked={isSelected}
                                      onChange={() => toggleCheckedItem("permission_ids", permission.id)}
                                      className="mt-0.5 w-4 h-4 text-emerald-600 border-slate-300 focus:ring-emerald-500 rounded cursor-pointer"
                                    />

                                    <div className="space-y-0.5">
                                      <div className="text-xs font-bold text-slate-800 flex items-center gap-2">
                                        <span>{permission.name}</span>
                                        <span className="text-[9px] font-mono text-slate-400 bg-slate-100 px-1 py-0.2 rounded font-semibold">
                                          {permission.code}
                                        </span>
                                      </div>
                                      <p className="text-[10px] text-slate-500 leading-relaxed">
                                        {permission.description ?? "未填写权限说明"}
                                      </p>
                                    </div>
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <div className="px-6 py-4.5 border-t border-slate-100 bg-slate-50/30 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="px-4 py-2 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-200 text-slate-600 text-xs font-semibold rounded-xl transition-all cursor-pointer"
                  >
                    取消
                  </button>

                  <button
                    type="submit"
                    disabled={saveMutation.isPending}
                    className="px-5 py-2.5 bg-[#0b0c16] text-[#93c5fd] hover:bg-[#121424] active:bg-[#06070c] border border-[#2b3558] text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    保存权限配置
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
