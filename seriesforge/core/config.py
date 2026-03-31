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


def load_config(project_path: Path) -> ProjectConfig:
    """Load configuration from seriesforge.yaml."""
    config_file = project_path / "seriesforge.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file) as f:
        data = yaml.safe_load(f)
    
    return ProjectConfig(**data)


def save_config(config: ProjectConfig, project_path: Path):
    """Save configuration to seriesforge.yaml."""
    config_file = project_path / "seriesforge.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config.model_dump(exclude_none=True), f, default_flow_style=False)
