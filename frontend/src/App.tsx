import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { AuthProvider } from "./lib/auth/auth-context";
import { queryClient } from "./lib/query/query-client";
import { router } from "./routes/router";

/**
 * 应用根组件负责挂接全局数据层、认证上下文和路由。
 */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
