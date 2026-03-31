"""Video generation from shots."""

import asyncio
import json
import os
from pathlib import Path

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.providers.video import create_video_provider


def load_shots(episode_path: Path) -> list:
    """Load shot list from YAML."""
    shots_yaml = episode_path / "shots.yaml"
    if not shots_yaml.exists():
        raise FileNotFoundError(f"Shots file not found: {shots_yaml}")
    
    with open(shots_yaml) as f:
        data = yaml.safe_load(f)
    
    return data.get("shots", [])


async def render_shot(
    shot: dict,
    video_provider,
    output_path: Path,
) -> dict:
    """Render a single shot."""
    shot_num = shot["shot_number"]
    prompt = shot["prompt"]
    duration = shot.get("duration_seconds", 5)
    
    typer.echo(f"  Rendering shot {shot_num}...")
    
    try:
        result = await video_provider.generate(
            prompt=prompt,
            duration=duration,
        )
        
        # Save video
        filename = f"shot_{shot_num:03d}.mp4"
        video_path = output_path / filename
        
        # Download video from URL
        if result.video_url:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(result.video_url)
                with open(video_path, 'wb') as f:
                    f.write(response.content)
        elif result.video_path:
            import shutil
            shutil.copy(result.video_path, video_path)
        
        return {
            "shot_number": shot_num,
            "status": "completed",
            "path": str(video_path),
            "duration": duration,
        }
    
    except Exception as e:
        return {
            "shot_number": shot_num,
            "status": "failed",
            "error": str(e),
        }


def generate_video_cli(
    episode: int = 1,
    season: int = 1,
    provider: str = "kling",
    failed_only: bool = False,
):
    """CLI entry point for video generation."""
    project_path = Path.cwd()
    
    try:
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
    video_path = episode_path / "video"
    video_path.mkdir(exist_ok=True)
    
    # Load shots
    shots = load_shots(episode_path)
    
    if failed_only:
        # Check for existing videos and skip them
        existing = set(f.stem for f in video_path.glob("*.mp4"))
        shots = [s for s in shots if f"shot_{s['shot_number']:03d}" not in existing]
        typer.echo(f"Rendering {len(shots)} shots (skipping existing)")
    
    typer.echo(f"Generating video for episode {episode}...")
    typer.echo(f"Shots to render: {len(shots)}")
    
    if not shots:
        typer.echo("No shots to render.")
        return
    
    # Get API key
    api_key = os.environ.get("KLING_API_KEY", "")
    if not api_key and provider == "runway":
        api_key = os.environ.get("RUNWAY_API_KEY", "")
    
    if not api_key:
        typer.echo(f"Warning: {provider.upper()}_API_KEY not set.")
        typer.echo("Video generation will fail without API key.")
        typer.echo("Generating placeholder manifest...")
        
        # Create placeholder manifest
        manifest = {
            "episode": episode,
            "provider": provider,
            "shots": [],
            "total_duration": 0,
            "note": "API key not set - no videos generated",
        }
        with open(video_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        return
    
    # Create video provider
    video_provider = create_video_provider(provider, {"api_key": api_key})
    
    # Render shots in parallel (with rate limiting)
    typer.echo(f"\nRendering {len(shots)} shots...")
    
    # Create tasks for all shots
    tasks = [
        render_shot(shot, video_provider, video_path)
        for shot in shots
    ]
    
    # Run with concurrency limit
    import asyncio
    
    async def render_with_limit(tasks, limit=4):
        """Render tasks with concurrency limit."""
        semaphore = asyncio.Semaphore(limit)
        
        async def bounded_render(task):
            async with semaphore:
                return await task
        
        return await asyncio.gather(*[bounded_render(t) for t in tasks])
    
    results = asyncio.run(render_with_limit(tasks, limit=4))
    
    # Save manifest
    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "failed"]
    
    manifest = {
        "episode": episode,
        "provider": provider,
        "shots": results,
        "total_duration": sum(r.get("duration", 0) for r in completed),
        "completed": len(completed),
        "failed": len(failed),
    }
    
    with open(video_path / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    typer.echo(f"\n✓ Video generation complete")
    typer.echo(f"  Completed: {len(completed)}/{len(results)}")
    typer.echo(f"  Failed: {len(failed)}")
    typer.echo(f"  Total duration: {manifest['total_duration']}s")
    typer.echo(f"  Output: {video_path}")
    
    if failed:
        typer.echo("\nFailed shots:")
        for f in failed:
            typer.echo(f"  Shot {f['shot_number']}: {f.get('error', 'unknown')}")
