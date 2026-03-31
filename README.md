# SeriesForge CLI

An agentic CLI for AI-native film and production studios.

> From prompt to pilot, entirely from the terminal.

## Installation

```bash
pip install seriesforge-cli
```

Or from source:

```bash
git clone https://github.com/yourorg/seriesforge-cli
cd seriesforge-cli
pip install -e .
```

### System Dependencies

- **FFmpeg** (required for video assembly)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
  - Windows: Download from https://ffmpeg.org/download.html

## Quick Start

```bash
# Initialize a new project
seriesforge project init my-show
cd my-show

# Set your API key
export OPENAI_API_KEY=sk-...

# Generate a show bible
seriesforge bible generate --concept "A deadpan workplace comedy set inside an AI film studio"

# Generate season arc
seriesforge arc generate --season 1

# Generate episode outline
seriesforge episode outline --episode 1

# Write the script
seriesforge script write --episode 1

# Plan shots
seriesforge shots plan --episode 1

# Or run the full pipeline up to shots
seriesforge pipeline run --episode 1 --to shots
```

## Full Pipeline

```bash
# Complete pipeline (requires multiple API keys)
seriesforge pipeline run --episode 1 --auto

# Pipeline with manual approval at each stage
seriesforge pipeline run --episode 1

# Resume from a specific stage
seriesforge pipeline run --episode 1 --from video

# Run specific stages only
seriesforge pipeline run --episode 1 --from script --to shots
```

## Commands

### Project Management

```bash
seriesforge project init <name>    # Create new project
seriesforge project status          # Show project status
seriesforge project validate        # Validate configuration
```

### Writing Pipeline

```bash
seriesforge bible generate --concept "..."    # Generate show bible
seriesforge arc generate --season 1           # Generate season arc
seriesforge episode outline --episode 1       # Generate outline
seriesforge script write --episode 1          # Write script
seriesforge script revise --episode 1 --notes file.md  # Revise with notes
seriesforge shots plan --episode 1            # Plan shots
```

### Media Generation

```bash
seriesforge voice generate --episode 1        # Generate dialogue audio
seriesforge video generate --episode 1        # Render video shots
seriesforge video generate --episode 1 --failed-only  # Retry failed shots
```

### Assembly & Export

```bash
seriesforge edit assemble --episode 1         # Assemble rough cut
seriesforge qc run --episode 1                # Run quality checks
seriesforge export package --episode 1        # Export delivery package
```

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY=sk-...          # For LLM generation
export ELEVENLABS_API_KEY=...         # For TTS (optional)
export KLING_API_KEY=...              # For video generation (optional)
export RUNWAY_API_KEY=...             # Alternative video provider
```

### Project Config

Edit `seriesforge.yaml` in your project directory:

```yaml
project:
  name: my-show
  format: episodic
  genre: comedy
  target_runtime_minutes: 5

workflow:
  approval_mode: manual  # manual, semi-auto, auto
  auto_retry_failed_jobs: true
  max_parallel_renders: 4

style:
  tone: deadpan, cinematic
  pacing: fast
  aspect_ratio: "16:9"

providers:
  llm:
    primary: openai
  video:
    primary: kling
  tts:
    primary: elevenlabs
```

## Project Structure

```
my-show/
  seriesforge.yaml      # Project configuration
  bible/
    show_bible.md       # Show bible (markdown)
    characters.yaml     # Character data
  seasons/
    season_01/
      arc.md            # Season arc
      arc.json          # Season arc (structured)
      episodes/
        ep_01/
          outline.md    # Episode outline
          script_ep01.fountain  # Script
          shots.yaml    # Shot list
          storyboard/   # Visual references
          audio/        # Generated dialogue
          video/        # Rendered shots
          edits/        # Assembled edits
          exports/      # Final packages
          qc/           # Quality check reports
          manifests/    # Asset tracking
  assets/
    shared/
    lookbooks/
    references/
  runs/                 # Pipeline run history
  cache/
```

## Pipeline Stages

1. **bible** - Generate show bible from concept
2. **arc** - Generate season arc and episode summaries
3. **outline** - Generate detailed episode outline with beats
4. **script** - Write full screenplay in Fountain format
5. **shots** - Break script into shots with video prompts
6. **voice** - Generate dialogue audio (TTS)
7. **video** - Render video clips from prompts
8. **edit** - Assemble clips into rough cut
9. **qc** - Run quality and continuity checks
10. **export** - Package final delivery bundle

## Provider Support

### LLM Providers
- OpenAI (GPT-4o) ✓
- Anthropic (Claude 3.5) ✓

### Video Providers
- Kling AI (placeholder)
- Runway ML (placeholder)
- Pika Labs (not implemented)

### TTS Providers
- ElevenLabs ✓
- OpenAI TTS ✓

## License

MIT

## Contributing

This is a V1 MVP. Areas for improvement:

- Actual video provider integrations (Kling, Runway APIs)
- Advanced FFmpeg editing (audio mixing, transitions)
- Subtitle generation
- Continuity checking system
- Visual style locking
- Parallel shot rendering
- Budget tracking
- Collaborative features
