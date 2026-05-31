from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.models import NotificationBot, ReviewRecord
from app.services.auth_service import get_settings


@dataclass(slots=True)
class NotificationTarget:
    bot_type: str
    webhook_url: str
    secret: str | None = None


class ReviewNotificationSender:
    """默认通知发送器，兼容现有 codereview 环境变量配置。"""

    def __init__(
        self,
        settings: Settings | None = None,
        cipher: SecretCipher | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cipher = cipher or SecretCipher(self.settings.secret_encryption_key)

    def send(
        self,
        *,
        bot_type: str,
        webhook_url: str,
        secret: str | None,
        content: str,
        title: str,
        project_name: str | None,
        url_slug: str | None,
        webhook_data: dict[str, object],
    ) -> None:
        normalized_bot_type = bot_type.strip().lower()
        if normalized_bot_type == "dingtalk":
            self._send_dingtalk_markdown(
                webhook_url=webhook_url,
                secret=secret,
                title=title,
                content=content,
            )
            return
        if normalized_bot_type == "wecom":
            self._send_wecom_markdown(webhook_url=webhook_url, title=title, content=content)
            return
        if normalized_bot_type == "feishu":
            self._send_feishu_markdown(webhook_url=webhook_url, title=title, content=content)
            return
        if normalized_bot_type in {"webhook", "extra_webhook", "custom_webhook"}:
            self._post_json(
                webhook_url,
                {
                    "ai_codereview_data": {
                        "content": content,
                        "msg_type": "markdown",
                        "title": title,
                        "project_name": project_name,
                        "url_slug": url_slug,
                    },
                    "webhook_data": webhook_data,
                },
            )
            return
        raise ValueError(f"Unsupported notification bot type: {bot_type}")

    def send_env_fallback(
        self,
        *,
        content: str,
        title: str,
        project_name: str | None,
        url_slug: str | None,
        webhook_data: dict[str, object],
    ) -> None:
        errors: list[str] = []

        for bot_type in ("dingtalk", "wecom", "feishu"):
            target = self._resolve_env_target(
                bot_type=bot_type,
                project_name=project_name,
                url_slug=url_slug,
            )
            if target is None:
                continue
            try:
                self.send(
                    bot_type=target.bot_type,
                    webhook_url=target.webhook_url,
                    secret=target.secret,
                    content=content,
                    title=title,
                    project_name=project_name,
                    url_slug=url_slug,
                    webhook_data=webhook_data,
                )
            except Exception as exc:
                errors.append(f"{bot_type}: {exc}")

        extra_target = self._resolve_env_target(
            bot_type="extra_webhook",
            project_name=project_name,
            url_slug=url_slug,
        )
        if extra_target is not None:
            try:
                self.send(
                    bot_type=extra_target.bot_type,
                    webhook_url=extra_target.webhook_url,
                    secret=extra_target.secret,
                    content=content,
                    title=title,
                    project_name=project_name,
                    url_slug=url_slug,
                    webhook_data=webhook_data,
                )
            except Exception as exc:
                errors.append(f"extra_webhook: {exc}")

        if errors:
            raise RuntimeError("; ".join(errors))

    def resolve_bot_secret(self, bot: NotificationBot) -> str | None:
        if bot.secret_encrypted is None:
            return None
        return self.cipher.decrypt_text(bot.secret_encrypted)

    def _resolve_env_target(
        self,
        *,
        bot_type: str,
        project_name: str | None,
        url_slug: str | None,
    ) -> NotificationTarget | None:
        if bot_type == "dingtalk":
            if os.getenv("DINGTALK_ENABLED", "0") != "1":
                return None
            webhook_url = self._lookup_scoped_env_url(
                default_key="DINGTALK_WEBHOOK_URL",
                project_name=project_name,
                url_slug=url_slug,
            )
            if not webhook_url:
                return None
            secret = os.getenv("DINGTALK_SECRET") if os.getenv("DINGTALK_SECRET_ENABLED", "0") == "1" else None
            return NotificationTarget(bot_type="dingtalk", webhook_url=webhook_url, secret=secret)

        if bot_type == "wecom":
            if os.getenv("WECOM_ENABLED", "0") != "1":
                return None
            webhook_url = self._lookup_scoped_env_url(
                default_key="WECOM_WEBHOOK_URL",
                project_name=project_name,
                url_slug=url_slug,
            )
            if not webhook_url:
                return None
            return NotificationTarget(bot_type="wecom", webhook_url=webhook_url)

        if bot_type == "feishu":
            if os.getenv("FEISHU_ENABLED", "0") != "1":
                return None
            webhook_url = self._lookup_scoped_env_url(
                default_key="FEISHU_WEBHOOK_URL",
                project_name=project_name,
                url_slug=url_slug,
            )
            if not webhook_url:
                return None
            return NotificationTarget(bot_type="feishu", webhook_url=webhook_url)

        if bot_type == "extra_webhook":
            if os.getenv("EXTRA_WEBHOOK_ENABLED", "0") != "1":
                return None
            webhook_url = os.getenv("EXTRA_WEBHOOK_URL", "").strip()
            if not webhook_url:
                return None
            return NotificationTarget(bot_type="extra_webhook", webhook_url=webhook_url)

        return None

    @staticmethod
    def _lookup_scoped_env_url(
        *,
        default_key: str,
        project_name: str | None,
        url_slug: str | None,
    ) -> str | None:
        if project_name:
            project_key = f"{default_key}_{project_name.upper()}"
            project_url = os.getenv(project_key, "").strip()
            if project_url:
                return project_url

        if url_slug:
            slug_key = f"{default_key}_{url_slug.upper()}"
            slug_url = os.getenv(slug_key, "").strip()
            if slug_url:
                return slug_url

        default_url = os.getenv(default_key, "").strip()
        return default_url or None

    def _send_dingtalk_markdown(
        self,
        *,
        webhook_url: str,
        secret: str | None,
        title: str,
        content: str,
    ) -> None:
        request_url = webhook_url
        if secret:
            request_url = self._sign_dingtalk_webhook(webhook_url, secret)
        self._post_json(
            request_url,
            {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content,
                },
                "at": {"isAtAll": False},
            },
        )

    def _send_wecom_markdown(self, *, webhook_url: str, title: str, content: str) -> None:
        formatted_content = self._format_wecom_markdown(content=content, title=title)
        self._post_json(
            webhook_url,
            {
                "msgtype": "markdown",
                "markdown": {"content": formatted_content},
            },
        )

    def _send_feishu_markdown(self, *, webhook_url: str, title: str, content: str) -> None:
        self._post_json(
            webhook_url,
            {
                "msg_type": "interactive",
                "card": {
                    "schema": "2.0",
                    "config": {"update_multi": True},
                    "header": {
                        "title": {"tag": "plain_text", "content": title},
                        "template": "blue",
                    },
                    "body": {
                        "direction": "vertical",
                        "padding": "12px 12px 12px 12px",
                        "elements": [
                            {
                                "tag": "markdown",
                                "content": content,
                                "text_align": "left",
                            }
                        ],
                    },
                },
            },
        )

    @staticmethod
    def _format_wecom_markdown(*, content: str, title: str) -> str:
        normalized_content = re.sub(r"#{5,}\s", "#### ", content)
        normalized_content = re.sub(r"\[(.*?)\]\((.*?)\)", r"[链接]\2", normalized_content)
        normalized_content = re.sub(r"<[^>]+>", "", normalized_content)
        return f"## {title}\n\n{normalized_content}"

    @staticmethod
    def _sign_dingtalk_webhook(webhook_url: str, secret: str) -> str:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(digest))
        separator = "&" if "?" in webhook_url else "?"
        return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"

    @staticmethod
    def _post_json(webhook_url: str, payload: dict[str, object]) -> None:
        request = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"notification request failed with status {response.status}")


