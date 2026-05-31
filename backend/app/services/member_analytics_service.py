from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ProjectMember, ReviewRecord
from app.db.session import get_db
from app.schemas.member_analytics import (
    MemberAnalyticsDetailResponse,
    MemberAnalyticsListItemResponse,
    MemberAnalyticsQuery,
    MemberAnalyticsRecentReviewResponse,
)
from app.schemas.pagination import PageResponse


class MemberAnalyticsService:
    """提供项目成员维度的审查统计查询。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def list_member_analytics(
        self,
        query: MemberAnalyticsQuery,
    ) -> PageResponse[MemberAnalyticsListItemResponse]:
        """分页返回成员分析列表。"""
        statement = (
            select(ProjectMember)
            .options(selectinload(ProjectMember.project))
            .where(ProjectMember.is_active.is_(True))
            .order_by(ProjectMember.id.asc())
        )
        if query.project_id is not None:
            statement = statement.where(ProjectMember.project_id == query.project_id)

        members = self.session.scalars(statement).all()
        total = len(members)
        paged_members = members[query.offset : query.offset + query.page_size]
        return PageResponse.create(
            items=[self._to_list_item(member) for member in paged_members],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_member_analytics(
        self,
        project_member_id: int,
    ) -> MemberAnalyticsDetailResponse:
        """返回单个项目成员的统计详情。"""
        project_member = self.session.scalar(
            select(ProjectMember)
            .options(selectinload(ProjectMember.project))
            .where(ProjectMember.id == project_member_id)
        )
        if project_member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目成员不存在。",
            )

        recent_reviews = self._get_reviews_for_member(project_member)
        stats = self._aggregate_member_reviews(project_member, recent_reviews)
        return MemberAnalyticsDetailResponse(
            **stats.model_dump(),
            recent_reviews=[
                MemberAnalyticsRecentReviewResponse(
                    review_record_id=review.id,
                    event_type=review.event_type,
                    title=review.title,
                    url_slug=review.url_slug,
                    score=review.score,
                    review_status=review.review_status,
                    updated_at=review.updated_at,
                )
                for review in recent_reviews[:10]
            ],
        )

    def _to_list_item(self, project_member: ProjectMember) -> MemberAnalyticsListItemResponse:
        """将项目成员与其审查记录聚合为列表项。"""
        reviews = self._get_reviews_for_member(project_member)
        return self._aggregate_member_reviews(project_member, reviews)

    def _aggregate_member_reviews(
        self,
        project_member: ProjectMember,
        reviews: list[ReviewRecord],
    ) -> MemberAnalyticsListItemResponse:
        """聚合单个成员的审查统计。"""
        review_count = len(reviews)
        scored_reviews = [review.score for review in reviews if review.score is not None]
        average_score = (
            round(sum(scored_reviews) / len(scored_reviews), 2)
            if scored_reviews
            else None
        )
        total_additions = sum(review.additions for review in reviews)
        total_deletions = sum(review.deletions for review in reviews)
        last_review_at = reviews[0].updated_at if reviews else None
        return MemberAnalyticsListItemResponse(
            project_member_id=project_member.id,
            project_id=project_member.project_id,
            project_name=project_member.project.name,
            member_name=project_member.member_name,
            member_email=project_member.member_email,
            role_name=project_member.role_name,
            review_count=review_count,
            average_score=average_score,
            total_additions=total_additions,
            total_deletions=total_deletions,
            last_review_at=last_review_at,
        )

    def _get_reviews_for_member(self, project_member: ProjectMember) -> list[ReviewRecord]:
        """读取单个项目成员对应的审查记录。"""
        return self.session.scalars(
            select(ReviewRecord)
            .where(
                ReviewRecord.project_id == project_member.project_id,
                ReviewRecord.author == project_member.member_name,
                ReviewRecord.review_status == "reviewed",
            )
            .order_by(ReviewRecord.updated_at.desc(), ReviewRecord.id.desc())
        ).all()
