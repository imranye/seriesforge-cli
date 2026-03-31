"""Subtitle generation."""

import json
import subprocess
from pathlib import Path

import typer


def generate_subtitles_cli(
    episode: int = 1,
    season: int = 1,
    input_video: str = None,
):
    """CLI entry point for subtitle generation."""
    project_path = Path.cwd()
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    edits_path = episode_path / "edits"
    
    # Find input video
    if input_video:
        video_path = Path(input_video)
    else:
        video_path = edits_path / f"rough_cut_ep{episode:02d}.mp4"
        if not video_path.exists():
            # Try to find any video
            videos = list(edits_path.glob("*.mp4"))
            if videos:
                video_path = videos[0]
            else:
                typer.echo("Error: No video found. Run 'seriesforge edit assemble' first.")
                raise typer.Exit(code=1)
    
    if not video_path.exists():
        typer.echo(f"Error: Video not found: {video_path}")
        raise typer.Exit(code=1)
    
    output_srt = edits_path / f"subs_ep{episode:02d}.srt"
    
    typer.echo(f"Generating subtitles for episode {episode}...")
    typer.echo(f"  Input: {video_path}")
    
    # Method 1: Use ffmpeg with built-in whisper (if available)
    # Method 2: Use separate whisper command
    # Method 3: Generate from script dialogue (fallback)
    
    # Try whisper first
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ae", "whisper",
            "-acodec", "srt",
            str(output_srt),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        
        if result.returncode == 0 and output_srt.exists():
            typer.echo(f"✓ Subtitles generated: {output_srt}")
            _count_subtitles(output_srt)
            return
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: generate from script
    typer.echo("FFmpeg whisper not available. Generating from script...")
    _generate_subtitles_from_script(episode_path, output_srt)


def _generate_subtitles_from_script(episode_path: Path, output_srt: Path):
    """Generate subtitles from script dialogue (fallback)."""
    script_path = episode_path / f"script_ep{episode_path.parent.name.split('_')[1]:02d}.fountain"
    
    if not script_path.exists():
        typer.echo("Error: Script not found for subtitle generation.")
        return
    
    # Extract dialogue and estimate timestamps
    lines = []
    current_character = None
    timestamp = 0  # in centiseconds (SRT format)
    
    for line in script_path.read_text().split('\n'):
        line = line.strip()
        
        if not line:
            current_character = None
            continue
        
        if line.isupper() and len(line) < 50 and " " in line and not line.startswith(("INT.", "EXT.")):
            current_character = line
        elif line.startswith("(") and line.endswith(")"):
            continue
        elif current_character:
            # Dialogue line
            duration = len(line) * 50  # Rough estimate: 50ms per character
            end_timestamp = timestamp + duration
            
            lines.append({
                "start": timestamp,
                "end": end_timestamp,
                "text": line,
            })
            
            timestamp = end_timestamp + 100  # 1 second gap
            current_character = None
    
    # Write SRT
    srt_lines = []
    for i, line in enumerate(lines, 1):
        start_ms = line["start"]
        end_ms = line["end"]
        
        # Convert to SRT timestamp format
        start_str = _cs_to_srt_time(start_ms)
        end_str = _cs_to_srt_time(end_ms)
        
        srt_lines.extend([
            str(i),
            f"{start_str} --> {end_str}",
            line["text"],
            "",
        ])
    
    output_srt.write_text("\n".join(srt_lines))
    
    typer.echo(f"✓ Subtitles generated from script: {output_srt}")
    _count_subtitles(output_srt)


def _cs_to_srt_time(centiseconds: int) -> str:
    """Convert centiseconds to SRT timestamp format."""
    hours = centiseconds // 360000
    minutes = (centiseconds % 360000) // 6000
    seconds = (centiseconds % 6000) // 100
    cents = centiseconds % 100
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{cents:02d}"


def _count_subtitles(srt_path: Path):
    """Count and display subtitle stats."""
    content = srt_path.read_text()
    count = content.strip().count("\n\n")
    typer.echo(f"  Lines: {count}")
    typer.echo(f"  Output: {srt_path}")