class ReviewNotificationService:
    """负责发送审查完成后的 IM 通知。"""

    def __init__(
        self,
        sender: ReviewNotificationSender | None = None,
    ) -> None:
        self.sender = sender or ReviewNotificationSender()

    def deliver(self, *, record: ReviewRecord) -> None:
        content = self._build_content(record)
        title = self._build_title(record)
        project_name = record.project_name_snapshot
        url_slug = record.url_slug
        webhook_data = record.webhook_data

        project = record.project
        bot = project.default_bot if project is not None else None
        if bot is not None:
            self.sender.send(
                bot_type=bot.bot_type,
                webhook_url=bot.webhook_url,
                secret=self._resolve_bot_secret(bot),
                content=content,
                title=title,
                project_name=project_name,
                url_slug=url_slug,
                webhook_data=webhook_data,
            )
            return

        self.sender.send_env_fallback(
            content=content,
            title=title,
            project_name=project_name,
            url_slug=url_slug,
            webhook_data=webhook_data,
        )

    def _resolve_bot_secret(self, bot: NotificationBot) -> str | None:
        resolver = getattr(self.sender, "resolve_bot_secret", None)
        if callable(resolver):
            return resolver(bot)
        return None

    @staticmethod
    def _build_title(record: ReviewRecord) -> str:
        if record.event_type == "push":
            return f"{record.project_name_snapshot} Push Event"
        if record.event_type == "pull_request":
            return "Pull Request Review"
        return "Merge Request Review"

    @classmethod
    def _build_content(cls, record: ReviewRecord) -> str:
        header = cls._build_header(record)
        branch_lines = cls._build_branch_lines(record)
        commit_messages = cls._format_commit_messages(record.commit_messages)
        detail_lines = [
            header,
            "",
            f"- **提交者:** {record.author}",
        ]
        if record.title:
            detail_lines.append(f"- **标题:** {record.title}")
        detail_lines.extend(branch_lines)
        if record.url:
            detail_lines.append(f"- [查看详情]({record.url})")
        if commit_messages:
            detail_lines.append(f"- **提交信息:** {commit_messages}")
        detail_lines.extend(
            [
                "",
                "- **AI Review 结果:**",
                "",
                record.review_result or "",
            ]
        )
        return "\n".join(detail_lines).strip()

    @staticmethod
    def _build_header(record: ReviewRecord) -> str:
        project_name = record.project_name_snapshot
        if record.event_type == "push":
            return f"### {project_name}: Push"
        if record.event_type == "pull_request":
            return f"### {project_name}: Pull Request"
        return f"### {project_name}: Merge Request"

    @staticmethod
    def _build_branch_lines(record: ReviewRecord) -> list[str]:
        if record.event_type == "push":
            return [f"- **分支:** {record.branch or '-'}"]

        return [
            f"- **源分支:** {record.source_branch or '-'}",
            f"- **目标分支:** {record.target_branch or '-'}",
        ]

    @staticmethod
    def _format_commit_messages(messages: list[str] | None) -> str:
        if not messages:
            return ""
        return "；".join(message.strip() for message in messages if message and message.strip())
