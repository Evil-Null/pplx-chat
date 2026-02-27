import logging
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Project root: pplx-chat/ (3 levels up from this file: config.py → pplx_chat/ → src/ → pplx-chat/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


MODELS = {
    "sonar": {
        "name": "Sonar",
        "description": "Fast web search, $1/$1 per M tokens",
        "input_cost": 1.0,
        "output_cost": 1.0,
    },
    "sonar-pro": {
        "name": "Sonar Pro",
        "description": "Multi-step search, $3/$15 per M tokens",
        "input_cost": 3.0,
        "output_cost": 15.0,
    },
    "sonar-reasoning-pro": {
        "name": "Sonar Reasoning Pro",
        "description": "Deep reasoning, $2/$8 per M tokens",
        "input_cost": 2.0,
        "output_cost": 8.0,
    },
    "sonar-deep-research": {
        "name": "Sonar Deep Research",
        "description": "Exhaustive research, $2/$8 per M tokens",
        "input_cost": 2.0,
        "output_cost": 8.0,
    },
}


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PPLX_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_key: str = Field(..., alias="PPLX_API_KEY")
    api_base_url: str = "https://api.perplexity.ai"

    # Model defaults
    default_model: str = "sonar"
    temperature: float = 0.2
    max_tokens: int = 4096
    top_p: float = 0.9

    # Search defaults
    search_mode: str = "web"
    search_recency_filter: str | None = None
    search_domain_filter: list[str] = []
    search_context_size: str = "medium"
    return_citations: bool = True
    return_related_questions: bool = True
    return_images: bool = False

    # System prompt
    system_prompt: str = "Be helpful, accurate, and concise. Provide sources when possible."

    # Paths
    db_path: Path = Path("~/.local/share/pplx-chat/history.db").expanduser()
    log_path: Path = Path("~/.local/share/pplx-chat/pplx.log").expanduser()
    export_dir: Path = Path("~/Desktop").expanduser()

    # UI
    show_cost: bool = True
    show_citations: bool = True
    show_related: bool = True

    @field_validator("default_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if v not in MODELS:
            valid = ", ".join(MODELS.keys())
            raise ValueError(f"Unknown model '{v}'. Valid models: {valid}")
        return v


def load_config() -> AppConfig:
    """Load config from .env, then overlay with yaml if it exists."""
    yaml_path = Path("~/.config/pplx-chat/config.yaml").expanduser()
    yaml_overrides = {}
    if yaml_path.exists():
        try:
            with open(yaml_path, encoding="utf-8") as f:
                yaml_overrides = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.warning("Invalid YAML config, using defaults: %s", e)
        except OSError as e:
            logger.warning("Cannot read config file, using defaults: %s", e)
    return AppConfig(**yaml_overrides)
