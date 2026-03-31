"""Shot planning from script."""

import asyncio
import json
import os
from pathlib import Path

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.core.models import Shot, StageStatus
from seriesforge.providers.llm import ChatMessage, create_provider


SHOT_PLAN_PROMPT = """
You are an expert film director and DP. Break this script into shots for AI video generation.

Script:
{script}

Visual Style: {style}

Output a valid JSON array of shots. Each shot should have:
{{
  "shot_number": 1,
  "scene_number": 1,
  "shot_type": "CU" or "MS" or "WS" or "ELS" etc.,
  "camera_movement": "static" or "pan right" or "dolly in" etc.,
  "description": "what happens in this shot",
  "prompt": "detailed prompt for AI video generation including visual style, lighting, camera, action",
  "duration_seconds": 5,
  "characters_in_shot": ["char1"],
  "dialogue_lines": ["line 1"],
  "continuity_notes": "wardrobe, props, lighting consistency"
}}

Create shots that:
- Are 3-8 seconds each (optimal for AI video)
- Have clear, simple actions
- Include specific visual details in prompts
- Maintain character consistency
- Work well with current AI video generators (Kling, Runway, Pika)

Output ONLY the JSON array, no explanations.
"""


async def plan_shots_llm(
    script_path: Path,
    bible_path: Path,
    provider_name: str = "openai",
    api_key: str = "",
) -> list:
    """Plan shots from script using LLM."""
    script_content = script_path.read_text() if script_path.exists() else ""
    
    # Get style from bible
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    style = "cinematic, natural lighting"  # TODO: extract from bible
    
    prompt = SHOT_PLAN_PROMPT.format(script=script_content[:12000], style=style)
    
    provider = create_provider(provider_name, {"api_key": api_key})
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON array only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.6, max_tokens=12000)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    return json.loads(content)


def save_shots(shots: list, episode_path: Path, episode_num: int):
    """Save shot list to YAML and JSON."""
    # YAML for human readability
    yaml_data = {
        "episode": episode_num,
        "shots": [
            {
                "shot_number": s["shot_number"],
                "scene_number": s["scene_number"],
                "shot_type": s["shot_type"],
                "camera_movement": s.get("camera_movement"),
                "description": s["description"],
                "prompt": s["prompt"],
                "duration_seconds": s.get("duration_seconds", 5),
                "characters_in_shot": s.get("characters_in_shot", []),
                "dialogue_lines": s.get("dialogue_lines", []),
                "continuity_notes": s.get("continuity_notes"),
                "status": "pending",
            }
            for s in shots
        ],
    }
    
    yaml_path = episode_path / "shots.yaml"
    with open(yaml_path, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False)
    
    # JSON for programmatic access
    json_path = episode_path / "shots.json"
    with open(json_path, 'w') as f:
        json.dump(yaml_data, f, indent=2)
    
    return yaml_path, json_path


def plan_shots_cli(
    episode: int = 1,
    season: int = 1,
    provider: str = "openai",
):
    """CLI entry point for shot planning."""
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    bible_path = project_path / "bible" / "show_bible.md"
    if not bible_path.exists():
        typer.echo("Error: Show bible not found.")
        raise typer.Exit(code=1)
    
    script_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
        / f"script_ep{episode:02d}.fountain"
    )
    if not script_path.exists():
        typer.echo(f"Error: Episode {episode} script not found. Run 'seriesforge script write' first.")
        raise typer.Exit(code=1)
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        typer.echo("Error: OPENAI_API_KEY not set.")
        raise typer.Exit(code=1)
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    
    typer.echo(f"Planning shots for episode {episode}...")
    
    try:
        shots = asyncio.run(plan_shots_llm(script_path, bible_path, provider, api_key))
    except Exception as e:
        typer.echo(f"Error planning shots: {e}")
        raise typer.Exit(code=1)
    
    yaml_path, json_path = save_shots(shots, episode_path, episode)
    
    typer.echo(f"✓ Shot list generated for episode {episode}")
    typer.echo(f"  YAML: {yaml_path}")
    typer.echo(f"  JSON: {json_path}")
    typer.echo(f"  Shots: {len(shots)}")
    
    # Calculate total duration
    total_duration = sum(s.get("duration_seconds", 5) for s in shots)
    typer.echo(f"  Estimated runtime: {total_duration} seconds ({total_duration/60:.1f} min)")
