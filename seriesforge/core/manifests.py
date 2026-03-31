"""Asset manifest system for tracking generated assets."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import json
import yaml


class AssetManifest(BaseModel):
    """Manifest for tracking a single asset."""
    asset_id: str
    asset_type: str  # video, audio, image, subtitle
    episode: int
    scene_number: Optional[int] = None
    shot_number: Optional[int] = None
    path: str
    filename: str
    size_bytes: int = 0
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None  # "1920x1080", "1080x1920"
    format: str = ""  # mp4, wav, png, srt
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    provider: str = ""  # kling, runway, elevenlabs
    prompt: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    status: str = "generated"  # generated, failed, approved, rejected


class EpisodeManifest(BaseModel):
    """Manifest for all assets in an episode."""
    episode: int
    season: int = 1
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assets: List[AssetManifest] = Field(default_factory=list)
    stages: Dict[str, str] = Field(default_factory=dict)  # stage_name -> status
    
    def add_asset(self, asset: AssetManifest):
        """Add an asset to the manifest."""
        self.assets.append(asset)
        self.updated_at = datetime.utcnow()
    
    def get_assets_by_type(self, asset_type: str) -> List[AssetManifest]:
        """Get all assets of a specific type."""
        return [a for a in self.assets if a.asset_type == asset_type]
    
    def get_asset_by_id(self, asset_id: str) -> Optional[AssetManifest]:
        """Get a specific asset by ID."""
        for asset in self.assets:
            if asset.asset_id == asset_id:
                return asset
        return None


class ProjectManifest(BaseModel):
    """Top-level project manifest."""
    project_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    episodes: Dict[int, str] = Field(default_factory=dict)  # episode_num -> path
    total_assets: int = 0
    total_size_bytes: int = 0


def create_episode_manifest(
    episode: int,
    season: int = 1,
    episode_path: Optional[Path] = None,
) -> EpisodeManifest:
    """Create a new episode manifest."""
    return EpisodeManifest(episode=episode, season=season)


def save_manifest(manifest: EpisodeManifest, path: Path):
    """Save episode manifest to JSON."""
    data = manifest.model_dump()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_manifest(path: Path) -> EpisodeManifest:
    """Load episode manifest from JSON."""
    with open(path) as f:
        data = json.load(f)
    return EpisodeManifest(**data)


def create_asset_entry(
    episode_path: Path,
    asset_type: str,
    filename: str,
    episode: int,
    scene_number: Optional[int] = None,
    shot_number: Optional[int] = None,
    provider: str = "",
    prompt: Optional[str] = None,
) -> AssetManifest:
    """Create an asset manifest entry."""
    asset_path = episode_path / filename
    size = asset_path.stat().st_size if asset_path.exists() else 0
    
    import uuid
    asset_id = f"{asset_type}_{episode}_{scene_number or 0}_{shot_number or 0}_{uuid.uuid4().hex[:8]}"
    
    return AssetManifest(
        asset_id=asset_id,
        asset_type=asset_type,
        episode=episode,
        scene_number=scene_number,
        shot_number=shot_number,
        path=str(asset_path.absolute()),
        filename=filename,
        size_bytes=size,
        provider=provider,
        prompt=prompt,
    )
