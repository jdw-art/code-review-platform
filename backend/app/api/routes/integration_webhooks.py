from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.integrations import INTEGRATION_ADAPTERS, BaseIntegrationAdapter
from app.db.models import Project
from app.schemas.integration_webhook import WebhookAcceptedResponse
from app.services.integration_project_locator import IntegrationProjectLocator
from app.services.review_ingest_service import ReviewIngestService
from app.services.review_queue_service import ReviewQueueService, get_review_queue_service


router = APIRouter(prefix="/integrations/webhooks", tags=["integration-webhooks"])
logger = logging.getLogger(__name__)


def get_adapter_registry() -> dict[str, type[BaseIntegrationAdapter]]:
    return INTEGRATION_ADAPTERS


def get_project_locator(
    ingest_service: ReviewIngestService = Depends(),
) -> IntegrationProjectLocator:
    return IntegrationProjectLocator(ingest_service.session)


def _merge_review_only_protected_branches_enabled() -> bool:
    return os.environ.get("MERGE_REVIEW_ONLY_PROTECTED_BRANCHES_ENABLED", "0") == "1"


def _project_protected_branches(project: Project) -> set[str]:
    raw_value = project.settings.get("protected_branches")
    if isinstance(raw_value, list):
        branches = {
            str(item).strip()
            for item in raw_value
            if str(item).strip()
        }
        if branches:
            return branches
    return {project.default_branch}


def _is_draft_or_wip(
    *,
    platform_type: str,
    payload: dict[str, Any],
) -> bool:
    if platform_type == "gitlab":
        attributes = payload.get("object_attributes")
        if not isinstance(attributes, dict):
            return False
        return bool(
            attributes.get("draft")
            or attributes.get("work_in_progress")
        )

    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return False
    title = pull_request.get("title")
    normalized_title = title.lower().strip() if isinstance(title, str) else ""
    return bool(
        pull_request.get("draft")
        or normalized_title.startswith("wip")
    )


def _is_supported_action(
    *,
    platform_type: str,
    event_type: str,
    action: str | None,
) -> bool:
    if event_type == "push":
        return True
    if platform_type == "gitlab":
        return action in {"open", "update"}
    if platform_type == "github":
        return action in {"opened", "synchronize"}
    return False


def _matches_target_branch_policy(project: Project, target_branch: str | None) -> bool:
    if not _merge_review_only_protected_branches_enabled():
        return True
    if not target_branch:
        return False
    return target_branch in _project_protected_branches(project)


def _has_required_fields(event_type: str, payload: dict[str, Any]) -> bool:
    if event_type == "merge_request":
        attributes = payload.get("object_attributes")
        if not isinstance(attributes, dict):
            return False
        last_commit = attributes.get("last_commit")
        last_commit_id = None
        if isinstance(last_commit, dict):
            last_commit_id = last_commit.get("id")
        if not last_commit_id:
            last_commit_id = attributes.get("last_commit_id")
        return bool(
            attributes.get("source_branch")
            and attributes.get("target_branch")
            and last_commit_id
        )

    if event_type == "pull_request":
        pull_request = payload.get("pull_request")
        if not isinstance(pull_request, dict):
            return False
        head = pull_request.get("head")
        base = pull_request.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            return False
        return bool(head.get("ref") and head.get("sha") and base.get("ref"))

    if event_type == "push":
        return bool(payload.get("ref") and (payload.get("checkout_sha") or payload.get("after")))

    return False


def _should_skip_event(
    *,
    project: Project,
    platform_type: str,
    event_type: str,
    action: str | None,
    target_branch: str | None,
    payload: dict[str, Any],
) -> bool:
    if not project.review_enabled:
        return True
    if not _has_required_fields(event_type, payload):
        return True
    if not _is_supported_action(
        platform_type=platform_type,
        event_type=event_type,
        action=action,
    ):
        return True
    if event_type in {"merge_request", "pull_request"} and _is_draft_or_wip(
        platform_type=platform_type,
        payload=payload,
    ):
        return True
    if event_type in {"merge_request", "pull_request"} and not _matches_target_branch_policy(
        project,
        target_branch,
    ):
        return True
    return False


