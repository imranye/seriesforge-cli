"""Project management CLI commands."""

import typer
from pathlib import Path
from datetime import datetime
import yaml

from seriesforge.core.config import ProjectConfig, save_config


def init_project(name: str):
    """Initialize a new SeriesForge project with directory structure."""
    project_path = Path.cwd() / name
    
    if project_path.exists():
        typer.echo(f"Error: Directory {name} already exists")
        raise typer.Exit(code=1)
    
    project_path.mkdir(parents=True)
    typer.echo(f"Creating project: {name}")
    
    # Create directory structure per PRD section 15.2
    dirs = [
        "bible",
        "seasons/season_01/episodes",
        "seasons/season_01/episodes/ep_01/storyboard",
        "seasons/season_01/episodes/ep_01/audio",
        "seasons/season_01/episodes/ep_01/video",
        "seasons/season_01/episodes/ep_01/edits",
        "seasons/season_01/episodes/ep_01/exports",
        "seasons/season_01/episodes/ep_01/qc",
        "seasons/season_01/episodes/ep_01/manifests",
        "assets/shared",
        "assets/lookbooks",
        "assets/references",
        "runs",
        "cache",
    ]
    
    for dir_path in dirs:
        (project_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create default config
    config = ProjectConfig(
        name=name,
        format="episodic",
        target_runtime_minutes=5,
    )
    save_config(config, project_path)
    
    # Create .gitignore
    gitignore = """.env
__pycache__/
*.pyc
.cache/
*.tmp
"""
    (project_path / ".gitignore").write_text(gitignore)
    
    # Create README
    readme = f"""# {name}

A SeriesForge production project.

## Getting Started

```bash
cd {name}
seriesforge bible generate --concept "Your show concept here"
seriesforge pipeline run --episode 1
```

## Project Structure

- `bible/` - Show bible and world-building
- `seasons/` - Episode scripts, assets, and renders
- `assets/` - Shared assets and references
- `runs/` - Pipeline execution history
"""
    (project_path / "README.md").write_text(readme)
    
    typer.echo(f"✓ Project initialized at {project_path.absolute()}")
    typer.echo("\nNext steps:")
    typer.echo(f"  cd {name}")
    typer.echo('  seriesforge bible generate --concept "Your concept"')
