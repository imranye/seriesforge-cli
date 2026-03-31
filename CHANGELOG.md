# Changelog

All notable changes to SeriesForge CLI will be documented in this file.

## [0.1.0] - 2026-03-30

### Added
- **Core CLI**: Typer-based CLI with 14 command groups
- **Project Management**: `project init`, `status`, `validate`
- **Writing Pipeline**:
  - `bible generate` - LLM-powered show bible generation
  - `arc generate` - Season arc and episode summaries
  - `episode outline` - Detailed beat generation
  - `script write` - Fountain format screenplay writing
  - `script revise` - Feedback-based revision
  - `shots plan` - Video prompt generation from scripts
- **Media Generation**:
  - `voice generate` - TTS dialogue generation (ElevenLabs, OpenAI)
  - `video generate` - Shot rendering with parallel processing (Kling, Runway)
  - `subtitles generate` - Caption generation from audio or script
- **Assembly & Export**:
  - `edit assemble` - FFmpeg-based timeline assembly
  - `export package` - Delivery bundle with ZIP archive
- **Quality Control**:
  - `qc run` - Continuity checking and validation
- **Pipeline Orchestration**:
  - `pipeline run` - 10-stage automated pipeline
  - `pipeline resume` - Checkpoint-based recovery
- **Provider Abstractions**:
  - LLM: OpenAI, Anthropic
  - TTS: ElevenLabs, OpenAI
  - Video: Kling, Runway, Pika (placeholders)
- **Asset Management**:
  - Manifest system for tracking all generated assets
  - Continuity memory (canon.json) for cross-episode tracking
- **Performance**:
  - Parallel shot rendering with concurrency limiting
  - Async API calls throughout

### Technical
- Python 3.9+ compatible
- Pydantic models for data validation
- Async HTTP with httpx
- FFmpeg integration for video assembly
- YAML/JSON configuration
- MIT licensed

### Documentation
- Comprehensive README with examples
- Command-line help for all subcommands
- Project structure documentation

## [Unreleased]

### Planned
- Script revision with human-in-the-loop
- Advanced FFmpeg editing (audio mixing, transitions)
- Visual style locking
- Budget tracking
- Collaborative features
- Web dashboard (Phase 2)
