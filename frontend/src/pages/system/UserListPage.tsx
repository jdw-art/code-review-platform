import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { ConsolePageHeader } from "../../components/console/ConsolePageHeader";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  assignUserRoles,
  createUser,
  deleteUser,
  listRoles,
  listUsers,
  updateUser,
  updateUserStatus,
} from "../../features/system/api";
import { normalizeOptionalText } from "../../lib/forms/serializers";
import type { RoleResponse, UserResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white disabled:cursor-not-allowed disabled:bg-slate-100";
const labelClassName = "block text-sm font-medium text-slate-700";

interface UserFormState {
  username: string;
  password: string;
  nickname: string;
  email: string;
  phone: string;
  is_superuser: boolean;
  role_ids: number[];
}

const emptyUserForm: UserFormState = {
  username: "",
  password: "",
  nickname: "",
  email: "",
  phone: "",
  is_superuser: false,
  role_ids: [],
};

function buildCreatePayload(form: UserFormState) {
  return {
    username: form.username.trim(),
    password: form.password.trim(),
    nickname: normalizeOptionalText(form.nickname),
    email: normalizeOptionalText(form.email),
    phone: normalizeOptionalText(form.phone),
    is_superuser: form.is_superuser,
    role_ids: form.role_ids,
  };
}

function buildUpdatePayload(form: UserFormState) {
  return {
    nickname: normalizeOptionalText(form.nickname),
    email: normalizeOptionalText(form.email),
    phone: normalizeOptionalText(form.phone),
    is_superuser: form.is_superuser,
  };
}

function buildUserForm(row: UserResponse): UserFormState {
  const roles = row.roles ?? [];

  return {
    username: row.username,
    password: "",
    nickname: row.nickname ?? "",
    email: row.email ?? "",
    phone: row.phone ?? "",
    is_superuser: row.is_superuser,
    role_ids: roles.map((role) => role.id),
  };
}

function RoleSelection({
  roles,
  selectedRoleIds,
  onToggle,
}: {
  roles: RoleResponse[];
  selectedRoleIds: number[];
  onToggle: (roleId: number) => void;
}) {
  if (roles.length === 0) {
    return <p className="mt-2 text-sm text-slate-500">暂无可分配角色。</p>;
  }

  return (
    <div className="mt-3 grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      {roles.map((role) => {
        const checked = selectedRoleIds.includes(role.id);
        return (
          <label
            key={role.id}
            className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
          >
            <input
              type="checkbox"
              checked={checked}
              aria-label={`角色 ${role.name}`}
              onChange={() => onToggle(role.id)}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
            />
            <span>
              <span className="font-medium text-slate-900">{role.name}</span>
              <span className="ml-2 text-xs uppercase tracking-[0.18em] text-slate-400">
                {role.code}
              </span>
              <span className="mt-1 block text-xs leading-5 text-slate-500">
                {role.description ?? "未填写角色说明"}
              </span>
            </span>
          </label>
        );
      })}
    </div>
  );
}

/**
 * 用户管理页补齐新增、编辑、删除、角色分配与启停操作，方便直接维护后台账号。
 */
export function UserListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const [form, setForm] = useState<UserFormState>(emptyUserForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["users", "list"],
    queryFn: () => listUsers(),
  });
  const { data: roles = [] } = useQuery({
    queryKey: ["roles", "list"],
    queryFn: () => listRoles(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingUser === null) {
        return createUser(buildCreatePayload(form));
      }

      await updateUser(editingUser.id, buildUpdatePayload(form));
      return assignUserRoles(editingUser.id, form.role_ids);
    },
    onSuccess: async () => {
      setDrawerOpen(false);
      setEditingUser(null);
      setForm(emptyUserForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["users", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存用户失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: UserResponse) => updateUserStatus(row.id, !row.is_active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["users", "list"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (row: UserResponse) => deleteUser(row.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["users", "list"] });
    },
  });

  function openCreateDrawer() {
    setEditingUser(null);
    setForm(emptyUserForm);
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: UserResponse) {
    setEditingUser(row);
    setForm(buildUserForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function updateField<KeyT extends keyof UserFormState>(
    field: KeyT,
    value: UserFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function toggleRole(roleId: number) {
    setForm((current) => ({
      ...current,
      role_ids: current.role_ids.includes(roleId)
        ? current.role_ids.filter((item) => item !== roleId)
        : [...current.role_ids, roleId],
    }));
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
        setErrorMessage("保存用户失败。");
      }
    }
  }

  async function handleDelete(row: UserResponse) {
    if (!window.confirm(`确认删除用户 ${row.username} 吗？`)) {
      return;
    }
    await deleteMutation.mutateAsync(row);
  }

  const userColumns: DataTableColumn<UserResponse>[] = [
    {
      key: "username",
      title: "用户名",
    },
    {
      key: "nickname",
      title: "昵称",
      render: (row) => row.nickname ?? "-",
    },
    {
      key: "email",
      title: "邮箱",
      render: (row) => row.email ?? "-",
    },
    {
      key: "roles",
      title: "角色",
      render: (row) => {
        const roles = row.roles ?? [];
        return roles.length > 0 ? roles.map((role) => role.name).join("、") : "未分配角色";
      },
    },
    {
      key: "is_superuser",
      title: "超级管理员",
      render: (row) => (row.is_superuser ? "是" : "否"),
    },
    {
      key: "is_active",
      title: "状态",
      render: (row) => <StatusBadge value={row.is_active} />,
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
          <button
            type="button"
            onClick={() => void statusMutation.mutateAsync(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            {row.is_active ? "停用" : "启用"}
          </button>
          <button
            type="button"
            onClick={() => void handleDelete(row)}
            className="rounded-full border border-rose-200 px-3 py-1 text-xs text-rose-700 transition hover:border-rose-300 hover:bg-rose-50"
          >
            删除
          </button>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="space-y-4 rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-sky-50/50 p-4 shadow-sm">
        <ConsolePageHeader
          title="系统用户中心"
          description="在此维护后台账号、超级管理员标记与角色分配。"
          action={
            <button
              type="button"
              onClick={openCreateDrawer}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              新建用户
            </button>
          }
        />
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <DataTable
            columns={userColumns}
            rows={data ?? []}
            loading={isLoading}
            emptyText="暂无用户数据"
          />
        </section>
      </div>

      <DrawerForm
        open={drawerOpen}
        title={editingUser === null ? "创建用户" : "编辑用户"}
        description="维护用户基础资料、超级管理员标记和角色分配。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-5" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            用户名
            <input
              value={form.username}
              disabled={editingUser !== null}
              onChange={(event) => updateField("username", event.target.value)}
              className={inputClassName}
            />
          </label>

          {editingUser === null ? (
            <label className={labelClassName}>
              初始密码
              <input
                type="password"
                value={form.password}
                onChange={(event) => updateField("password", event.target.value)}
                className={inputClassName}
              />
            </label>
          ) : null}

          <label className={labelClassName}>
            昵称
            <input
              value={form.nickname}
              onChange={(event) => updateField("nickname", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            邮箱
            <input
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            手机号
            <input
              value={form.phone}
              onChange={(event) => updateField("phone", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_superuser}
              onChange={(event) => updateField("is_superuser", event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
            />
            <span>设为超级管理员</span>
          </label>

          <div>
            <p className={labelClassName}>角色分配</p>
            <RoleSelection
              roles={roles}
              selectedRoleIds={form.role_ids}
              onToggle={toggleRole}
            />
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-200 pt-5">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="submit"
              className="rounded-full bg-slate-950 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              保存用户
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
