"""Edit assembly with FFmpeg."""

import json
import subprocess
from pathlib import Path
from typing import List, Dict

import typer
import yaml


def load_video_manifest(episode_path: Path) -> Dict:
    """Load video manifest."""
    manifest_path = episode_path / "video" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Video manifest not found")
    
    with open(manifest_path) as f:
        return json.load(f)


def load_audio_manifest(episode_path: Path) -> Dict:
    """Load audio manifest."""
    manifest_path = episode_path / "audio" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Audio manifest not found")
    
    with open(manifest_path) as f:
        return json.load(f)


def create_ffmpeg_concat_file(video_path: Path, shots: List[Dict]):
    """Create FFmpeg concat list file."""
    concat_lines = []
    
    for shot in sorted(shots, key=lambda s: s["shot_number"]):
        if shot.get("status") == "completed" and shot.get("path"):
            shot_path = Path(shot["path"])
            if shot_path.exists():
                # FFmpeg concat requires absolute paths
                concat_lines.append(f"file '{shot_path.absolute()}'")
    
    concat_file = video_path / "concat_list.txt"
    concat_file.write_text("\n".join(concat_lines))
    
    return concat_file


def assemble_edit_cli(
    episode: int = 1,
    season: int = 1,
    output_name: str = "rough_cut",
):
    """CLI entry point for edit assembly."""
    project_path = Path.cwd()
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    edits_path = episode_path / "edits"
    edits_path.mkdir(exist_ok=True)
    
    video_path = episode_path / "video"
    audio_path = episode_path / "audio"
    
    typer.echo(f"Assembling edit for episode {episode}...")
    
    # Load manifests
    try:
        video_manifest = load_video_manifest(episode_path)
        typer.echo(f"  Found {video_manifest.get('completed', 0)} video shots")
    except FileNotFoundError:
        typer.echo("Warning: No video manifest found. Skipping video assembly.")
        video_manifest = {"shots": []}
    
    try:
        audio_manifest = load_audio_manifest(episode_path)
        typer.echo(f"  Found {len(audio_manifest.get('files', []))} audio files")
    except FileNotFoundError:
        typer.echo("Warning: No audio manifest found. Skipping audio assembly.")
        audio_manifest = {"files": []}
    
    # Create output path
    output_file = edits_path / f"{output_name}_ep{episode:02d}.mp4"
    
    # Check if we have videos to assemble
    completed_shots = [s for s in video_manifest.get("shots", []) if s.get("status") == "completed"]
    
    if not completed_shots:
        typer.echo("No completed video shots to assemble.")
        typer.echo("Create a placeholder manifest...")
        
        # Create placeholder
        manifest = {
            "episode": episode,
            "output": str(output_file),
            "note": "No videos to assemble",
        }
        with open(edits_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        return
    
    # Method 1: Simple concat (videos only, no audio mixing)
    typer.echo("\nAssembling video clips...")
    
    concat_file = create_ffmpeg_concat_file(video_path, completed_shots)
    
    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",  # Copy codec (fast, no re-encoding)
        str(output_file),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode == 0:
            typer.echo(f"✓ Edit assembled: {output_file}")
            
            # Get duration
            import subprocess
            probe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(output_file),
            ]
            duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(duration_result.stdout.strip())
            
            typer.echo(f"  Duration: {duration:.1f}s")
        else:
            typer.echo(f"✗ FFmpeg error: {result.stderr}")
            raise typer.Exit(code=1)
    
    except FileNotFoundError:
        typer.echo("Error: FFmpeg not found. Install with:")
        typer.echo("  macOS: brew install ffmpeg")
        typer.echo("  Ubuntu: sudo apt install ffmpeg")
        raise typer.Exit(code=1)
    except subprocess.TimeoutExpired:
        typer.echo("Error: FFmpeg timed out.")
        raise typer.Exit(code=1)
    
    # Save edit manifest
    edit_manifest = {
        "episode": episode,
        "output": str(output_file),
        "duration": duration,
        "video_shots": len(completed_shots),
        "audio_files": len(audio_manifest.get("files", [])),
        "method": "concat",
    }
    
    with open(edits_path / "manifest.json", 'w') as f:
        json.dump(edit_manifest, f, indent=2)
    
    typer.echo(f"\n✓ Edit assembly complete")
    typer.echo(f"  Output: {output_file}")
    typer.echo(f"  Duration: {duration:.1f}s")
