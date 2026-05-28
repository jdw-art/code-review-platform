from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.db.models import LlmModel, NotificationBot, Project, ProjectTemplate, User
from app.db.session import SessionLocal
from app.services.bootstrap import bootstrap_initial_admin
from app.services.llm_model_service import mask_secret


@dataclass(frozen=True)
class SeedSummary:
    project_templates: int
    projects: int
    llm_models: int
    notification_bots: int


def _get_admin_user(session, settings: Settings) -> User:
    admin = session.scalar(
        select(User).where(User.username == settings.bootstrap_admin_username)
    )
    if admin is None:
        raise RuntimeError("未找到 bootstrap 超级管理员，请先完成启动初始化。")
    return admin


def _ensure_template(
    session,
    *,
    code: str,
    admin_id: int,
    name: str,
    description: str,
    file_extensions: list[str],
    review_prompt_template: str,
    prompt_metadata: dict[str, object],
) -> ProjectTemplate:
    template = session.scalar(select(ProjectTemplate).where(ProjectTemplate.code == code))
    if template is None:
        template = ProjectTemplate(
            name=name,
            code=code,
            description=description,
            file_extensions=file_extensions,
            review_prompt_template=review_prompt_template,
            prompt_metadata=prompt_metadata,
            is_system=False,
            is_active=True,
            created_by=admin_id,
        )
        session.add(template)
        session.flush()
    return template


def _ensure_model(
    session,
    cipher: SecretCipher,
    *,
    model_code: str,
    name: str,
    provider: str,
    base_url: str,
    api_key: str,
    is_default: bool,
    temperature: float,
    max_tokens: int,
    top_p: float,
    prompt_template: str,
) -> LlmModel:
    model = session.scalar(select(LlmModel).where(LlmModel.model_code == model_code))
    if model is None:
        can_be_default = is_default and session.scalar(
            select(LlmModel.id).where(LlmModel.is_default.is_(True))
        ) is None
        model = LlmModel(
            name=name,
            provider=provider,
            model_code=model_code,
            base_url=base_url,
            api_key_encrypted=cipher.encrypt_text(api_key),
            api_key_masked=mask_secret(api_key),
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            prompt_template=prompt_template,
            is_default=can_be_default,
            is_active=True,
            last_test_status="success",
            last_test_message="mock seed connected",
        )
        session.add(model)
        session.flush()
    return model


def _ensure_bot(
    session,
    cipher: SecretCipher,
    *,
    name: str,
    bot_type: str,
    webhook_url: str,
    secret: str,
    mention_strategy: str,
    template_config: dict[str, object],
) -> NotificationBot:
    bot = session.scalar(select(NotificationBot).where(NotificationBot.name == name))
    if bot is None:
        bot = NotificationBot(
            name=name,
            bot_type=bot_type,
            webhook_url=webhook_url,
            secret_encrypted=cipher.encrypt_text(secret),
            secret_masked=mask_secret(secret),
            mention_strategy=mention_strategy,
            template_config=template_config,
            is_active=True,
            last_test_status="success",
            last_test_message="mock seed connected",
        )
        session.add(bot)
        session.flush()
    return bot


def _ensure_project(
    session,
    *,
    key: str,
    name: str,
    platform_type: str,
    repo_url: str,
    default_branch: str,
    description: str,
    template_id: int | None,
    default_model_id: int | None,
    default_bot_id: int | None,
    review_enabled: bool,
    created_by: int,
    settings: dict[str, object],
) -> Project:
    project = session.scalar(select(Project).where(Project.key == key))
    if project is None:
        project = Project(
            name=name,
            key=key,
            platform_type=platform_type,
            repo_url=repo_url,
            default_branch=default_branch,
            description=description,
            template_id=template_id,
            default_model_id=default_model_id,
            default_bot_id=default_bot_id,
            review_enabled=review_enabled,
            is_active=True,
            created_by=created_by,
            settings=settings,
        )
        session.add(project)
        session.flush()
    return project


