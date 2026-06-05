import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { PageCard } from "../../components/common/PageCard";
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

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";
const sectionTitleClassName = "text-sm font-semibold text-slate-900";

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

function buildRoleForm(row: RoleResponse): RoleFormState {
  const permissions = row.permissions ?? [];
  const menus = row.menus ?? [];

  return {
    name: row.name,
    code: row.code,
    description: row.description ?? "",
    permission_ids: permissions.map((item) => item.id),
    menu_ids: collectMenuIds(menus),
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

function collectMenuIds(menus: MenuNode[]): number[] {
  return menus.flatMap((item) => [item.id, ...collectMenuIds(item.children)]);
}

function flattenMenus(
  menus: MenuNode[],
  level = 0
): Array<{ id: number; name: string; path: string; level: number; is_system: boolean }> {
  return menus.flatMap((item) => [
    {
      id: item.id,
      name: item.name,
      path: item.path,
      level,
      is_system: item.is_system,
    },
    ...flattenMenus(item.children, level + 1),
  ]);
}

function SystemBadge({ value }: { value: boolean }) {
  return (
    <span
      className={[
        "inline-flex rounded-full border px-3 py-1 text-xs font-medium",
        value
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-slate-200 bg-slate-50 text-slate-600",
      ].join(" ")}
    >
      {value ? "系统角色" : "普通角色"}
    </span>
  );
}

/**
 * 角色管理页补齐 CRUD 与权限/菜单分配，方便管理员直接维护 RBAC 配置。
 */
export function RoleListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleResponse | null>(null);
  const [form, setForm] = useState<RoleFormState>(emptyRoleForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["roles", "list"],
    queryFn: () => listRoles(),
  });
  const { data: permissions = [] } = useQuery({
    queryKey: ["permissions", "list"],
    queryFn: () => listPermissions(),
  });
  const { data: menuTree = [] } = useQuery({
    queryKey: ["menus", "list"],
    queryFn: () => listMenus(),
  });

  const menuOptions = flattenMenus(menuTree);

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
      setDrawerOpen(false);
      setEditingRole(null);
      setForm(emptyRoleForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["roles", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存角色失败。");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (row: RoleResponse) => deleteRole(row.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["roles", "list"] });
    },
  });

  function openCreateDrawer() {
    setEditingRole(null);
    setForm(emptyRoleForm);
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: RoleResponse) {
    setEditingRole(row);
    setForm(buildRoleForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
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

  function toggleCheckedItem(
    field: "permission_ids" | "menu_ids",
    checkedId: number
  ) {
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

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
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

  async function handleDelete(row: RoleResponse) {
    if (row.is_system) {
      return;
    }
    const confirmed = window.confirm(`确认删除角色 ${row.name} 吗？`);
    if (!confirmed) {
      return;
    }
    await deleteMutation.mutateAsync(row);
  }

  const roleColumns: DataTableColumn<RoleResponse>[] = [
    {
      key: "name",
      title: "角色名称",
    },
    {
      key: "code",
      title: "角色编码",
    },
    {
      key: "description",
      title: "描述",
      render: (row) => row.description ?? "-",
    },
    {
      key: "permissions",
      title: "权限数",
      render: (row) => (row.permissions ?? []).length,
    },
    {
      key: "menus",
      title: "菜单数",
      render: (row) => collectMenuIds(row.menus ?? []).length,
    },
    {
      key: "is_system",
      title: "角色类型",
      render: (row) => <SystemBadge value={row.is_system} />,
    },
    {
      key: "actions",
      title: "操作",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => openEditDrawer(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            编辑
          </button>
          {row.is_system ? (
            <span className="inline-flex items-center rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-400">
              不可删除
            </span>
          ) : (
            <button
              type="button"
              onClick={() => void handleDelete(row)}
              className="rounded-full border border-rose-200 px-3 py-1 text-xs text-rose-700 transition hover:bg-rose-50"
            >
              删除
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageCard
        title="角色管理"
        description="查看角色定义、权限规模以及菜单可见范围。"
        actions={
          <button
            type="button"
            onClick={openCreateDrawer}
            className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            新建角色
          </button>
        }
      >
        <DataTable
          columns={roleColumns}
          rows={data ?? []}
          loading={isLoading}
          emptyText="暂无角色数据"
        />
      </PageCard>

      <DrawerForm
        open={drawerOpen}
        title={editingRole === null ? "创建角色" : "编辑角色"}
        description="维护角色基础信息，并直接分配权限与菜单。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-6" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            角色名称
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            角色编码
            <input
              value={form.code}
              onChange={(event) => updateField("code", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            描述
            <textarea
              value={form.description}
              onChange={(event) => updateField("description", event.target.value)}
              className={`${inputClassName} min-h-24`}
            />
          </label>

          <section className="space-y-3">
            <div>
              <h3 className={sectionTitleClassName}>权限分配</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                选择该角色可以访问的资源操作。
              </p>
            </div>
            <div className="grid gap-3 rounded-2xl border border-slate-200 p-4 md:grid-cols-2">
              {permissions.length === 0 ? (
                <p className="text-sm text-slate-500">暂无可分配权限</p>
              ) : (
                permissions.map((item: PermissionResponse) => (
                  <label
                    key={item.id}
                    className="flex items-start gap-3 rounded-2xl border border-slate-100 px-3 py-3 text-sm text-slate-700"
                  >
                    <input
                      type="checkbox"
                      aria-label={`权限 ${item.code}`}
                      checked={form.permission_ids.includes(item.id)}
                      onChange={() => toggleCheckedItem("permission_ids", item.id)}
                    />
                    <span>
                      <span className="block font-medium text-slate-900">
                        {item.name}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {item.code}
                      </span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </section>

          <section className="space-y-3">
            <div>
              <h3 className={sectionTitleClassName}>菜单分配</h3>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                选择角色在后台中可见的菜单入口。
              </p>
            </div>
            <div className="grid gap-3 rounded-2xl border border-slate-200 p-4">
              {menuOptions.length === 0 ? (
                <p className="text-sm text-slate-500">暂无可分配菜单</p>
              ) : (
                menuOptions.map((item) => (
                  <label
                    key={item.id}
                    className="flex items-start gap-3 rounded-2xl border border-slate-100 px-3 py-3 text-sm text-slate-700"
                    style={{ paddingLeft: `${item.level * 20 + 12}px` }}
                  >
                    <input
                      type="checkbox"
                      aria-label={`菜单 ${item.name}`}
                      checked={form.menu_ids.includes(item.id)}
                      onChange={() => toggleCheckedItem("menu_ids", item.id)}
                    />
                    <span>
                      <span className="block font-medium text-slate-900">
                        {item.name}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {item.path || "/"}
                      </span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </section>

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saveMutation.isPending ? "保存中..." : "保存角色"}
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
