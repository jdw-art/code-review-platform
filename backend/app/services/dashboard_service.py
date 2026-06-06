from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

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


@dataclass(frozen=True)
class _ReviewOverviewRow:
    id: int
    project_id: int
    project_name_snapshot: str
    title: str | None
    branch: str | None
    last_commit_id: str | None
    external_commit_sha: str | None
    author: str
    score: float | None
    review_status: str
    summary: str | None
    created_at: datetime
    commit_count: int
    additions: int
    deletions: int

    @property
    def commit_hash(self) -> str | None:
        return self.last_commit_id or self.external_commit_sha


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
        review_rows = [
            _ReviewOverviewRow(**row)
            for row in self.session.execute(
                select(
                    ReviewRecord.id,
                    ReviewRecord.project_id,
                    ReviewRecord.project_name_snapshot,
                    ReviewRecord.title,
                    ReviewRecord.branch,
                    ReviewRecord.last_commit_id,
                    ReviewRecord.external_commit_sha,
                    ReviewRecord.author,
                    ReviewRecord.score,
                    ReviewRecord.review_status,
                    ReviewRecord.summary,
                    ReviewRecord.created_at,
                    ReviewRecord.commit_count,
                    ReviewRecord.additions,
                    ReviewRecord.deletions,
                ).order_by(ReviewRecord.created_at.desc(), ReviewRecord.id.desc())
            )
            .mappings()
            .all()
        ]

        total_projects = len(projects)
        active_projects = sum(1 for project in projects if project.is_active)
        total_review_records = len(review_rows)
        scored_reviews = [
            review.score
            for review in review_rows
            if self._is_scored_review(review)
        ]
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
        ) or next((model for model in models if model.is_active), None)

        project_names = {project.id: project.name for project in projects}
        reviews_by_project: dict[int, list[_ReviewOverviewRow]] = defaultdict(list)
        project_buckets: dict[int, _AggregateBucket] = defaultdict(_AggregateBucket)
        member_buckets: dict[str, _AggregateBucket] = defaultdict(_AggregateBucket)

        for review in review_rows:
            reviews_by_project[review.project_id].append(review)
            self._apply_review(project_buckets[review.project_id], review)
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
                    commit_hash=review.commit_hash,
                    committer=review.author,
                    score=review.score,
                    review_status=review.review_status,
                    summary=review.summary,
                    created_at=review.created_at,
                )
                for review in review_rows[:4]
            ],
            project_chart=self._build_project_chart(project_buckets, project_names),
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
    def _is_scored_review(review: _ReviewOverviewRow) -> bool:
        """只有 reviewed 状态且有分数的记录才参与质量均分。"""
        return review.review_status == "reviewed" and review.score is not None

    def _apply_review(self, bucket: _AggregateBucket, review: _ReviewOverviewRow) -> None:
        """把单条审查记录累计到图表聚合桶。"""
        bucket.commits += review.commit_count
        bucket.additions += review.additions
        bucket.deletions += review.deletions
        if self._is_scored_review(review):
            bucket.score_total += review.score
            bucket.scored_reviews += 1

    def _build_project_chart(
        self,
        buckets: dict[int, _AggregateBucket],
        project_names: dict[int, str],
    ) -> list[DashboardChartPoint]:
        """按稳定 project_id 聚合项目图表，再映射显示名。"""
        return [
            DashboardChartPoint(
                project_id=project_id,
                name=project_names.get(project_id, f"Project {project_id}"),
                commits=bucket.commits,
                avg_score=round(bucket.score_total / bucket.scored_reviews, 2)
                if bucket.scored_reviews
                else None,
                additions=bucket.additions,
                deletions=bucket.deletions,
            )
            for project_id, bucket in sorted(
                buckets.items(),
                key=lambda item: (
                    -item[1].commits,
                    -item[1].additions,
                    project_names.get(item[0], "").lower(),
                    item[0],
                ),
            )
        ]

    def _build_chart_points(
        self,
        buckets: dict[str, _AggregateBucket],
    ) -> list[DashboardChartPoint]:
        """构建项目/成员图表点。"""
        points = [
            DashboardChartPoint(
                project_id=None,
                name=name,
                commits=bucket.commits,
                avg_score=round(bucket.score_total / bucket.scored_reviews, 2)
                if bucket.scored_reviews
                else None,
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
        reviews_by_project: dict[int, list[_ReviewOverviewRow]],
    ) -> list[DashboardRepoHealthItem]:
        """构建仓库健康摘要。"""
        items: list[DashboardRepoHealthItem] = []
        for project in projects:
            reviews = reviews_by_project.get(project.id, [])
            scored_reviews = [
                review.score
                for review in reviews
                if self._is_scored_review(review)
            ]
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
