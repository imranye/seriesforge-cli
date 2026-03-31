# SeriesForge CLI (autoseries)

An agentic CLI for AI-native TV production studios.

> From prompt to pilot, entirely from the terminal.

Inspired by [NousResearch/autonovel](https://github.com/NousResearch/autonovel) and [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

## What Changed (autoseries v2)

SeriesForge now includes autonovel's evaluation-driven pipeline:

- **Evaluation retry loop** - Scripts auto-retry until score ≥ 6.0/10
- **Adversarial editing** - Automatic cut recommendations and application
- **4-persona showrunner panel** - Comedy, drama, pacing, budget editors
- **Opus dual-persona review** - Showrunner + network exec with stopping conditions
- **Continuity tracking** - Canon database with contradiction detection
- **State tracking** - Pipeline state + propagation debts in `state.json`

## Installation

```bash
pip install seriesforge-cli
```

Or from source:

```bash
git clone https://github.com/imranye/seriesforge-cli
cd seriesforge-cli
pip install -e .
```

### API Keys

Set your API keys in `.env` or as environment variables:

```bash
# Option 1: OpenRouter (recommended - one key for all models)
export OPENROUTER_API_KEY=sk-or-***

# Option 2: Direct provider keys
export ANTHROPIC_API_KEY=sk-ant-***  # For Claude
export OPENAI_API_KEY=sk-***         # For GPT
```

**OpenRouter models:**
- `anthropic/claude-3.5-sonnet` (default for evaluation)
- `anthropic/claude-3.5-opus` (for Opus review loop)
## Quick Start

```bash
# Initialize a new project
seriesforge project init my-show
cd my-show

# Set your API key (OpenRouter recommended)
export OPENROUTER_API_KEY=sk-or-...

# Generate show bible (uses GPT-4o by default)
seriesforge bible generate --concept "A deadpan workplace comedy set inside an AI film studio"

# Generate season arc
seriesforge arc generate --season 1 --episodes 8

# Generate episode outline
seriesforge episode outline --episode 1

# Write the script (uses Claude 3.5 Sonnet by default)
seriesforge script write --episode 1

# Run revision loop (uses Claude 3.5 Opus by default)
seriesforge revision run --episode 1

# Or run the full pipeline
seriesforge pipeline run --episode 1 --auto
```

## The Pipeline

```
bible → arc → outline → script → revision → shots → voice → video → edit → qc → export
                              ↑          ↑
                        (retry loop)  (Opus review)
```

### Script Writing (with evaluation)

```bash
# Write with default settings (3 attempts, 6.0 threshold)
seriesforge script write --episode 1

# Custom settings
seriesforge script write --episode 1 --max-attempts 5 --threshold 7.0

# Skip adversarial editing
seriesforge script write --episode 1 --no-adversarial
```

**What happens:**
1. Generate draft from outline
2. Apply adversarial cuts (remove filler)
3. Evaluate (mechanical + LLM scoring)
4. If score < threshold, retry with feedback
5. Repeat until passed or max attempts

### Revision Loop (Opus review)

```bash
# Run revision loop
seriesforge revision run --episode 1 --max-rounds 6

# See what it does:
# 1. Get dual-persona review (showrunner + network exec)
# 2. Check stopping conditions
# 3. Apply revisions if needed
# 4. Repeat until "should_continue" = false
```

**Stopping conditions:**
- No major issues remaining
- Both reviewers score ≥ 7.5
- Only cosmetic/preferences left
- Further revision would diminish script

## New Commands

### Evaluation

```bash
# Evaluate a script (standalone)
seriesforge evaluate --episode 1 --season 1
```

Outputs:
- Mechanical score (slop detection)
- LLM judge score
- Voice adherence
- Character distinctiveness
- Pacing
- Beat coverage
- Overall score

### Continuity

```bash
# Check for continuity errors
seriesforge continuity check --episode 1 --season 1

# Extract canon facts
seriesforge continuity extract --episode 1 --season 1
```

### State

```bash
# View pipeline state
seriesforge state show

# Clear state
seriesforge state clear
```

## File Structure

```
my-show/
├── bible.md                 # Show bible
├── season_1_arc.md          # Season arc
├── s1e1_outline.md          # Episode outline
├── s1e1_script.md           # Final script
├── state.json               # Pipeline state (NEW)
├── continuity.json          # Canon database (NEW)
├── evals/                   # Evaluation reports (NEW)
│   └── s1e1_eval.json
└── revisions/               # Revision history (NEW)
    └── s1e1/
        ├── review_round_1.json
        ├── script_round_1.md
        └── ...
```

## Evaluation Scores

Scripts are evaluated on multiple dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Mechanical | 40% | Slop detection (regex-based) |
| Voice | 10% | Character voice adherence |
| Character | 15% | Distinctiveness without tags |
| Pacing | 15% | Act breaks, momentum |
| Beats | 10% | Outline coverage |
| Prose | 10% | Action lines, dialogue quality |

**Threshold:** 6.0/10 to pass (configurable)

## Adversarial Editing

Automatic cut recommendations:

- Filler dialogue (no plot/character value)
- Redundant action lines
- Over-explained moments
- Slow pacing sections
- Tell-not-show

Target: 10% reduction per pass

## Showrunner Panel

4-persona evaluation:

1. **Comedy Editor** - Jokes, timing, laugh density
2. **Drama Editor** - Emotional arcs, character depth
3. **Pacing Editor** - Act breaks, momentum, runtime
4. **Budget Editor** - Feasibility, locations, VFX, cast

Consensus issues = must-fix items

## Network Review

Dual-persona (Claude Opus):

1. **Showrunner** - Creative vision, authenticity, tone
2. **Network Exec** - Audience appeal, marketability, budget

Stops when:
- No major issues
- Scores ≥ 7.5 from both
- Only qualified hedges remain

## Continuity Tracking

Canon database tracks:

- Characters (names, relationships, traits, backstory)
- Locations (descriptions, rules, significance)
- Plot (events, outcomes)
- Lore (world rules, magic, technology)
- Props (important objects)

Auto-detects contradictions between episodes.

## State Tracking

`state.json` tracks:

- Stage status (pending, running, completed, failed, needs_revision)
- Scores per stage
- Attempt counts
- Propagation debts (changes that need downstream updates)

## Comparison: autonovel → autoseries

| autonovel | autoseries |
|-----------|------------|
| `world.md` | `bible.md` |
| `outline.md` | `season_arc.md` + `s1e1_outline.md` |
| `draft_chapter.py` | `script write` (with retry) |
| `evaluate.py` | `evaluate_episode()` |
| `adversarial_edit.py` | `generate_cut_brief()` |
| `reader_panel.py` | `showrunner_panel_review()` |
| `review.py` (Opus) | `network_review()` |
| `canon.md` | `continuity.json` |
| `state.json` | `state.json` |

## License

MIT
