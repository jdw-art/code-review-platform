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
  const commitMessages = Array.isArray(review.commit_messages)
    ? review.commit_messages.filter(
        (message): message is string => typeof message === "string"
      )
    : [];

  return {
    id: review.id,
    projectName: review.project_name_snapshot,
    eventType: review.event_type,
    author: review.author,
    score: review.score,
    status: review.review_status,
    updatedAt: review.updated_at,
    commitMessages,
  };
}

export function toConsoleReviewDetail(review: ReviewRecordDetailResponse) {
  const commits = Array.isArray(review.commits) ? review.commits : [];

  return {
    ...toConsoleReviewRecord(review),
    reviewPromptSnapshot: review.review_prompt_snapshot,
    commits,
    summary: review.summary,
  };
}
