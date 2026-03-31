"""Export episode package."""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import typer


def export_package_cli(
    episode: int = 1,
    season: int = 1,
    include_source: bool = False,
):
    """CLI entry point for export."""
    project_path = Path.cwd()
    
    try:
        from seriesforge.core.config import load_config
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    exports_path = episode_path / "exports"
    exports_path.mkdir(exist_ok=True)
    
    typer.echo(f"Exporting episode {episode}...")
    
    # Collect assets
    assets = {
        "script": episode_path / f"script_ep{episode:02d}.fountain",
        "outline": episode_path / "outline.md",
        "shots": episode_path / "shots.yaml",
        "video_manifest": episode_path / "video" / "manifest.json",
        "audio_manifest": episode_path / "audio" / "manifest.json",
        "edit_manifest": episode_path / "edits" / "manifest.json",
        "rough_cut": episode_path / "edits" / f"rough_cut_ep{episode:02d}.mp4",
    }
    
    # Check what exists
    existing = {k: v for k, v in assets.items() if v.exists()}
    missing = {k: v for k, v in assets.items() if not v.exists()}
    
    typer.echo(f"  Found: {len(existing)} assets")
    if missing:
        typer.echo(f"  Missing: {', '.join(missing.keys())}")
    
    # Create export package
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    package_name = f"{config.name}_s{season}e{episode}_{timestamp}"
    package_path = exports_path / package_name
    package_path.mkdir()
    
    # Copy assets
    for name, asset_path in existing.items():
        dest = package_path / asset_path.name
        if asset_path.is_file():
            shutil.copy(asset_path, dest)
            typer.echo(f"  ✓ {name}")
    
    # Copy video files if they exist
    video_path = episode_path / "video"
    if video_path.exists():
        video_dest = package_path / "videos"
        video_dest.mkdir()
        for video_file in video_path.glob("*.mp4"):
            shutil.copy(video_file, video_dest)
    
    # Copy audio files if they exist
    audio_path = episode_path / "audio"
    if audio_path.exists():
        audio_dest = package_path / "audio"
        audio_dest.mkdir()
        for audio_file in audio_path.glob("*.mp3"):
            shutil.copy(audio_file, audio_dest)
    
    # Create export manifest
    export_manifest = {
        "project": config.name,
        "season": season,
        "episode": episode,
        "exported_at": datetime.utcnow().isoformat(),
        "assets": list(existing.keys()),
        "missing": list(missing.keys()),
        "package_path": str(package_path.absolute()),
    }
    
    manifest_path = package_path / "export_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(export_manifest, f, indent=2)
    
    # Create ZIP archive
    zip_path = exports_path / f"{package_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(package_path.parent)
                zipf.write(file_path, arcname)
    
    typer.echo(f"\n✓ Export complete")
    typer.echo(f"  Package: {package_path}")
    typer.echo(f"  Archive: {zip_path}")
    typer.echo(f"  Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
