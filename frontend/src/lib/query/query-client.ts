import { QueryClient } from "@tanstack/react-query";

/**
 * 当前阶段以前端关键链路验证为主，关闭默认重试可以避免认证失败时重复打接口。
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export const queryClient = createQueryClient();
