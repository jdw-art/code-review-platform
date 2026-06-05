import type {
  MemberAnalyticsDetailResponse,
  MemberAnalyticsListItemResponse,
} from "../../lib/api/types";

export interface ConsoleMemberAnalyticsRow {
  id: number;
  projectId: number;
  projectName: string;
  memberName: string;
  memberEmail: string | null;
  roleName: string | null;
  reviewCount: number;
  averageScore: number | null;
  totalChanges: number;
  lastReviewAt: string | null;
}

export function toConsoleMemberAnalyticsRow(
  member: MemberAnalyticsListItemResponse
): ConsoleMemberAnalyticsRow {
  return {
    id: member.project_member_id,
    projectId: member.project_id,
    projectName: member.project_name,
    memberName: member.member_name,
    memberEmail: member.member_email,
    roleName: member.role_name,
    reviewCount: member.review_count,
    averageScore: member.average_score,
    totalChanges: member.total_additions + member.total_deletions,
    lastReviewAt: member.last_review_at,
  };
}

export function toConsoleMemberAnalyticsDetail(
  member: MemberAnalyticsDetailResponse
) {
  return {
    ...toConsoleMemberAnalyticsRow(member),
    recentReviews: member.recent_reviews,
  };
}
