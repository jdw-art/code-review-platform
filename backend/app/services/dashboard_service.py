from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LlmModel, Project, ReviewRecord
from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardChartPoint,
    DashboardModelSummary,
    DashboardOverviewResponse,
    DashboardRecentReviewItem,
    DashboardRepoHealthItem,
)


@dataclass
class _AggregateBucket:
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    score_total: float = 0.0
    scored_reviews: int = 0


class DashboardService:
    """提供管理后台仪表盘概览统计。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def get_overview(self) -> DashboardOverviewResponse:
        """返回项目与审查记录的概览统计。"""
        projects = self.session.scalars(select(Project).order_by(Project.id.asc())).all()
        models = self.session.scalars(
            select(LlmModel).order_by(
                LlmModel.is_default.desc(),
                LlmModel.is_active.desc(),
                LlmModel.id.asc(),
            )
        ).all()
        reviews = self.session.scalars(
            select(ReviewRecord).order_by(ReviewRecord.created_at.desc(), ReviewRecord.id.desc())
        ).all()

        total_projects = len(projects)
        active_projects = sum(1 for project in projects if project.is_active)
        total_review_records = len(reviews)
        scored_reviews = [review.score for review in reviews if review.score is not None]
        average_score = (
            round(sum(scored_reviews) / len(scored_reviews), 2)
            if scored_reviews
            else None
        )

        active_model = next(
            (
                model
                for model in models
                if model.is_default and model.is_active
            ),
            None,
        ) or next((model for model in models if model.is_active), None) or next(
            (model for model in models if model.is_default),
            None,
        )

        reviews_by_project: dict[int, list[ReviewRecord]] = defaultdict(list)
        project_buckets: dict[str, _AggregateBucket] = defaultdict(_AggregateBucket)
        member_buckets: dict[str, _AggregateBucket] = defaultdict(_AggregateBucket)

        for review in reviews:
            reviews_by_project[review.project_id].append(review)
            self._apply_review(project_buckets[review.project_name_snapshot], review)
            self._apply_review(member_buckets[review.author], review)

        return DashboardOverviewResponse(
            total_projects=total_projects,
            active_projects=active_projects,
            total_review_records=total_review_records,
            average_score=average_score,
            active_model_name=active_model.name if active_model is not None else None,
            recent_reviews=[
                DashboardRecentReviewItem(
                    id=review.id,
                    project_name=review.project_name_snapshot,
                    title=review.title,
                    branch=review.branch,
                    commit_hash=review.last_commit_id or review.external_commit_sha,
                    committer=review.author,
                    score=review.score,
                    review_status=review.review_status,
                    summary=review.summary,
                    created_at=review.created_at,
                )
                for review in reviews[:4]
            ],
            project_chart=self._build_chart_points(project_buckets),
            member_chart=self._build_chart_points(member_buckets),
            models=[
                DashboardModelSummary(
                    id=model.id,
                    name=model.name,
                    provider=model.provider,
                    temperature=model.temperature,
                    is_default=model.is_default,
                    is_active=model.is_active,
                )
                for model in models
            ],
            repo_health=self._build_repo_health(projects, reviews_by_project),
        )

    @staticmethod
    def _apply_review(bucket: _AggregateBucket, review: ReviewRecord) -> None:
        """把单条审查记录累计到图表聚合桶。"""
        bucket.commits += 1
        bucket.additions += review.additions
        bucket.deletions += review.deletions
        if review.score is not None:
            bucket.score_total += review.score
            bucket.scored_reviews += 1

    def _build_chart_points(
        self,
        buckets: dict[str, _AggregateBucket],
    ) -> list[DashboardChartPoint]:
        """构建项目/成员图表点。"""
        points = [
            DashboardChartPoint(
                name=name,
                commits=bucket.commits,
                avg_score=round(bucket.score_total / bucket.scored_reviews, 2)
                if bucket.scored_reviews
                else 0.0,
                additions=bucket.additions,
                deletions=bucket.deletions,
            )
            for name, bucket in buckets.items()
        ]
        return sorted(
            points,
            key=lambda item: (-item.commits, -item.additions, item.name.lower()),
        )

    def _build_repo_health(
        self,
        projects: list[Project],
        reviews_by_project: dict[int, list[ReviewRecord]],
    ) -> list[DashboardRepoHealthItem]:
        """构建仓库健康摘要。"""
        items: list[DashboardRepoHealthItem] = []
        for project in projects:
            reviews = reviews_by_project.get(project.id, [])
            scored_reviews = [review.score for review in reviews if review.score is not None]
            latest_review = max(reviews, key=lambda review: (review.created_at, review.id), default=None)
            items.append(
                DashboardRepoHealthItem(
                    project_id=project.id,
                    name=project.name,
                    is_active=project.is_active,
                    review_count=len(reviews),
                    average_score=(
                        round(sum(scored_reviews) / len(scored_reviews), 2)
                        if scored_reviews
                        else None
                    ),
                    last_review_at=latest_review.created_at if latest_review is not None else None,
                )
            )
        items.sort(
            key=lambda item: (
                -(item.average_score if item.average_score is not None else -1),
                -item.review_count,
                item.name.lower(),
            )
        )
        return items[:3]
