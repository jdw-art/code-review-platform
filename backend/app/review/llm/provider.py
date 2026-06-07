from app.llm.provider import PROVIDER_ENV_CONFIG, LLMConfig, load_llm_config


ReviewerLLMConfig = LLMConfig


def load_reviewer_llm_config() -> ReviewerLLMConfig:
    return load_llm_config(default_provider="anthropic")
