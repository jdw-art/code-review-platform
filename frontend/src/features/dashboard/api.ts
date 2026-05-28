import { http } from "../../lib/api/http";
import type { DashboardOverviewResponse } from "../../lib/api/types";

/**
 * 查询管理后台仪表盘概览统计。
 */
export async function getDashboardOverview() {
  const response = await http.get<DashboardOverviewResponse>("/dashboard/overview");
  return response.data;
}
