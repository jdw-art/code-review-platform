from app.integrations.base import BaseIntegrationAdapter, NormalizedWebhookEvent
from app.integrations.github import GitHubIntegrationAdapter
from app.integrations.gitlab import GitLabIntegrationAdapter

INTEGRATION_ADAPTERS: dict[str, type[BaseIntegrationAdapter]] = {
    "gitlab": GitLabIntegrationAdapter,
    "github": GitHubIntegrationAdapter,
}

__all__ = [
    "BaseIntegrationAdapter",
    "GitHubIntegrationAdapter",
    "GitLabIntegrationAdapter",
    "INTEGRATION_ADAPTERS",
    "NormalizedWebhookEvent",
]
