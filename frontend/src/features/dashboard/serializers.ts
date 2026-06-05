import type {
  DashboardChartPoint,
  DashboardOverviewResponse,
  DashboardRecentReviewItem,
} from "../../lib/api/types";

export interface ConsoleDashboardStat {
  label: string;
  value: number;
}

export interface ConsoleDashboardOverview {
  totalProjects: number;
  activeProjects: number;
  totalReviewRecords: number;
  averageScore: number | null;
  activeModelName: string | null;
  recentReviews: DashboardRecentReviewItem[];
  projectChart: DashboardChartPoint[];
  memberChart: DashboardChartPoint[];
}

export function toConsoleDashboardOverview(
  overview: DashboardOverviewResponse
): ConsoleDashboardOverview {
  const recentReviews = Array.isArray(overview.recent_reviews)
    ? overview.recent_reviews
    : [];
  const projectChart = Array.isArray(overview.project_chart)
    ? overview.project_chart
    : [];
  const memberChart = Array.isArray(overview.member_chart)
    ? overview.member_chart
    : [];

  return {
    totalProjects: overview.total_projects,
    activeProjects: overview.active_projects,
    totalReviewRecords: overview.total_review_records,
    averageScore: overview.average_score,
    activeModelName: overview.active_model_name,
    recentReviews,
    projectChart,
    memberChart,
  };
}
