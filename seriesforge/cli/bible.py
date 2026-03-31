"""Bible generation with LLM."""

import asyncio
import json
import os
from pathlib import Path
from typing import List

import typer
import yaml

from seriesforge.core.models import ShowBible, Character, Location
from seriesforge.providers.llm import ChatMessage, create_provider


BIBLE_PROMPT = """
You are an expert TV show developer. Create a comprehensive show bible based on the concept provided.

Input:
- Concept: {concept}
- Genre: {genre}
- Tone: {tone}

Output a valid JSON object with this exact structure:
{{
  "title": "show title",
  "concept": "refined concept statement",
  "genre": "genre",
  "tone": "tone description",
  "characters": [
    {{
      "name": "character name",
      "description": "detailed character description including personality, appearance, backstory",
      "voice": "voice characteristics",
      "wardrobe": "typical clothing/style",
      "relationships": {{}}
    }}
  ],
  "locations": [
    {{
      "name": "location name",
      "description": "visual description of the location",
      "visual_style": "cinematic visual style notes"
    }}
  ],
  "themes": ["theme1", "theme2"],
  "lore": "any world-building lore",
  "running_jokes": ["joke1", "joke2"]
}}

Create 3-5 main characters and 2-4 key locations. Be specific and visual.
"""


async def generate_bible_llm(
    concept: str,
    genre: str,
    tone: str,
    provider_name: str = "openai",
    api_key: str = "",
) -> ShowBible:
    """Generate show bible using LLM."""
    prompt = BIBLE_PROMPT.format(concept=concept, genre=genre, tone=tone)
    
    provider = create_provider(provider_name, {"api_key": api_key})
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only, no markdown formatting."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.8)
    
    # Parse JSON response
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    characters = [
        Character(
            name=c["name"],
            description=c["description"],
            voice=c.get("voice"),
            wardrobe=c.get("wardrobe"),
            relationships=c.get("relationships", {}),
        )
        for c in data.get("characters", [])
    ]
    
    locations = [
        Location(
            name=l["name"],
            description=l["description"],
            visual_style=l.get("visual_style"),
        )
        for l in data.get("locations", [])
    ]
    
    return ShowBible(
        title=data.get("title", "Untitled"),
        concept=data.get("concept", concept),
        genre=data.get("genre", genre),
        tone=data.get("tone", tone),
        characters=characters,
        locations=locations,
        themes=data.get("themes", []),
        lore=data.get("lore"),
        running_jokes=data.get("running_jokes", []),
    )


def format_bible_markdown(bible: ShowBible) -> str:
    """Format show bible as markdown."""
    lines = [
        f"# {bible.title}",
        "",
        f"**Concept:** {bible.concept}",
        "",
        f"**Genre:** {bible.genre}",
        "",
        f"**Tone:** {bible.tone}",
        "",
        "## Characters",
        "",
    ]
    
    for char in bible.characters:
        lines.append(f"### {char.name}")
        lines.append(f"{char.description}")
        if char.voice:
            lines.append(f"\n**Voice:** {char.voice}")
        if char.wardrobe:
            lines.append(f"**Wardrobe:** {char.wardrobe}")
        if char.relationships:
            lines.append("\n**Relationships:**")
            for rel, desc in char.relationships.items():
                lines.append(f"- {rel}: {desc}")
        lines.append("")
    
    lines.extend(["## Locations", ""])
    
    for loc in bible.locations:
        lines.append(f"### {loc.name}")
        lines.append(f"{loc.description}")
        if loc.visual_style:
            lines.append(f"\n**Visual Style:** {loc.visual_style}")
        lines.append("")
    
    if bible.themes:
        lines.extend(["## Themes", ""])
        for theme in bible.themes:
            lines.append(f"- {theme}")
        lines.append("")
    
    if bible.lore:
        lines.extend(["## Lore", "", bible.lore, ""])
    
    if bible.running_jokes:
        lines.extend(["## Running Jokes", ""])
        for joke in bible.running_jokes:
            lines.append(f"- {joke}")
        lines.append("")
    
    return "\n".join(lines)


def save_bible_to_yaml(bible: ShowBible, path: Path):
    """Save bible as YAML for programmatic access."""
    data = {
        "title": bible.title,
        "concept": bible.concept,
        "genre": bible.genre,
        "tone": bible.tone,
        "characters": [
            {
                "name": c.name,
                "description": c.description,
                "voice": c.voice,
                "wardrobe": c.wardrobe,
                "relationships": c.relationships,
            }
            for c in bible.characters
        ],
        "locations": [
            {
                "name": l.name,
                "description": l.description,
                "visual_style": l.visual_style,
            }
            for l in bible.locations
        ],
        "themes": bible.themes,
        "lore": bible.lore,
        "running_jokes": bible.running_jokes,
    }
    
    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def generate_bible_cli(
    concept: str,
    genre: str = "drama",
    tone: str = "cinematic",
    provider: str = "openai",
):
    """CLI entry point for bible generation."""
    from seriesforge.core.config import load_config
    
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project. Run 'seriesforge project init' first.")
        raise typer.Exit(code=1)
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and provider == "openai":
        typer.echo("Warning: OPENAI_API_KEY not set. Generating placeholder bible.")
        bible = ShowBible(
            title=" ".join(concept.split()[:3]),
            concept=concept,
            genre=genre,
            tone=tone,
            characters=[],
            locations=[],
            themes=[],
        )
        bible_path = project_path / "bible" / "show_bible.md"
        bible_path.write_text(format_bible_markdown(bible))
        typer.echo(f"✓ Placeholder bible generated: {bible_path}")
        typer.echo("Set OPENAI_API_KEY environment variable for full LLM generation")
        return
    
    try:
        bible = asyncio.run(generate_bible_llm(concept, genre, tone, provider, api_key))
    except Exception as e:
        typer.echo(f"Error generating bible with LLM: {e}")
        raise typer.Exit(code=1)
    
    bible_md_path = project_path / "bible" / "show_bible.md"
    bible_md_path.write_text(format_bible_markdown(bible))
    
    bible_yaml_path = project_path / "bible" / "characters.yaml"
    save_bible_to_yaml(bible, bible_yaml_path)
    
    typer.echo(f"✓ Show bible generated")
    typer.echo(f"  Markdown: {bible_md_path}")
    typer.echo(f"  YAML: {bible_yaml_path}")
    typer.echo(f"\nCharacters: {len(bible.characters)}")
    typer.echo(f"Locations: {len(bible.locations)}")
