"""Core configuration and models for SeriesForge."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from pathlib import Path
import yaml


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""
    primary: str
    fallback: Optional[str] = None
    api_key: Optional[str] = Field(None, exclude=True)


class ProvidersConfig(BaseModel):
    """Provider configuration for all service types."""
    llm: ProviderConfig = Field(default_factory=lambda: ProviderConfig(primary="openai"))
    video: Optional[ProviderConfig] = None
    tts: Optional[ProviderConfig] = None
    music: Optional[ProviderConfig] = None
    edit: ProviderConfig = Field(default_factory=lambda: ProviderConfig(primary="ffmpeg"))


class StyleConfig(BaseModel):
    """Style and tone configuration."""
    tone: str = "cinematic"
    pacing: str = "medium"
    aspect_ratio: str = "16:9"
    continuity_strictness: str = "high"


class WorkflowConfig(BaseModel):
    """Workflow and pipeline configuration."""
    approval_mode: str = "manual"  # manual, semi-auto, auto
    auto_retry_failed_jobs: bool = True
    max_parallel_renders: int = 4


class ProjectConfig(BaseModel):
    """Main project configuration."""
    name: str
    format: str = "episodic"
    genre: Optional[str] = None
    target_runtime_minutes: int = 5
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    class Config:
        arbitrary_types_allowed = True


def load_config(project_path: Path) -> dict:
    """Load configuration from seriesforge.yaml and environment.
    
    Returns a dict with config + API keys from environment.
    """
    import os
    
    config_file = project_path / "seriesforge.yaml"
    data = {}
    
    if config_file.exists():
        with open(config_file) as f:
            data = yaml.safe_load(f) or {}
    
    # Add API keys from environment
    data["api_keys"] = data.get("api_keys", {})
    
    if "anthropic_api_key" not in data["api_keys"]:
        data["api_keys"]["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")
    
    if "openai_api_key" not in data["api_keys"]:
        data["api_keys"]["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")
    
    if "openrouter_api_key" not in data["api_keys"]:
        data["api_keys"]["openrouter_api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
    
    return data


def get_api_key(config: dict, provider: str) -> str:
    """Get API key for a provider from config or environment."""
    import os
    
    api_keys = config.get("api_keys", {})
    
    if provider == "anthropic":
        return api_keys.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    elif provider == "openai":
        return api_keys.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
    elif provider == "openrouter":
        return api_keys.get("openrouter_api_key", os.environ.get("OPENROUTER_API_KEY", ""))
    
    return ""


def save_config(config: ProjectConfig, project_path: Path):
    """Save configuration to seriesforge.yaml."""
    config_file = project_path / "seriesforge.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config.model_dump(exclude_none=True), f, default_flow_style=False)
