"""Script revision with feedback."""

import asyncio
import os
from pathlib import Path

import typer

from seriesforge.providers.llm import ChatMessage, create_provider


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
