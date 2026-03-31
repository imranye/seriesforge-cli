"""Pipeline orchestration."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.core.manifests import (
    EpisodeManifest,
    create_episode_manifest,
    save_manifest,
)


STAGES = [
    {"name": "bible", "command": "bible generate", "required_env": ["OPENAI_API_KEY"]},
    {"name": "arc", "command": "arc generate", "required_env": ["OPENAI_API_KEY"]},
    {"name": "outline", "command": "episode outline", "required_env": ["OPENAI_API_KEY"]},
    {"name": "script", "command": "script write", "required_env": ["ANTHROPIC_API_KEY"]},
    {"name": "revision", "command": "revision run", "required_env": ["ANTHROPIC_API_KEY"]},
    {"name": "shots", "command": "shots plan", "required_env": ["OPENAI_API_KEY"]},
    {"name": "voice", "command": "voice generate", "required_env": []},
    {"name": "video", "command": "video generate", "required_env": []},
    {"name": "edit", "command": "edit assemble", "required_env": []},
    {"name": "qc", "command": "qc run", "required_env": []},
    {"name": "export", "command": "export package", "required_env": []},
]


def check_env_vars(required: List[str]) -> bool:
    """Check if required environment variables are set."""
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        typer.echo(f"Missing environment variables: {', '.join(missing)}")
        return False
    return True


def run_stage(stage: dict, episode: int, season: int, auto: bool) -> bool:
    """Run a single pipeline stage."""
    name = stage["name"]
    command = stage["command"]
    
    typer.echo(f"\n{'='*60}")
    typer.echo(f"Stage: {name.upper()}")
    typer.echo(f"{'='*60}")
    
    # Check required env vars
    if not check_env_vars(stage.get("required_env", [])):
        if auto:
            typer.echo(f"Skipping {name} due to missing env vars")
            return False
        raise typer.Exit(code=1)
    
    # Build command
    cmd_parts = ["seriesforge"]
    if " " in command:
        cmd_parts.extend(command.split())
    cmd_parts.extend([f"--episode", str(episode), f"--season", str(season)])
    
    # Add --auto flag if in auto mode
    if auto and name not in ["bible", "arc"]:
        cmd_parts.append("--auto")
    
    typer.echo(f"Running: {' '.join(cmd_parts)}")
    
    # TODO: Actually run the subcommand
    # For now, just simulate
    typer.echo(f"✓ {name} stage complete (simulated)")
    
    return True


def create_run_manifest(
    project_path: Path,
    episode: int,
    season: int,
    run_id: str,
):
    """Create a pipeline run manifest."""
    runs_path = project_path / "runs" / run_id
    runs_path.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "run_id": run_id,
        "project": project_path.name,
        "episode": episode,
        "season": season,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "stages": [],
        "status": "running",
    }
    
    manifest_path = runs_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest_path, manifest


def update_run_manifest(manifest_path: Path, stage_name: str, status: str):
    """Update run manifest with stage completion."""
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    manifest["stages"].append({
        "name": stage_name,
        "status": status,
        "completed_at": datetime.utcnow().isoformat(),
    })
    
    if status == "failed":
        manifest["status"] = "failed"
        manifest["completed_at"] = datetime.utcnow().isoformat()
    elif all(s["status"] == "completed" for s in manifest["stages"]):
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.utcnow().isoformat()
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)


def run_pipeline_cli(
    episode: int = 1,
    season: int = 1,
    auto: bool = False,
    from_stage: Optional[str] = None,
    to_stage: Optional[str] = None,
):
    """CLI entry point for pipeline execution."""
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    # Generate run ID
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Create run manifest
    manifest_path, manifest = create_run_manifest(project_path, episode, season, run_id)
    typer.echo(f"Pipeline run: {run_id}")
    typer.echo(f"Episode: S{season}E{episode}")
    typer.echo(f"Auto-mode: {'yes' if auto else 'no'}")
    
    # Filter stages if --from/--to specified
    stages = STAGES
    if from_stage:
        from_idx = next((i for i, s in enumerate(STAGES) if s["name"] == from_stage), 0)
        stages = stages[from_idx:]
    if to_stage:
        to_idx = next((i for i, s in enumerate(STAGES) if s["name"] == to_stage), len(STAGES))
        stages = stages[:to_idx + 1]
    
    # Run stages
    failed = False
    for stage in stages:
        if failed:
            typer.echo(f"Skipping {stage['name']} (previous stage failed)")
            continue
        
        try:
            success = run_stage(stage, episode, season, auto)
            status = "completed" if success else "failed"
            update_run_manifest(manifest_path, stage["name"], status)
            
            if not success:
                failed = True
                typer.echo(f"✗ {stage['name']} stage failed")
        except Exception as e:
            failed = True
            update_run_manifest(manifest_path, stage["name"], "failed")
            typer.echo(f"✗ {stage['name']} stage error: {e}")
        
        # Ask for approval in manual mode
        if not auto and not failed:
            typer.echo(f"\n{stage['name']} complete. Continue?")
            if not typer.confirm("Proceed to next stage?"):
                typer.echo("Pipeline paused. Use 'seriesforge pipeline resume' to continue.")
                break
    
    # Summary
    typer.echo(f"\n{'='*60}")
    typer.echo("PIPELINE SUMMARY")
    typer.echo(f"{'='*60}")
    completed = sum(1 for s in manifest["stages"] if s["status"] == "completed")
    failed_count = sum(1 for s in manifest["stages"] if s["status"] == "failed")
    typer.echo(f"Stages completed: {completed}/{len(stages)}")
    typer.echo(f"Stages failed: {failed_count}")
    typer.echo(f"Run manifest: {manifest_path}")
    
    if failed:
        raise typer.Exit(code=1)
