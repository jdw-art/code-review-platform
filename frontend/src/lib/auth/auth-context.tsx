import axios from "axios";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { http } from "../api/http";
import type {
  AccessContextResponse,
  ApiErrorResponse,
  CurrentUserProfileResponse,
  CurrentUserRoleSummary,
  CurrentUserSummary,
  MenuNode,
  TokenPair,
} from "../api/types";
import { tokenStore } from "./token-store";

type AuthStatus =
  | "loading"
  | "anonymous"
  | "authenticated"
  | "password_change_required";

interface LoginPayload {
  username: string;
  password: string;
}

interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUserSummary | null;
  roles: CurrentUserRoleSummary[];
  permissions: string[];
  menuTree: MenuNode[];
  mustChangePassword: boolean;
  login: (payload: LoginPayload) => Promise<{ mustChangePassword: boolean }>;
  logout: () => Promise<void>;
  changePassword: (payload: ChangePasswordPayload) => Promise<void>;
  refreshAccessContext: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function isPasswordChangeRequiredError(error: unknown) {
  return (
    axios.isAxiosError<ApiErrorResponse>(error) &&
    error.response?.data.code === "PASSWORD_CHANGE_REQUIRED"
  );
}

/**
 * AuthProvider 负责串联登录、会话恢复、强制改密和菜单上下文初始化。
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const initialTokenPair = tokenStore.load();
  const [status, setStatus] = useState<AuthStatus>(
    initialTokenPair === null ? "anonymous" : "loading"
  );
  const [user, setUser] = useState<CurrentUserSummary | null>(null);
  const [roles, setRoles] = useState<CurrentUserRoleSummary[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [menuTree, setMenuTree] = useState<MenuNode[]>([]);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  function clearAuthState() {
    tokenStore.clear();
    setStatus("anonymous");
    setUser(null);
    setRoles([]);
    setPermissions([]);
    setMenuTree([]);
    setMustChangePassword(false);
  }

  function applyAccessContext(payload: AccessContextResponse) {
    setStatus(payload.must_change_password ? "password_change_required" : "authenticated");
    setUser(payload.user);
    setRoles(payload.roles);
    setPermissions(payload.permissions);
    setMenuTree(payload.menus);
    setMustChangePassword(payload.must_change_password);
  }

  function applyProfile(payload: CurrentUserProfileResponse) {
    setStatus(payload.must_change_password ? "password_change_required" : "authenticated");
    setUser({
      id: payload.id,
      username: payload.username,
      nickname: payload.nickname,
      email: payload.email,
      phone: payload.phone,
      is_active: payload.is_active,
      is_superuser: payload.is_superuser,
    });
    setRoles(payload.roles);
    setPermissions([]);
    setMenuTree([]);
    setMustChangePassword(payload.must_change_password);
  }

  async function loadAccessContext() {
    const response = await http.get<AccessContextResponse>("/me/access-context");
    applyAccessContext(response.data);
  }

  async function loadProfile() {
    const response = await http.get<CurrentUserProfileResponse>("/me/profile");
    applyProfile(response.data);
  }

  async function syncSessionFromTokenPair(tokenPair: TokenPair) {
    // 首次登录强制改密期间，后台不允许拉取 access-context，只能读个人资料并走改密流程。
    if (tokenPair.must_change_password) {
      await loadProfile();
      return;
    }

    try {
      await loadAccessContext();
    } catch (error) {
      if (isPasswordChangeRequiredError(error)) {
        await loadProfile();
        return;
      }
      throw error;
    }
  }

  async function refreshAccessContext() {
    const stored = tokenStore.load();
    if (stored === null) {
      clearAuthState();
      return;
    }

    try {
      await syncSessionFromTokenPair(stored);
    } catch {
      clearAuthState();
    }
  }

  async function login(payload: LoginPayload) {
    const response = await http.post<TokenPair>("/auth/login", payload);
    tokenStore.save(response.data);
    await syncSessionFromTokenPair(response.data);
    return { mustChangePassword: response.data.must_change_password };
  }

  async function logout() {
    const stored = tokenStore.load();
    try {
      if (stored?.refresh_token) {
        await http.post("/auth/logout", {
          refresh_token: stored.refresh_token,
        });
      }
    } finally {
      clearAuthState();
    }
  }

  async function changePassword(payload: ChangePasswordPayload) {
    await http.post("/auth/change-password", payload);
    // 修改密码后 refresh session 已被后端吊销，前端直接清空会话并要求重新登录最稳妥。
    clearAuthState();
  }

  useEffect(() => {
    const stored = tokenStore.load();
    if (stored === null) {
      return;
    }
    const tokenPair = stored;

    let cancelled = false;

    async function restoreSession() {
      try {
        await syncSessionFromTokenPair(tokenPair);
      } catch {
        if (!cancelled) {
          clearAuthState();
        }
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        roles,
        permissions,
        menuTree,
        mustChangePassword,
        login,
        logout,
        changePassword,
        refreshAccessContext,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * useAuth 是后台壳子的统一认证入口，避免页面绕过上下文直接操作 token。
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth 必须在 AuthProvider 内部使用。");
  }
  return context;
}
