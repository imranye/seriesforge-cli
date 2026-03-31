"""Core data models for SeriesForge."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class StageStatus(str, Enum):
    """Pipeline stage status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Character(BaseModel):
    """Character definition."""
    name: str
    description: str
    voice: Optional[str] = None
    wardrobe: Optional[str] = None
    relationships: Dict[str, str] = Field(default_factory=dict)


class Location(BaseModel):
    """Location definition."""
    name: str
    description: str
    visual_style: Optional[str] = None


class ShowBible(BaseModel):
    """Show bible containing world-building elements."""
    title: str
    concept: str
    genre: str
    tone: str
    characters: List[Character] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    lore: Optional[str] = None
    running_jokes: List[str] = Field(default_factory=list)


class EpisodeOutline(BaseModel):
    """Episode outline with beats."""
    episode_number: int
    title: Optional[str] = None
    logline: str
    beats: List[str] = Field(default_factory=list)


class Scene(BaseModel):
    """Scene within an episode."""
    scene_number: int
    heading: str  # INT./EXT. location - time
    action: str
    dialogue: List[Dict[str, str]] = Field(default_factory=list)  # character -> lines


class Shot(BaseModel):
    """Shot definition for production."""
    shot_number: int
    scene_number: int
    shot_type: str  # CU, WS, MS, etc.
    camera_movement: Optional[str] = None
    prompt: str  # Prompt for video generation
    duration_seconds: int = 5
    status: StageStatus = StageStatus.PENDING


class Script(BaseModel):
    """Complete episode script."""
    episode_number: int
    title: Optional[str] = None
    scenes: List[Scene] = Field(default_factory=list)
    format: str = "fountain"


class Asset(BaseModel):
    """Generated asset tracking."""
    asset_id: str
    asset_type: str  # video, audio, image
    path: str
    scene_number: Optional[int] = None
    shot_number: Optional[int] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineRun(BaseModel):
    """Pipeline execution tracking."""
    run_id: str
    project: str
    episode: int
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    stages: List[Dict[str, str]] = Field(default_factory=list)
    status: StageStatus = StageStatus.RUNNING