def seed_dev_admin_console_data() -> SeedSummary:
    settings = Settings()
    bootstrap_initial_admin(settings=settings)
    cipher = SecretCipher(settings.secret_encryption_key)

    with SessionLocal() as session:
        admin = _get_admin_user(session, settings)

        python_template = _ensure_template(
            session,
            code="demo-python-template",
            admin_id=admin.id,
            name="Python 服务模板",
            description="用于本地开发验证的 Python 审查模板。",
            file_extensions=[".py", ".toml", ".yaml"],
            review_prompt_template="请使用中文审查 Python 服务端改动，重点关注异常处理、并发安全与数据库访问。",
            prompt_metadata={"language": "zh-CN", "scene": "backend"},
        )
        frontend_template = _ensure_template(
            session,
            code="demo-react-template",
            admin_id=admin.id,
            name="React 前端模板",
            description="用于本地开发验证的 React 审查模板。",
            file_extensions=[".ts", ".tsx", ".css"],
            review_prompt_template="请使用中文审查 React + TypeScript 改动，重点关注状态管理、副作用与类型安全。",
            prompt_metadata={"language": "zh-CN", "scene": "frontend"},
        )

        default_model = _ensure_model(
            session,
            cipher,
            model_code="gpt-4.1",
            name="OpenAI GPT-4.1",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-demo-openai-key",
            is_default=True,
            temperature=0.2,
            max_tokens=4096,
            top_p=0.9,
            prompt_template="请使用中文输出结构化代码审查结论。",
        )
        _ensure_model(
            session,
            cipher,
            model_code="deepseek-chat",
            name="DeepSeek Chat",
            provider="deepseek",
            base_url="https://api.deepseek.com",
            api_key="sk-demo-deepseek-key",
            is_default=False,
            temperature=0.3,
            max_tokens=8192,
            top_p=0.95,
            prompt_template="请聚焦 correctness、security 和 maintainability。",
        )

        dingtalk_bot = _ensure_bot(
            session,
            cipher,
            name="钉钉默认机器人",
            bot_type="dingtalk",
            webhook_url="https://oapi.dingtalk.com/robot/send?access_token=demo",
            secret="demo-dingtalk-secret",
            mention_strategy="author",
            template_config={"channel": "dingtalk", "version": "v1"},
        )
        _ensure_bot(
            session,
            cipher,
            name="企业微信机器人",
            bot_type="wecom",
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo",
            secret="demo-wecom-secret",
            mention_strategy="none",
            template_config={"channel": "wecom", "version": "v1"},
        )

        _ensure_project(
            session,
            key="demo-api-service",
            name="Demo API Service",
            platform_type="gitlab",
            repo_url="https://gitlab.example.com/demo/api-service.git",
            default_branch="main",
            description="用于验证项目管理页面增改查的后端服务项目。",
            template_id=python_template.id,
            default_model_id=default_model.id,
            default_bot_id=dingtalk_bot.id,
            review_enabled=True,
            created_by=admin.id,
            settings={"language": "python", "owner": "backend"},
        )
        _ensure_project(
            session,
            key="demo-web-console",
            name="Demo Web Console",
            platform_type="github",
            repo_url="https://github.com/example/demo-web-console.git",
            default_branch="develop",
            description="用于验证项目管理页面增改查的前端项目。",
            template_id=frontend_template.id,
            default_model_id=default_model.id,
            default_bot_id=dingtalk_bot.id,
            review_enabled=False,
            created_by=admin.id,
            settings={"language": "typescript", "owner": "frontend"},
        )

        session.commit()

        return SeedSummary(
            project_templates=len(
                session.scalars(
                    select(ProjectTemplate.id).where(
                        ProjectTemplate.code.in_(
                            ["demo-python-template", "demo-react-template"]
                        )
                    )
                ).all()
            ),
            projects=len(
                session.scalars(
                    select(Project.id).where(
                        Project.key.in_(["demo-api-service", "demo-web-console"])
                    )
                ).all()
            ),
            llm_models=len(
                session.scalars(
                    select(LlmModel.id).where(
                        LlmModel.model_code.in_(["gpt-4.1", "deepseek-chat"])
                    )
                ).all()
            ),
            notification_bots=len(
                session.scalars(
                    select(NotificationBot.id).where(
                        NotificationBot.name.in_(["钉钉默认机器人", "企业微信机器人"])
                    )
                ).all()
            ),
        )


def main() -> None:
    summary = seed_dev_admin_console_data()
    print(
        "Seeded dev admin console data:",
        {
            "project_templates": summary.project_templates,
            "projects": summary.projects,
            "llm_models": summary.llm_models,
            "notification_bots": summary.notification_bots,
        },
    )


if __name__ == "__main__":
    main()
