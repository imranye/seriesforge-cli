"""SeriesForge CLI main entry point."""

import typer
from typing import Optional

app = typer.Typer(
    name="seriesforge",
    help="An agentic CLI for AI-native film and production studios",
    add_completion=True,
)


@app.command()
def version():
    """Show SeriesForge version."""
    from seriesforge import __version__
    typer.echo(f"seriesforge version {__version__}")


# Project commands
project_app = typer.Typer(name="project", help="Project management commands")


@project_app.command("init")
def project_init(name: str = typer.Argument(..., help="Project name")):
    """Initialize a new SeriesForge project."""
    from seriesforge.cli.project import init_project
    init_project(name)


@project_app.command()
def project_status():
    """Show project status."""
    typer.echo("TODO: Implement project status")


@project_app.command()
def project_validate():
    """Validate project configuration."""
    typer.echo("TODO: Implement project validation")


app.add_typer(project_app, name="project")


# Bible commands
bible_app = typer.Typer(name="bible", help="Show bible commands")


@bible_app.command("generate")
def bible_generate(
    concept: str = typer.Option(..., "--concept", help="Show concept description"),
    genre: str = typer.Option("drama", "--genre", help="Genre"),
    tone: str = typer.Option("cinematic", "--tone", help="Tone"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Generate a show bible from a concept."""
    from seriesforge.cli.bible import generate_bible_cli
    generate_bible_cli(concept=concept, genre=genre, tone=tone, provider=provider)


app.add_typer(bible_app, name="bible")


# Arc commands
arc_app = typer.Typer(name="arc", help="Season arc commands")


@arc_app.command("generate")
def arc_generate(
    season: int = typer.Option(1, "--season", help="Season number"),
    episodes: int = typer.Option(8, "--episodes", help="Number of episodes"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Generate season arc."""
    from seriesforge.cli.arc import generate_arc_cli
    generate_arc_cli(season=season, episodes=episodes, provider=provider)


app.add_typer(arc_app, name="arc")


# Episode commands
episode_app = typer.Typer(name="episode", help="Episode commands")


@episode_app.command("outline")
def episode_outline(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Generate episode outline."""
    from seriesforge.cli.episode import outline_episode_cli
    outline_episode_cli(episode=episode, season=season, provider=provider)


app.add_typer(episode_app, name="episode")


# Script commands
script_app = typer.Typer(name="script", help="Script writing commands")


@script_app.command("write")
def script_write(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Write episode script."""
    from seriesforge.cli.script import write_script_cli
    write_script_cli(episode=episode, season=season, provider=provider)


@script_app.command("revise")
def script_revise(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    notes: str = typer.Option(..., "--notes", help="Path to feedback notes file"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Revise script based on notes."""
    from seriesforge.cli.script import revise_script_cli
    revise_script_cli(episode=episode, season=season, notes=notes, provider=provider)


app.add_typer(script_app, name="script")


# Shots commands
shots_app = typer.Typer(name="shots", help="Shot planning commands")


@shots_app.command("plan")
def shots_plan(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    provider: str = typer.Option("openai", "--provider", help="LLM provider"),
):
    """Generate shot list from script."""
    from seriesforge.cli.shots import plan_shots_cli
    plan_shots_cli(episode=episode, season=season, provider=provider)


app.add_typer(shots_app, name="shots")


# Voice commands
voice_app = typer.Typer(name="voice", help="Voice generation commands")


@voice_app.command("generate")
def voice_generate(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    provider: str = typer.Option("openai", "--provider", help="TTS provider"),
):
    """Generate dialogue audio."""
    from seriesforge.cli.voice import generate_voice_cli
    generate_voice_cli(episode=episode, season=season, provider=provider)


app.add_typer(voice_app, name="voice")


# Video commands
video_app = typer.Typer(name="video", help="Video generation commands")


@video_app.command("generate")
def video_generate(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    provider: str = typer.Option("kling", "--provider", help="Video provider"),
    failed_only: bool = typer.Option(False, "--failed-only", help="Only render failed shots"),
):
    """Generate video clips."""
    from seriesforge.cli.video import generate_video_cli
    generate_video_cli(episode=episode, season=season, provider=provider, failed_only=failed_only)


@video_app.command("render-scene")
def video_render_scene(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    scene: int = typer.Option(1, "--scene", help="Scene number"),
    season: int = typer.Option(1, "--season", help="Season number"),
):
    """Render specific scene."""
    typer.echo(f"TODO: Render scene {scene} from episode {episode}")


app.add_typer(video_app, name="video")


# Edit commands
edit_app = typer.Typer(name="edit", help="Edit assembly commands")


@edit_app.command("assemble")
def edit_assemble(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    output_name: str = typer.Option("rough_cut", "--output", help="Output filename"),
):
    """Assemble episode edit."""
    from seriesforge.cli.edit import assemble_edit_cli
    assemble_edit_cli(episode=episode, season=season, output_name=output_name)


app.add_typer(edit_app, name="edit")


# QC commands
qc_app = typer.Typer(name="qc", help="Quality control commands")


@qc_app.command("run")
def qc_run(episode: int = typer.Option(1, "--episode", help="Episode number")):
    """Run quality checks."""
    from seriesforge.cli.qc import run_qc
    run_qc(episode=episode)


app.add_typer(qc_app, name="qc")


# Subtitle commands
subtitle_app = typer.Typer(name="subtitles", help="Subtitle commands")


@subtitle_app.command("generate")
def subtitles_generate(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    input_video: str = typer.Option(None, "--input", help="Input video path"),
):
    """Generate subtitles."""
    from seriesforge.cli.subtitles import generate_subtitles_cli
    generate_subtitles_cli(episode=episode, season=season, input_video=input_video)


app.add_typer(subtitle_app, name="subtitles")


# Export commands
export_app = typer.Typer(name="export", help="Export commands")


@export_app.command("package")
def export_package(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    include_source: bool = typer.Option(False, "--source", help="Include source files"),
):
    """Export episode package."""
    from seriesforge.cli.export import export_package_cli
    export_package_cli(episode=episode, season=season, include_source=include_source)


app.add_typer(export_app, name="export")


# Pipeline commands
pipeline_app = typer.Typer(name="pipeline", help="Pipeline orchestration commands")


@pipeline_app.command("run")
def pipeline_run(
    episode: int = typer.Option(1, "--episode", help="Episode number"),
    season: int = typer.Option(1, "--season", help="Season number"),
    auto: bool = typer.Option(False, "--auto", help="Auto-approve all stages"),
    from_stage: Optional[str] = typer.Option(None, "--from", help="Start from stage"),
    to_stage: Optional[str] = typer.Option(None, "--to", help="End at stage"),
):
    """Run full production pipeline."""
    from seriesforge.cli.pipeline import run_pipeline_cli
    run_pipeline_cli(
        episode=episode,
        season=season,
        auto=auto,
        from_stage=from_stage,
        to_stage=to_stage,
    )


@pipeline_app.command()
def pipeline_resume(run_id: str = typer.Argument(..., help="Run ID to resume")):
    """Resume a paused pipeline run."""
    from pathlib import Path
    import json
    
    project_path = Path.cwd()
    runs_path = project_path / "runs" / run_id
    
    if not runs_path.exists():
        typer.echo(f"Error: Run {run_id} not found")
        raise typer.Exit(code=1)
    
    manifest_path = runs_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Find first incomplete stage
    completed_stages = {s["name"] for s in manifest.get("stages", []) if s["status"] == "completed"}
    all_stages = ["bible", "arc", "outline", "script", "shots", "voice", "video", "edit", "qc", "export"]
    
    next_stage = None
    for stage in all_stages:
        if stage not in completed_stages:
            next_stage = stage
            break
    
    if not next_stage:
        typer.echo("Pipeline already complete")
        return
    
    episode = manifest.get("episode", 1)
    season = manifest.get("season", 1)
    
    typer.echo(f"Resuming run {run_id}")
    typer.echo(f"Next stage: {next_stage}")
    typer.echo(f"Episode: S{season}E{episode}")
    
    # Re-run pipeline from next stage
    from seriesforge.cli.pipeline import run_pipeline_cli
    run_pipeline_cli(
        episode=episode,
        season=season,
        auto=False,
        from_stage=next_stage,
    )


app.add_typer(pipeline_app, name="pipeline")


if __name__ == "__main__":
    app()
