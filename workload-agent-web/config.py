from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-sonnet-4-6", alias="CLAUDE_MODEL")

    # Gmail (IMAP with App Password — no OAuth needed)
    gmail_address: str = Field("", alias="GMAIL_ADDRESS")
    gmail_app_password: str = Field("", alias="GMAIL_APP_PASSWORD")

    # Outlook (IMAP)
    outlook_address: str = Field("", alias="OUTLOOK_ADDRESS")
    outlook_password: str = Field("", alias="OUTLOOK_PASSWORD")

    # Asana
    asana_access_token: str = Field("", alias="ASANA_ACCESS_TOKEN")
    asana_workspace_gid: str = Field("", alias="ASANA_WORKSPACE_GID")

    # App
    api_key: str = Field("change-me", alias="API_KEY")
    email_lookback_hours: int = Field(24, alias="EMAIL_LOOKBACK_HOURS")
    db_path: str = Field("workload.db", alias="DB_PATH")


settings = Settings()
