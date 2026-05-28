import axios, {
  AxiosHeaders,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";

import type { ApiErrorResponse, TokenPair } from "./types";
import { tokenStore } from "../auth/token-store";

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/**
 * 共享 HTTP 客户端，负责注入 access token，并在 access token 失效时自动尝试 refresh。
 */
export const http = axios.create({
  baseURL: API_BASE_URL,
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
});

let refreshPromise: Promise<TokenPair> | null = null;

function isAuthEndpoint(url?: string) {
  return Boolean(url?.startsWith("/auth/"));
}

async function refreshTokenPair(): Promise<TokenPair> {
  const stored = tokenStore.load();
  if (!stored?.refresh_token) {
    tokenStore.clear();
    throw new Error("缺少 refresh token，无法刷新会话。");
  }

  // 多个请求同时 401 时，共享同一个 refresh 过程，避免并发重复刷新。
  if (refreshPromise === null) {
    refreshPromise = refreshClient
      .post<TokenPair>("/auth/refresh", {
        refresh_token: stored.refresh_token,
      })
      .then((response) => {
        tokenStore.save(response.data);
        return response.data;
      })
      .catch((error) => {
        tokenStore.clear();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

http.interceptors.request.use((config) => {
  const stored = tokenStore.load();
  if (!stored?.access_token) {
    return config;
  }

  const headers = AxiosHeaders.from(config.headers);
  headers.set("Authorization", `Bearer ${stored.access_token}`);
  config.headers = headers;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const config = error.config as RetryableRequestConfig | undefined;
    if (
      config === undefined ||
      error.response?.status !== 401 ||
      config._retry ||
      isAuthEndpoint(config.url)
    ) {
      throw error;
    }

    config._retry = true;
    const replacement = await refreshTokenPair();
    const headers = AxiosHeaders.from(config.headers);
    headers.set("Authorization", `Bearer ${replacement.access_token}`);
    config.headers = headers;
    return http(config);
  }
);
