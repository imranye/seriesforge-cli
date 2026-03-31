"""Revision loop with Opus dual-persona review."""

import asyncio
import typer
from pathlib import Path
from typing import Optional, List

from seriesforge.core.config import load_config
from seriesforge.core.network_review import network_review
from seriesforge.core.state import PipelineState
from seriesforge.core.manifests import load_episode_manifest
from seriesforge.providers.llm import ChatMessage, create_provider


async def revision_loop(
    episode: int,
    season: int,
    max_rounds: int = 6,
    provider: str = "anthropic",
):
    """Run revision loop with Opus dual-persona review."""
    
    project_path = Path.cwd()
    config = load_config(project_path)
    state_path = project_path / "state.json"
    state = PipelineState(state_path)
    
    bible_path = project_path / "bible.md"
    script_path = project_path / f"s{season}e{episode}_script.md"
    revision_dir = project_path / "revisions" / f"s{season}e{episode}"
    revision_dir.mkdir(parents=True, exist_ok=True)
    
    # Load current script
    if not script_path.exists():
        typer.echo(f"Error: Script not found at {script_path}")
        typer.echo("Run 'seriesforge script write' first")
        return
    
    script_text = script_path.read_text()
    
    for round_num in range(1, max_rounds + 1):
        typer.echo(f"\n{'='*60}")
        typer.echo(f"Revision Round {round_num}/{max_rounds}")
        typer.echo(f"{'='*60}")
        
        # Get network review
        typer.echo("Getting dual-persona review (showrunner + network exec)...")
        review = await network_review(
            script_text,
            bible_path,
            provider_name=provider,
            api_key=config.get("anthropic_api_key", ""),
        )
        
        # Save review
        review_path = revision_dir / f"review_round_{round_num}.json"
        import json
        from dataclasses import asdict
        review_data = {
            "showrunner_review": review.showrunner_review,
            "network_exec_review": review.network_exec_review,
            "major_issues": review.major_issues,
            "minor_issues": review.minor_issues,
            "actionable_items": review.actionable_items,
            "should_continue": review.should_continue,
            "stopping_reason": review.stopping_reason,
        }
        review_path.write_text(json.dumps(review_data, indent=2))
        
        # Print review summary
        typer.echo(f"\n{'='*40}")
        typer.echo("Review Summary:")
        typer.echo(f"  Showrunner score: {review.showrunner_review['score']:.1f}/10")
        typer.echo(f"  Network exec score: {review.network_exec_review['score']:.1f}/10")
        typer.echo(f"  Major issues: {len(review.major_issues)}")
        typer.echo(f"  Minor issues: {len(review.minor_issues)}")
        typer.echo(f"{'='*40}")
        
        if review.major_issues:
            typer.echo("\nMajor issues:")
            for issue in review.major_issues:
                typer.echo(f"  • {issue}")
        
        # Check stopping conditions
        if not review.should_continue:
            typer.echo(f"\n✓ Revision complete!")
            typer.echo(f"Stopping reason: {review.stopping_reason}")
            break
        
        if not review.actionable_items:
            typer.echo("\n✓ No actionable items remaining")
            break
        
        # Apply revisions
        typer.echo("\nApplying revisions...")
        typer.echo("Actionable items:")
        for item in review.actionable_items[:5]:
            typer.echo(f"  • {item}")
        
        # Generate revised script
        revision_prompt = f"""You are revising a TV script based on feedback.

CURRENT SCRIPT:
{script_text[:30000]}

FEEDBACK TO ADDRESS:
Major issues:
{chr(10).join(f'- {i}' for i in review.major_issues)}

Actionable items:
{chr(10).join(f'- {i}' for i in review.actionable_items)}

Output ONLY the revised script, no explanations.
"""
        
        provider = create_provider(provider, {"api_key": config.get("anthropic_api_key", "")})
        messages = [
            ChatMessage(role="system", content="Output only the revised script text."),
            ChatMessage(role="user", content=revision_prompt),
        ]
        
        response = await provider.chat(messages, temperature=0.3)
        script_text = response.content
        
        # Save revised script
        revision_script_path = revision_dir / f"script_round_{round_num}.md"
        revision_script_path.write_text(script_text)
        
        # Update main script
        script_path.write_text(script_text)
        typer.echo(f"✓ Revision saved")
    
    typer.echo(f"\n{'='*60}")
    typer.echo("Revision loop complete")
    typer.echo(f"{'='*60}")


def revision_cli(
    episode: int = 1,
    season: int = 1,
    max_rounds: int = 6,
    provider: str = "anthropic",
):
    """CLI for revision loop."""
    asyncio.run(revision_loop(
        episode=episode,
        season=season,
        max_rounds=max_rounds,
        provider=provider,
    ))