async def _accept_webhook(
    *,
    platform_type: str,
    payload: dict[str, Any],
    headers: Mapping[str, str],
    ingest_service: ReviewIngestService,
    queue_service: ReviewQueueService,
    adapter_registry: dict[str, type[BaseIntegrationAdapter]],
    locator: IntegrationProjectLocator,
) -> WebhookAcceptedResponse:
    adapter_class = adapter_registry.get(platform_type)
    if adapter_class is None:
        logger.warning("Unsupported webhook platform received platform=%s.", platform_type)
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")
    if not isinstance(payload, dict):
        logger.warning("Skipping non-object webhook payload platform=%s.", platform_type)
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")

    try:
        adapter = adapter_class()
        event = adapter.parse_webhook(payload, dict(headers))
    except ValueError as exc:
        logger.warning(
            "Skipping invalid webhook payload platform=%s error=%s.",
            platform_type,
            exc,
        )
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")

    project = locator.locate(
        platform_type=platform_type,
        repo_url=event.repo_url,
        repo_full_name=event.repo_full_name,
        external_project_id=event.external_project_id,
    )
    if project is None or _should_skip_event(
        project=project,
        platform_type=platform_type,
        event_type=event.event_type,
        action=event.action,
        target_branch=event.target_branch,
        payload=payload,
    ):
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")

    review_record, is_duplicate = await ingest_service.ingest_webhook_event(
        project=project,
        event=event,
    )
    if is_duplicate:
        ingest_service.session.rollback()
        return WebhookAcceptedResponse(
            review_record_id=review_record.id,
            status="duplicate",
        )

    try:
        raw_message = await queue_service.enqueue(
            review_record_id=review_record.id,
            platform_type=event.platform_type,
        )
        try:
            ingest_service.session.commit()
        except Exception as exc:
            ingest_service.session.rollback()
            try:
                await queue_service.remove_message(raw_message)
            except Exception:
                logger.exception(
                    "Failed to remove queued webhook message after commit failure platform=%s review_record_id=%s.",
                    platform_type,
                    review_record.id,
                )
            logger.exception(
                "Webhook commit failed after enqueue platform=%s project_id=%s error=%s.",
                platform_type,
                project.id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="审查任务落库失败。",
            ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        ingest_service.session.rollback()
        logger.exception(
            "Webhook enqueue failed platform=%s project_id=%s error=%s.",
            platform_type,
            project.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="审查任务入队失败。",
        ) from exc

    return WebhookAcceptedResponse(
        review_record_id=review_record.id,
        status="queued",
    )


@router.post(
    "/gitlab",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="接收 GitLab webhook",
    description="接收 GitLab merge request 或 push webhook，完成标准化、落库与入队。",
)
async def receive_gitlab_webhook(
    request: Request,
    ingest_service: ReviewIngestService = Depends(),
    queue_service: ReviewQueueService = Depends(get_review_queue_service),
    adapter_registry: dict[str, type[BaseIntegrationAdapter]] = Depends(get_adapter_registry),
    locator: IntegrationProjectLocator = Depends(get_project_locator),
) -> WebhookAcceptedResponse:
    try:
        payload = await request.json()
    except (ValueError, JSONDecodeError):
        logger.warning("Skipping malformed GitLab webhook payload.")
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")
    return await _accept_webhook(
        platform_type="gitlab",
        payload=payload,
        headers=request.headers,
        ingest_service=ingest_service,
        queue_service=queue_service,
        adapter_registry=adapter_registry,
        locator=locator,
    )


@router.post(
    "/github",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="接收 GitHub webhook",
    description="接收 GitHub pull request 或 push webhook，完成标准化、落库与入队。",
)
async def receive_github_webhook(
    request: Request,
    ingest_service: ReviewIngestService = Depends(),
    queue_service: ReviewQueueService = Depends(get_review_queue_service),
    adapter_registry: dict[str, type[BaseIntegrationAdapter]] = Depends(get_adapter_registry),
    locator: IntegrationProjectLocator = Depends(get_project_locator),
) -> WebhookAcceptedResponse:
    try:
        payload = await request.json()
    except (ValueError, JSONDecodeError):
        logger.warning("Skipping malformed GitHub webhook payload.")
        return WebhookAcceptedResponse(review_record_id=0, status="skipped")
    return await _accept_webhook(
        platform_type="github",
        payload=payload,
        headers=request.headers,
        ingest_service=ingest_service,
        queue_service=queue_service,
        adapter_registry=adapter_registry,
        locator=locator,
    )
