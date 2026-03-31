"""Script generation and revision."""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer

from seriesforge.providers.llm import ChatMessage, create_provider


SCRIPT_GENERATION_PROMPT = """
You are an expert TV screenwriter. Write a complete episode script in Fountain format.

CRITICAL: Use ONLY these characters: {characters}
CRITICAL: Use ONLY these locations: {locations}
CRITICAL: Tone is: {tone}

EPISODE OUTLINE:
{outline}

Write in proper Fountain screenplay format.

Output ONLY the Fountain script. No explanations.
"""


async def generate_script_llm(
    episode: int,
    season: int,
    bible_path: Path,
    outline_path: Path,
    provider_name: str = "openrouter",
    api_key: str = "",
    model: str = None,
) -> str:
    """Generate episode script from outline using LLM."""
    
    # Load bible
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    
    # Load outline
    outline_content = outline_path.read_text() if outline_path.exists() else ""
    
    # Extract characters with descriptions
    import re
    
    # Get character section - find ## Characters and grab everything until next ## at line start
    char_match = re.search(r'## Characters\n((?:.|\n)*?)(?=\n## |\Z)', bible_content)
    char_desc = ""
    if char_match:
        char_desc = char_match.group(1)[:2000]  # First 2000 chars of character section
    else:
        # Fallback: just use the whole bible
        char_desc = bible_content[:1000]
    
    # Extract location names
    loc_section = re.search(r'## Locations\s+(.+?)(?:## |\Z)', bible_content, re.DOTALL)
    locations = ""
    if loc_section:
        loc_matches = re.findall(r'### (.+?)\n', loc_section.group(1))
        locations = ", ".join(loc_matches[:5])
    
    # Extract tone
    tone_match = re.search(r'\*\*Tone\*\*: (.+?)\n', bible_content)
    tone = tone_match.group(1) if tone_match else "comedy"
    
    # Set default model
    if model is None:
        if provider_name == "openrouter":
            model = "anthropic/claude-3.5-sonnet"
        elif provider_name == "anthropic":
            model = "claude-3-5-sonnet-20241022"
        else:
            model = "gpt-4o"
    
    prompt = f"""Write a TV episode script in Fountain format.

CHARACTERS (use ONLY these):
{char_desc}

LOCATIONS (use ONLY these): {locations}

TONE: {tone}

OUTLINE:
{outline_content[:4000]}

Output ONLY the Fountain script."""
    
    provider = create_provider(provider_name, {"api_key": api_key, "model": model})
    
    messages = [
        ChatMessage(role="system", content=f"You are a TV screenwriter. Use ONLY the characters provided: Robo, Mark, Jenna. Output Fountain format only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.7, max_tokens=8000)
    
    return response.content


REVISE_PROMPT = """
You are an expert script doctor. Revise this script based on the feedback notes.

Original Script:
{script}

Feedback Notes:
{notes}

Revise the script addressing all the feedback. Maintain the Fountain format.
Keep the same scene structure unless the feedback specifically asks to change it.

Output ONLY the revised Fountain script, no explanations.
"""


async def revise_script_llm(
    script_path: Path,
    notes_path: Path,
    provider_name: str = "openai",
    api_key: str = "",
) -> str:
    """Revise script using LLM."""
    script_content = script_path.read_text()
    notes_content = notes_path.read_text()
    
    prompt = REVISE_PROMPT.format(script=script_content[:12000], notes=notes_content[:4000])
    
    provider = create_provider(provider_name, {"api_key": api_key})
    
    messages = [
        ChatMessage(role="system", content="You are a professional script doctor. Output Fountain format only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.7, max_tokens=16000)
    
    return response.content


def revise_script_cli(
    episode: int = 1,
    season: int = 1,
    notes: str = "",
    provider: str = "openai",
):
    """CLI entry point for script revision."""
    project_path = Path.cwd()
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    
    script_path = episode_path / f"script_ep{episode:02d}.fountain"
    if not script_path.exists():
        typer.echo(f"Error: Script not found. Run 'seriesforge script write' first.")
        raise typer.Exit(code=1)
    
    # Handle notes
    notes_path = Path(notes)
    if not notes_path.exists():
        typer.echo(f"Error: Notes file not found: {notes}")
        raise typer.Exit(code=1)
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        typer.echo("Error: OPENAI_API_KEY not set.")
        raise typer.Exit(code=1)
    
    typer.echo(f"Revising script for episode {episode}...")
    typer.echo(f"  Notes: {notes_path}")
    
    try:
        revised_script = asyncio.run(
            revise_script_llm(script_path, notes_path, provider, api_key)
        )
    except Exception as e:
        typer.echo(f"Error revising script: {e}")
        raise typer.Exit(code=1)
    
    # Backup original
    backup_path = script_path.parent / f"script_ep{episode:02d}_v1.fountain"
    import shutil
    shutil.copy(script_path, backup_path)
    
    # Save revised
    script_path.write_text(revised_script)
    
    typer.echo(f"✓ Script revised")
    typer.echo(f"  Original backed up: {backup_path}")
    typer.echo(f"  Revised: {script_path}")
