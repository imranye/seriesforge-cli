"""Voice generation from script."""

import asyncio
import json
import os
from pathlib import Path

import typer
import yaml

from seriesforge.core.config import load_config
from seriesforge.core.manifests import create_asset_entry
from seriesforge.providers.tts import create_tts_provider


def extract_dialogue_from_script(script_path: Path) -> list:
    """Extract dialogue lines from Fountain script."""
    lines = []
    current_character = None
    
    for line in script_path.read_text().split('\n'):
        line = line.strip()
        
        if not line:
            current_character = None
            continue
        
        # Character name (centered, caps in Fountain)
        if line.isupper() and len(line) < 50 and " " in line and not line.startswith(("INT.", "EXT.")):
            current_character = line
        # Parenthetical
        elif line.startswith("(") and line.endswith(")"):
            continue
        # Dialogue
        elif current_character and not line.endswith(":"):
            lines.append({
                "character": current_character,
                "text": line,
            })
    
    return lines


async def generate_voice_for_line(
    text: str,
    character: str,
    tts_provider,
    voice_id: str,
) -> dict:
    """Generate voice for a single dialogue line."""
    result = await tts_provider.synthesize(text, voice_id)
    
    return {
        "character": character,
        "text": text,
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
    }


def map_characters_to_voices(bible_path: Path) -> dict:
    """Map characters to voice IDs based on bible."""
    # Load character data from bible
    characters_yaml = bible_path.parent / "characters.yaml"
    if characters_yaml.exists():
        with open(characters_yaml) as f:
            bible_data = yaml.safe_load(f)
            characters = bible_data.get("characters", [])
            
            # Map based on voice hints in bible
            mapping = {}
            for char in characters:
                name = char["name"]
                voice_hint = char.get("voice", "")
                
                # Simple heuristic: male/female voices
                if "male" in voice_hint.lower():
                    mapping[name] = "male_voice_1"
                elif "female" in voice_hint.lower():
                    mapping[name] = "female_voice_1"
                else:
                    mapping[name] = "default_voice"
            
            return mapping
    
    # Default mapping
    return {}


def generate_voice_cli(
    episode: int = 1,
    season: int = 1,
    provider: str = "openai",
):
    """CLI entry point for voice generation."""
    project_path = Path.cwd()
    
    try:
        config = load_config(project_path)
    except FileNotFoundError:
        typer.echo("Error: Not in a SeriesForge project.")
        raise typer.Exit(code=1)
    
    script_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
        / f"script_ep{episode:02d}.fountain"
    )
    if not script_path.exists():
        typer.echo(f"Error: Episode {episode} script not found.")
        raise typer.Exit(code=1)
    
    bible_path = project_path / "bible" / "show_bible.md"
    
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    
    if not api_key:
        typer.echo("Error: OPENAI_API_KEY or ELEVENLABS_API_KEY not set.")
        raise typer.Exit(code=1)
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    audio_path = episode_path / "audio"
    audio_path.mkdir(exist_ok=True)
    
    typer.echo(f"Generating voice for episode {episode}...")
    
    # Extract dialogue
    dialogue = extract_dialogue_from_script(script_path)
    typer.echo(f"Found {len(dialogue)} dialogue lines")
    
    if not dialogue:
        typer.echo("No dialogue found in script.")
        return
    
    # Create TTS provider
    tts = create_tts_provider(provider, {"api_key": api_key})
    
    # Map characters to voices
    char_to_voice = map_characters_to_voices(bible_path)
    
    # Default voices for OpenAI
    default_voices = ["alloy", "echo", "fable", "onyx", "nova"]
    
    # Generate audio for each line
    tasks = []
    for i, line in enumerate(dialogue):
        character = line["character"]
        text = line["text"]
        
        # Assign voice (round-robin for now)
        if character in char_to_voice:
            voice_id = char_to_voice[character]
        else:
            voice_id = default_voices[i % len(default_voices)]
        
        tasks.append(generate_voice_for_line(text, character, tts, voice_id))
    
    typer.echo(f"Synthesizing {len(tasks)} lines...")
    
    results = asyncio.run(asyncio.gather(*tasks, return_exceptions=True))
    
    # Save results
    audio_files = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            typer.echo(f"Error generating line {i+1}: {result}")
            continue
        
        filename = f"line_{i+1:03d}_{result['character'].replace(' ', '_')[:20]}.mp3"
        dest_path = audio_path / filename
        
        if result.get("audio_path") and Path(result["audio_path"]).exists():
            import shutil
            shutil.copy(result["audio_path"], dest_path)
            audio_files.append({
                "filename": filename,
                "character": result["character"],
                "text": result["text"][:50],
                "duration": result["duration"],
            })
    
    # Save manifest
    manifest = {
        "episode": episode,
        "provider": provider,
        "files": audio_files,
        "total_duration": sum(f["duration"] for f in audio_files),
    }
    
    manifest_path = audio_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    typer.echo(f"✓ Voice generation complete")
    typer.echo(f"  Files: {len(audio_files)}")
    typer.echo(f"  Total duration: {manifest['total_duration']:.1f}s")
    typer.echo(f"  Output: {audio_path}")
