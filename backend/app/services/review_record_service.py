from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ReviewCommit, ReviewRecord
from app.db.session import get_db
from app.schemas.pagination import PageResponse
from app.schemas.review_record import (
    ReviewCommitResponse,
    ReviewRecordAuthorOption,
    ReviewRecordDetailResponse,
    ReviewRecordFiltersResponse,
    ReviewRecordListItemResponse,
    ReviewRecordQuery,
    ReviewRecordRawResponse,
)


class ReviewRecordService:
    """封装审查记录列表、详情、筛选与原始载荷查询。"""

    def __init__(self, session: Session = Depends(get_db)) -> None:
        self.session = session

    async def list_records(
        self,
        query: ReviewRecordQuery,
    ) -> PageResponse[ReviewRecordListItemResponse]:
        """分页返回审查记录列表。"""
        filters = []
        if query.project_id is not None:
            filters.append(ReviewRecord.project_id == query.project_id)
        if query.event_type:
            filters.append(ReviewRecord.event_type == query.event_type)
        if query.author:
            filters.append(ReviewRecord.author == query.author)
        if query.review_status:
            filters.append(ReviewRecord.review_status == query.review_status)

        total_statement = select(func.count()).select_from(ReviewRecord)
        list_statement = select(ReviewRecord).order_by(
            ReviewRecord.updated_at.desc(),
            ReviewRecord.id.desc(),
        )
        if filters:
            total_statement = total_statement.where(*filters)
            list_statement = list_statement.where(*filters)

        total = self.session.scalar(total_statement) or 0
        records = self.session.scalars(
            list_statement.offset(query.offset).limit(query.page_size)
        ).all()
        return PageResponse.create(
            items=[self._to_list_item(record) for record in records],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_record(self, review_record_id: int) -> ReviewRecordDetailResponse:
        """按 ID 返回审查记录详情。"""
        record = self._get_record_or_404(review_record_id, with_commits=True)
        return self._to_detail_response(record)

    async def get_raw_record(self, review_record_id: int) -> ReviewRecordRawResponse:
        """按 ID 返回审查记录原始 webhook / trace 数据。"""
        record = self._get_record_or_404(review_record_id, with_commits=False)
        return ReviewRecordRawResponse(
            id=record.id,
            webhook_data=record.webhook_data,
            agent_trace=record.agent_trace,
            extra_data=record.extra_data,
        )

    async def get_filters(self) -> ReviewRecordFiltersResponse:
        """返回审查记录列表筛选项。"""
        event_types = self.session.scalars(
            select(ReviewRecord.event_type)
            .distinct()
            .order_by(ReviewRecord.event_type.asc())
        ).all()
        authors = self.session.scalars(
            select(ReviewRecord.author)
            .distinct()
            .order_by(ReviewRecord.author.asc())
        ).all()
        return ReviewRecordFiltersResponse(
            event_types=[event_type for event_type in event_types if event_type],
            authors=[
                ReviewRecordAuthorOption(label=author, value=author)
                for author in authors
                if author
            ],
        )

    def _get_record_or_404(
        self,
        review_record_id: int,
        *,
        with_commits: bool,
    ) -> ReviewRecord:
        """读取单条审查记录，不存在则抛出 404。"""
        statement = select(ReviewRecord).where(ReviewRecord.id == review_record_id)
        if with_commits:
            statement = statement.options(selectinload(ReviewRecord.commits))
        record = self.session.scalar(statement)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="审查记录不存在。",
            )
        return record

    @staticmethod
    def _to_list_item(record: ReviewRecord) -> ReviewRecordListItemResponse:
        """将 ORM 对象转换为审查记录列表响应。"""
        return ReviewRecordListItemResponse(
            id=record.id,
            project_id=record.project_id,
            event_type=record.event_type,
            external_event_id=record.external_event_id,
            project_name_snapshot=record.project_name_snapshot,
            template_id_snapshot=record.template_id_snapshot,
            template_name_snapshot=record.template_name_snapshot,
            author=record.author,
            title=record.title,
            branch=record.branch,
            source_branch=record.source_branch,
            target_branch=record.target_branch,
            commit_count=record.commit_count,
            commit_messages=record.commit_messages,
            score=record.score,
            review_status=record.review_status,
            review_result=record.review_result,
            summary=record.summary,
            url=record.url,
            url_slug=record.url_slug,
            last_commit_id=record.last_commit_id,
            additions=record.additions,
            deletions=record.deletions,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_detail_response(self, record: ReviewRecord) -> ReviewRecordDetailResponse:
        """将 ORM 对象转换为审查记录详情响应。"""
        return ReviewRecordDetailResponse(
            **self._to_list_item(record).model_dump(),
            review_prompt_snapshot=record.review_prompt_snapshot,
            commits=[self._to_commit_response(commit) for commit in record.commits],
        )

    @staticmethod
    def _to_commit_response(commit: ReviewCommit) -> ReviewCommitResponse:
        """将 commit ORM 对象转换为响应模型。"""
        return ReviewCommitResponse(
            id=commit.id,
            commit_id=commit.commit_id,
            short_commit_id=commit.short_commit_id,
            author=commit.author,
            message=commit.message,
            timestamp=commit.timestamp,
            sequence=commit.sequence,
            payload=commit.payload,
            created_at=commit.created_at,
        )
