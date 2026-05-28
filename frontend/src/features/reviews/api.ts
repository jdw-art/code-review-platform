import { http } from "../../lib/api/http";
import type {
  PageResponse,
  ReviewRecordDetailResponse,
  ReviewRecordFiltersResponse,
  ReviewRecordListItemResponse,
} from "../../lib/api/types";

export interface ReviewRecordListParams {
  page: number;
  page_size: number;
  project_id?: number;
  event_type?: string;
  author?: string;
  review_status?: string;
}

/**
 * 查询审查记录分页列表。
 */
export async function listReviewRecords(params: ReviewRecordListParams) {
  const response = await http.get<PageResponse<ReviewRecordListItemResponse>>(
    "/review-records",
    {
      params,
    }
  );
  return response.data;
}

/**
 * 查询单条审查记录详情。
 */
export async function getReviewRecord(reviewRecordId: number) {
  const response = await http.get<ReviewRecordDetailResponse>(
    `/review-records/${reviewRecordId}`
  );
  return response.data;
}

/**
 * 查询审查记录筛选项，后续接筛选面板时可直接复用。
 */
export async function getReviewRecordFilters() {
  const response = await http.get<ReviewRecordFiltersResponse>("/review-records/filters");
  return response.data;
}
