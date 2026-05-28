import { http } from "../../lib/api/http";
import type {
  MemberAnalyticsDetailResponse,
  MemberAnalyticsListItemResponse,
  PageResponse,
} from "../../lib/api/types";

export interface MemberAnalyticsListParams {
  page: number;
  page_size: number;
  project_id?: number;
}

/**
 * 查询成员分析分页列表。
 */
export async function listMemberAnalytics(params: MemberAnalyticsListParams) {
  const response = await http.get<PageResponse<MemberAnalyticsListItemResponse>>(
    "/member-analytics",
    {
      params,
    }
  );
  return response.data;
}

/**
 * 查询单个项目成员的分析详情。
 */
export async function getMemberAnalytics(projectMemberId: number) {
  const response = await http.get<MemberAnalyticsDetailResponse>(
    `/member-analytics/${projectMemberId}`
  );
  return response.data;
}
