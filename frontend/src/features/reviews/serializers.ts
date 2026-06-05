import type {
  ReviewRecordDetailResponse,
  ReviewRecordListItemResponse,
} from "../../lib/api/types";

export interface ConsoleReviewRecord {
  id: number;
  projectName: string;
  eventType: string;
  author: string;
  score: number | null;
  status: string;
  updatedAt: string;
  commitMessages: string[];
}

export function toConsoleReviewRecord(
  review: ReviewRecordListItemResponse
): ConsoleReviewRecord {
  return {
    id: review.id,
    projectName: review.project_name_snapshot,
    eventType: review.event_type,
    author: review.author,
    score: review.score,
    status: review.review_status,
    updatedAt: review.updated_at,
    commitMessages: review.commit_messages,
  };
}

export function toConsoleReviewDetail(review: ReviewRecordDetailResponse) {
  return {
    ...toConsoleReviewRecord(review),
    reviewPromptSnapshot: review.review_prompt_snapshot,
    commits: review.commits,
    summary: review.summary,
  };
}
