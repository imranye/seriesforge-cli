"""Episode outline generation."""

import asyncio
import json
import os
from pathlib import Path

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.core.models import EpisodeOutline
from seriesforge.providers.llm import ChatMessage, create_provider


OUTLINE_PROMPT = """
You are an expert TV writer. Create a detailed episode outline.

Show Bible:
{bible}

Season Arc:
{arc}

Episode: {episode}
Episode Title: {ep_title}
Episode Logline: {ep_logline}

Output a valid JSON object with this structure:
{{
  "episode_number": {episode},
  "title": "{ep_title}",
  "logline": "{ep_logline}",
  "cold_open": "brief description of cold open if any",
  "acts": [
    {{
      "act_number": 1,
      "description": "what happens in this act",
      "beats": [
        {{
          "beat_number": 1,
          "description": "specific beat description",
          "location": "where it happens",
          "characters": ["char1", "char2"],
          "purpose": "why this beat matters"
        }}
      ]
    }}
  ],
  "tag": "brief tag/stinger if any"
}}

Create 3-4 acts with 4-6 beats each. Be specific about what happens and why.
"""


async def generate_outline_llm(
    bible_path: Path,
    arc_path: Path,
    episode: int,
    provider_name: str = "openrouter",
    api_key: str = "",
    model: str = None,
) -> EpisodeOutline:
    """Generate episode outline using LLM."""
    # Load bible
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    
    # Load arc and get episode info
    arc_data = json.loads(arc_path.read_text()) if arc_path.exists() else {}
    ep_info = next(
        (ep for ep in arc_data.get("episodes", []) if ep["episode_number"] == episode),
        {"title": f"Episode {episode}", "logline": "", "beats": []},
    )
    
    # Set default model
    if model is None:
        if provider_name == "openrouter":
            model = "openai/gpt-4o"
        elif provider_name == "anthropic":
            model = "claude-3-5-sonnet-20241022"
        else:
            model = "gpt-4o"
    
    prompt = OUTLINE_PROMPT.format(
        bible=bible_content[:6000],
        arc=json.dumps(arc_data, indent=2)[:4000],
        episode=episode,
        ep_title=ep_info.get("title", f"Episode {episode}"),
        ep_logline=ep_info.get("logline", ""),
    )
    
    provider = create_provider(provider_name, {"api_key": api_key, "model": model})
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.8)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    # Flatten beats for EpisodeOutline
    all_beats = []
    for act in data.get("acts", []):
        for beat in act.get("beats", []):
            all_beats.append(f"Act {act['act_number']}, Beat {beat['beat_number']}: {beat['description']}")
    
    return EpisodeOutline(
        episode_number=data.get("episode_number", episode),
        title=data.get("title"),
        logline=data.get("logline", ""),
        beats=all_beats,
    )


def save_outline(outline: EpisodeOutline, episode_path: Path):
    """Save episode outline to markdown."""
    lines = [
        f"# Episode {outline.episode_number}: {outline.title or 'Untitled'}",
        "",
        f"**Logline:** {outline.logline}",
        "",
        "## Beats",
        "",
    ]
    
    for beat in outline.beats:
        lines.append(f"- {beat}")
    
    lines.append("")
    
    md_path = episode_path / "outline.md"
    md_path.write_text("\n".join(lines))
    
    return md_path


def outline_episode_cli(
    episode: int = 1,
    season: int = 1,
    provider: str = "openrouter",
    model: str = None,
):
    """CLI entry point for episode outline."""
    from seriesforge.core.config import get_api_key
    
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    bible_path = project_path / "bible" / "show_bible.md"
    if not bible_path.exists():
        typer.echo("Error: Show bible not found. Run 'seriesforge bible generate' first.")
        raise typer.Exit(code=1)
    
    arc_path = project_path / f"season_{season}" / "arc.json"
    if not arc_path.exists():
        typer.echo(f"Error: Season {season} arc not found. Run 'seriesforge arc generate' first.")
        raise typer.Exit(code=1)
    
    api_key = get_api_key(config, provider)
    if not api_key:
        typer.echo(f"Error: {provider.upper()}_API_KEY not set.")
        raise typer.Exit(code=1)
    
    episode_path = (
        project_path
        / f"season_{season}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    episode_path.mkdir(parents=True, exist_ok=True)
    
    typer.echo(f"Generating outline for episode {episode}...")
    
    try:
        outline = asyncio.run(
            generate_outline_llm(bible_path, arc_path, episode, provider, api_key, model)
        )
    except Exception as e:
        typer.echo(f"Error generating outline: {e}")
        raise typer.Exit(code=1)
    
    md_path = save_outline(outline, episode_path)
    
    typer.echo(f"✓ Episode {episode} outline generated")
    typer.echo(f"  {md_path}")
    typer.echo(f"  Beats: {len(outline.beats)}")
