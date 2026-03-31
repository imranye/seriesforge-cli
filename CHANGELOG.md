# Changelog

## [2.0.0] - 2026-03-31

### Added (autoseries features)

- **Evaluation retry loop** - Scripts auto-retry until score ≥ 6.0/10
- **Adversarial editing** - Automatic cut recommendations and application
- **4-persona showrunner panel** - Comedy, drama, pacing, budget editors
- **Opus dual-persona review** - Showrunner + network exec with stopping conditions
- **Continuity tracking** - Canon database with contradiction detection
- **State tracking** - Pipeline state + propagation debts in `state.json`

### New Commands

- `seriesforge script write` - Write with evaluation retry loop
- `seriesforge revision run` - Opus review loop with stopping conditions
- `seriesforge evaluate` - Standalone evaluation
- `seriesforge continuity check` - Check for continuity errors
- `seriesforge continuity extract` - Extract canon facts
- `seriesforge state show` - View pipeline state

### Changed

- Pipeline now includes `revision` stage between `script` and `shots`
- Scripts require `ANTHROPIC_API_KEY` for evaluation
- All scripts now track state in `state.json`

### Inspiration

- [NousResearch/autonovel](https://github.com/NousResearch/autonovel) - Evaluation-driven pipeline
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) - Modify-evaluate-keep loop

## [1.0.0] - 2026-03-30

### Added

- Initial release
- Show bible generation
- Season arc generation
- Episode outline generation
- Script writing
- Shot planning
- Media generation pipeline

