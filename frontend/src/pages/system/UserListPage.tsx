import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, KeyRound, Mail, X } from "lucide-react";

import {
  assignUserRoles,
  listRoles,
  listUsers,
  updateUser,
  updateUserStatus,
} from "../../features/system/api";
import { normalizeOptionalText } from "../../lib/forms/serializers";
import type { RoleResponse, UserResponse } from "../../lib/api/types";

interface UserFormState {
  username: string;
  nickname: string;
  email: string;
  phone: string;
  is_superuser: boolean;
  role_ids: number[];
}

const emptyUserForm: UserFormState = {
  username: "",
  nickname: "",
  email: "",
  phone: "",
  is_superuser: false,
  role_ids: [],
};

function buildUserForm(row: UserResponse): UserFormState {
  return {
    username: row.username,
    nickname: row.nickname ?? "",
    email: row.email ?? "",
    phone: row.phone ?? "",
    is_superuser: row.is_superuser,
    role_ids: (row.roles ?? []).map((role) => role.id),
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

function getRolesDisplay(roles?: UserResponse["roles"]) {
  if (roles === undefined || roles === null || roles.length === 0) {
    return "Normal User";
  }

  return roles.map((role) => role.name).join(", ");
}

export function UserListPage() {
  const queryClient = useQueryClient();
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const [form, setForm] = useState<UserFormState>(emptyUserForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: usersPage } = useQuery({
    queryKey: ["users", "list", currentPage, pageSize],
    queryFn: () => listUsers({ page: currentPage, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
  const { data: rolesPage } = useQuery({
    queryKey: ["roles", "options", 1, 100],
    queryFn: () => listRoles({ page: 1, page_size: 100 }),
  });
  const users = usersPage?.items ?? [];
  const roles = rolesPage?.items ?? [];

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingUser === null) {
        throw new Error("当前未选择用户。");
      }

      await updateUser(editingUser.id, buildUpdatePayload(form));
      return assignUserRoles(editingUser.id, form.role_ids);
    },
    onSuccess: async () => {
      closeModal();
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

  const totalUsers = usersPage?.total ?? 0;
  const totalPages = Math.max(usersPage?.total_pages ?? 0, 1);
  const indexOfFirstUser = totalUsers === 0 ? 0 : (currentPage - 1) * pageSize;
  const indexOfLastUser = totalUsers === 0 ? 0 : indexOfFirstUser + users.length;
  const currentUsers = useMemo(() => users, [users]);
  const activeUsers = useMemo(
    () => users.filter((user) => user.is_active).length,
    [users]
  );

  useEffect(() => {
    if (usersPage !== undefined && currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages, usersPage]);

  function closeModal() {
    setEditingUser(null);
    setForm(emptyUserForm);
    setErrorMessage(null);
  }

  function openEditModal(row: UserResponse) {
    setEditingUser(row);
    setForm(buildUserForm(row));
    setErrorMessage(null);
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
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

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <h2 className="sr-only">系统用户中心</h2>

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
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden w-full">
          <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
            <div className="space-y-0.5">
              <h3 className="text-xs font-bold text-slate-800 font-mono uppercase">
                用户管理
              </h3>
              <p className="text-[10px] text-slate-400">
                查看系统用户账号、角色分配和启用状态
              </p>
            </div>
            <span className="text-[10px] text-indigo-600 font-semibold font-mono bg-indigo-50 border border-indigo-100/50 px-2 py-0.5 rounded-sm">
              Active Users ({activeUsers})
            </span>
          </div>

          <div className="overflow-x-auto scrollbar-none">
            <table className="w-full text-left border-collapse whitespace-nowrap text-xs">
              <thead>
                <tr className="bg-slate-50/50 text-slate-400 font-bold border-b border-slate-100">
                  <th className="py-3 px-6">用户名</th>
                  <th className="py-3 px-6">昵称</th>
                  <th className="py-3 px-6">邮箱</th>
                  <th className="py-3 px-6">角色</th>
                  <th className="py-3 px-6">超管</th>
                  <th className="py-3 px-6">状态</th>
                  <th className="py-3 px-6 text-right">操作</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {currentUsers.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-10 text-center text-xs text-slate-400">
                      暂无用户数据
                    </td>
                  </tr>
                ) : (
                  currentUsers.map((user) => {
                    const isSelected = editingUser?.id === user.id;

                    return (
                      <tr
                        key={user.id}
                        className={`hover:bg-slate-50/40 transition-colors ${
                          isSelected ? "bg-indigo-50/50 hover:bg-indigo-50/70" : ""
                        }`}
                      >
                        <td className="py-3.5 px-6 font-semibold font-mono text-slate-900">
                          {user.username}
                        </td>
                        <td className="py-3.5 px-6 text-slate-600 font-medium">
                          {user.nickname || "—"}
                        </td>
                        <td className="py-3.5 px-6 text-slate-500 font-mono text-[11px]">
                          {user.email ? (
                            <span className="flex items-center gap-1.5">
                              <Mail className="w-3 h-3 text-slate-300" />
                              <span>{user.email}</span>
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-6 text-slate-700 font-medium">
                          <span className="bg-indigo-50/60 text-indigo-700 px-2.5 py-0.5 rounded-full text-[10px] border border-indigo-100/50 shadow-2xs">
                            {getRolesDisplay(user.roles)}
                          </span>
                        </td>
                        <td className="py-3.5 px-6">
                          <span
                            className={`px-2 py-0.5 rounded-sm font-bold text-[10px] uppercase ${
                              user.is_superuser
                                ? "bg-indigo-50 text-indigo-600 border border-indigo-100"
                                : "bg-slate-100 text-slate-400"
                            }`}
                          >
                            {user.is_superuser ? "SUPER" : "COMMON"}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono">
                          <button
                            type="button"
                            onClick={() => void statusMutation.mutateAsync(user)}
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold cursor-pointer transition-colors ${
                              user.is_active
                                ? "bg-emerald-50 text-emerald-600 border border-emerald-100"
                                : "bg-red-50 text-red-500 border border-red-100"
                            }`}
                          >
                            {user.is_active ? "ACTIVE" : "DISABLED"}
                          </button>
                        </td>
                        <td className="py-3.5 px-6 text-right">
                          <button
                            type="button"
                            onClick={() => openEditModal(user)}
                            className="px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-indigo-600 border border-slate-200/80 rounded-lg text-[11px] font-semibold transition-all shadow-2xs hover:shadow-sm cursor-pointer"
                          >
                            编辑
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {totalUsers > 0 ? (
            <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-100 bg-white px-6 py-4 text-xs gap-4 select-none">
              <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
                <div>
                  显示 <span className="font-semibold text-slate-800">{indexOfFirstUser + 1}</span>{" "}
                  至{" "}
                  <span className="font-semibold text-slate-800">
                    {indexOfLastUser}
                  </span>{" "}
                  条，共 <span className="font-semibold text-slate-800">{totalUsers}</span> 个用户
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
        {editingUser ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.button
              type="button"
              aria-label="关闭用户编辑弹窗"
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
              className="relative w-full max-w-lg bg-white rounded-2xl border border-slate-200/80 shadow-2xl overflow-hidden z-10 flex flex-col max-h-[85vh]"
            >
              <div className="px-6 py-4.5 border-b border-slate-100 flex justify-between items-center bg-slate-50/65">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
                    <h3 className="text-sm font-bold text-slate-800">编辑用户角色与信息</h3>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-normal">
                    维护用户账户对应的联系资料、安全标记和角色授权
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
                <div className="p-6 space-y-4 overflow-y-auto max-h-[50vh] md:max-h-[55vh] scrollbar-thin">
                  {errorMessage ? (
                    <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-red-700 text-xs font-semibold">
                      {errorMessage}
                    </div>
                  ) : null}

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase font-bold text-slate-500 block font-mono">
                      用户名 (username)
                    </label>
                    <div className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-600 font-mono text-xs select-all">
                      {form.username}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="user-nickname" className="text-[10.5px] font-bold text-slate-700 block">
                      昵称
                    </label>
                    <input
                      id="user-nickname"
                      aria-label="昵称"
                      type="text"
                      value={form.nickname}
                      onChange={(event) => updateField("nickname", event.target.value)}
                      placeholder="请输入昵称"
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="user-email" className="text-[10.5px] font-bold text-slate-700 block">
                      邮箱
                    </label>
                    <input
                      id="user-email"
                      aria-label="邮箱"
                      type="text"
                      value={form.email}
                      onChange={(event) => updateField("email", event.target.value)}
                      placeholder="请输入邮箱地址"
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="user-phone" className="text-[10.5px] font-bold text-slate-700 block">
                      手机号
                    </label>
                    <input
                      id="user-phone"
                      aria-label="手机号"
                      type="text"
                      value={form.phone}
                      onChange={(event) => updateField("phone", event.target.value)}
                      placeholder="请输入手机号"
                      className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-600 focus:outline-hidden transition-all"
                    />
                  </div>

                  <label className="flex items-center gap-3 p-3.5 bg-slate-50/50 border border-slate-200 rounded-xl hover:bg-slate-50 cursor-pointer select-none transition-colors">
                    <input
                      type="checkbox"
                      aria-label="设为超级管理员 (is_superuser)"
                      checked={form.is_superuser}
                      onChange={(event) => updateField("is_superuser", event.target.checked)}
                      className="w-4 h-4 text-indigo-600 border-slate-300 focus:ring-indigo-500 rounded cursor-pointer"
                    />
                    <span className="text-xs font-bold text-slate-800">
                      设为超级管理员 (is_superuser)
                    </span>
                  </label>

                  <div className="space-y-2.5">
                    <label className="text-[10.5px] font-bold text-slate-700 block">
                      角色分配
                    </label>

                    <div className="space-y-2.5">
                      {roles.length === 0 ? (
                        <p className="text-[11px] text-slate-400">暂无可分配角色。</p>
                      ) : (
                        roles.map((role: RoleResponse) => {
                          const isSelected = form.role_ids.includes(role.id);

                          return (
                            <label
                              key={role.id}
                              className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                                isSelected
                                  ? "bg-indigo-50/45 border-indigo-200 ring-2 ring-indigo-500/5"
                                  : "bg-white border-slate-200 hover:bg-slate-50/50"
                              }`}
                            >
                              <input
                                type="checkbox"
                                aria-label={`角色 ${role.name}`}
                                checked={isSelected}
                                onChange={() => toggleRole(role.id)}
                                className="mt-1 w-4 h-4 text-indigo-600 border-slate-300 focus:ring-indigo-500 rounded cursor-pointer transition-all"
                              />

                              <div className="space-y-0.5">
                                <div className="text-xs font-bold text-slate-800 flex items-center gap-2">
                                  <span>{role.name}</span>
                                  <span className="text-[9px] font-mono text-slate-400 bg-slate-100 px-1 py-0.2 rounded font-semibold uppercase">
                                    {role.code}
                                  </span>
                                </div>
                                <p className="text-[10.5px] text-slate-500 font-light leading-relaxed">
                                  {role.description ?? "未填写角色说明"}
                                </p>
                              </div>
                            </label>
                          );
                        })
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
                    保存修改
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
