import type { TokenPair } from "../api/types";

const STORAGE_KEY = "ai-code-reviewer.auth";

/**
 * tokenStore 只负责浏览器本地存储，不承担业务决策，方便在测试中直接 mock。
 */
export const tokenStore = {
  load(): TokenPair | null {
    if (
      typeof window === "undefined" ||
      typeof window.localStorage?.getItem !== "function"
    ) {
      return null;
    }

    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) {
      return null;
    }

    try {
      return JSON.parse(raw) as TokenPair;
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  },
  save(payload: TokenPair) {
    if (
      typeof window === "undefined" ||
      typeof window.localStorage?.setItem !== "function"
    ) {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  },
  clear() {
    if (
      typeof window === "undefined" ||
      typeof window.localStorage?.removeItem !== "function"
    ) {
      return;
    }

    window.localStorage.removeItem(STORAGE_KEY);
  },
};
