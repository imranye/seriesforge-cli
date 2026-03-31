"""Season arc generation with LLM."""

import asyncio
import json
import os
from pathlib import Path

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.core.models import EpisodeOutline
from seriesforge.providers.llm import ChatMessage, create_provider


ARC_PROMPT = """
You are an expert TV show runner. Create a season arc based on the show bible.

Show Bible:
{bible}

Season: {season}

Output a valid JSON object with this structure:
{{
  "season": {season},
  "title": "season title/theme",
  "logline": "one-sentence season summary",
  "arc_description": "2-3 paragraphs describing the overall season arc, major character developments, and key plot threads",
  "episode_count": {episode_count},
  "episodes": [
    {{
      "episode_number": 1,
      "title": "episode title",
      "logline": "one-sentence episode summary",
      "beats": ["beat 1", "beat 2", "beat 3"]
    }}
  ],
  "character_arcs": [
    {{
      "character": "character name",
      "arc": "how they change over the season"
    }}
  ]
}}

Create {episode_count} episodes. Each episode should have 5-8 beats that advance the overall arc.
"""


async def generate_arc_llm(
    bible_path: Path,
    season: int = 1,
    episode_count: int = 8,
    provider_name: str = "openrouter",
    api_key: str = "",
    model: str = None,
) -> dict:
    """Generate season arc using LLM."""
    # Load bible
    if bible_path.exists():
        with open(bible_path) as f:
            bible_content = f.read()
    else:
        raise FileNotFoundError(f"Bible not found at {bible_path}")
    
    # Set default model
    if model is None:
        if provider_name == "openrouter":
            model = "openai/gpt-4o"
        elif provider_name == "anthropic":
            model = "claude-3-5-sonnet-20241022"
        else:
            model = "gpt-4o"
    
    prompt = ARC_PROMPT.format(
        bible=bible_content[:8000],  # Limit context
        season=season,
        episode_count=episode_count,
    )
    
    provider = create_provider(provider_name, {"api_key": api_key, "model": model})
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only, no markdown formatting."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.8)
    
    # Parse JSON
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    return json.loads(content)


def save_arc(arc_data: dict, season_path: Path):
    """Save season arc to markdown and JSON."""
    # Markdown version
    md_lines = [
        f"# Season {arc_data['season']} Arc",
        "",
        f"**Theme:** {arc_data.get('title', 'Untitled')}",
        "",
        f"**Logline:** {arc_data.get('logline', '')}",
        "",
        "## Arc Description",
        "",
        arc_data.get('arc_description', ''),
        "",
        "## Episodes",
        "",
    ]
    
    for ep in arc_data.get('episodes', []):
        md_lines.extend([
            f"### Episode {ep['episode_number']}: {ep.get('title', 'Untitled')}",
            "",
            f"**Logline:** {ep.get('logline', '')}",
            "",
            "Beats:",
        ])
        for beat in ep.get('beats', []):
            md_lines.append(f"- {beat}")
        md_lines.append("")
    
    if arc_data.get('character_arcs'):
        md_lines.extend(["## Character Arcs", ""])
        for ca in arc_data['character_arcs']:
            md_lines.append(f"### {ca['character']}")
            md_lines.append(f"{ca['arc']}")
            md_lines.append("")
    
    md_path = season_path / "arc.md"
    md_path.write_text("\n".join(md_lines))
    
    # JSON version for programmatic access
    json_path = season_path / "arc.json"
    with open(json_path, 'w') as f:
        json.dump(arc_data, f, indent=2)
    
    return md_path, json_path


def generate_arc_cli(
    season: int = 1,
    episodes: int = 8,
    provider: str = "openrouter",
    model: str = None,
):
    """CLI entry point for arc generation."""
    from seriesforge.core.config import load_config, get_api_key
    
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    bible_path = project_path / "bible" / "show_bible.md"
    api_key = get_api_key(config, provider)
    season_path = project_path / f"season_{season}"
    season_path.mkdir(parents=True, exist_ok=True)
    
    if not api_key:
        typer.echo(f"Warning: {provider.upper()}_API_KEY not set.")
        raise typer.Exit(code=1)
    
    typer.echo(f"Generating season {season} arc...")
    
    try:
        arc_data = asyncio.run(
            generate_arc_llm(bible_path, season, episodes, provider, api_key, model)
        )
    except Exception as e:
        typer.echo(f"Error generating arc: {e}")
        raise typer.Exit(code=1)
    
    md_path, json_path = save_arc(arc_data, season_path)
    
    typer.echo(f"✓ Season {season} arc generated")
    typer.echo(f"  Markdown: {md_path}")
    typer.echo(f"  JSON: {json_path}")
    typer.echo(f"  Episodes: {len(arc_data.get('episodes', []))}")
