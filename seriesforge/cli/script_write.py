"""Script writing with evaluation retry loop."""

import asyncio
import typer
from pathlib import Path
from typing import Optional

from seriesforge.core.config import load_config
from seriesforge.core.evaluation import evaluate_episode, save_evaluation_report
from seriesforge.core.adversarial_edit import generate_cut_brief, apply_cuts
from seriesforge.core.state import PipelineState
from seriesforge.core.manifests import load_episode_manifest


async def write_episode_with_retry(
    episode: int,
    season: int,
    max_attempts: int = 3,
    score_threshold: float = 6.0,
    apply_adversarial: bool = True,
    provider: str = "anthropic",
):
    """Write episode script with evaluation retry loop."""
    
    project_path = Path.cwd()
    config = load_config(project_path)
    state_path = project_path / "state.json"
    state = PipelineState(state_path)
    
    bible_path = project_path / "bible.md"
    outline_path = project_path / f"s{season}e{episode}_outline.md"
    script_path = project_path / f"s{season}e{episode}_script.md"
    eval_path = project_path / "evals" / f"s{season}e{episode}_eval.json"
    
    # Import here to avoid circular imports
    from seriesforge.cli.script import generate_script_llm
    
    for attempt in range(1, max_attempts + 1):
        typer.echo(f"\n{'='*60}")
        typer.echo(f"Draft Attempt {attempt}/{max_attempts}")
        typer.echo(f"{'='*60}")
        
        # Generate draft
        typer.echo("Generating draft...")
        script_text = await generate_script_llm(
            episode=episode,
            season=season,
            bible_path=bible_path,
            outline_path=outline_path,
            provider_name=provider,
            api_key=config.get("anthropic_api_key", ""),
        )
        
        # Save draft
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script_text)
        typer.echo(f"✓ Draft saved to {script_path}")
        
        # Apply adversarial editing if enabled
        if apply_adversarial and attempt < max_attempts:
            typer.echo("\nApplying adversarial editing...")
            cut_brief = await generate_cut_brief(script_text, target_reduction=10.0, provider_name=provider)
            typer.echo(f"Found {len(cut_brief.cuts)} cuts to make")
            script_text = await apply_cuts(script_text, cut_brief, provider_name=provider)
            script_path.write_text(script_text)
        
        # Evaluate
        typer.echo("\nEvaluating draft...")
        score = await evaluate_episode(
            script_path,
            bible_path,
            outline_path,
            provider_name=provider,
            api_key=config.get("anthropic_api_key", ""),
        )
        
        # Save evaluation report
        report = save_evaluation_report(score, eval_path)
        
        # Print scores
        typer.echo(f"\n{'='*40}")
        typer.echo(f"Scores (Attempt {attempt}):")
        typer.echo(f"  Mechanical: {score.mechanical_score:.1f}/10")
        typer.echo(f"  LLM Judge: {score.llm_score:.1f}/10")
        typer.echo(f"  Overall: {score.overall:.1f}/10")
        typer.echo(f"  Threshold: {score_threshold}/10")
        typer.echo(f"{'='*40}")
        
        # Update state
        state.set_stage_status(f"s{season}e{episode}_script", "completed" if score.overall >= score_threshold else "needs_revision", score.overall)
        
        # Check if passed
        if score.overall >= score_threshold:
            typer.echo(f"\n✓ Episode passed evaluation (score {score.overall:.1f} >= {score_threshold})")
            return script_text, score
        
        typer.echo(f"\n✗ Episode did not pass (score {score.overall:.1f} < {score_threshold})")
        typer.echo("Issues:")
        for issue in score.issues[:5]:
            typer.echo(f"  - {issue}")
        
        if attempt < max_attempts:
            typer.echo(f"\n→ Retrying with feedback...")
    
    # Max attempts reached
    typer.echo(f"\n⚠ Max attempts ({max_attempts}) reached")
    typer.echo(f"Final score: {score.overall:.1f}/10")
    return script_text, score


def write_script_cli(
    episode: int = 1,
    season: int = 1,
    max_attempts: int = 3,
    score_threshold: float = 6.0,
    no_adversarial: bool = False,
    provider: str = "anthropic",
):
    """CLI for writing script with retry loop."""
    
    asyncio.run(write_episode_with_retry(
        episode=episode,
        season=season,
        max_attempts=max_attempts,
        score_threshold=score_threshold,
        apply_adversarial=not no_adversarial,
        provider=provider,
    ))
