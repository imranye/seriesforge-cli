"""Quality control and continuity checking."""

import asyncio
import json
from pathlib import Path

import typer

from seriesforge.providers.llm import ChatMessage, create_provider


QC_PROMPT = """
You are a TV show continuity supervisor. Check this episode for continuity errors.

Show Bible:
{bible}

Episode Script:
{script}

Check for:
1. Character continuity - do characters appear consistently? Any unexplained absences?
2. Wardrobe continuity - do characters wear consistent clothing?
3. Location continuity - are locations used consistently?
4. Timeline continuity - does the story timeline make sense?
5. Prop continuity - are important props tracked consistently?
6. Character voice - do characters speak consistently with their established voices?
7. Plot holes - any logical inconsistencies?

Output a valid JSON object:
{{
  "episode": {episode},
  "checks_passed": true/false,
  "score": 0-100,
  "issues": [
    {{
      "type": "character|wardrobe|location|timeline|prop|voice|plot",
      "severity": "critical|warning|info",
      "description": "what the issue is",
      "scene_reference": "where it appears",
      "suggestion": "how to fix it"
    }}
  ],
  "summary": "brief summary of continuity status"
}}
"""


async def run_qc_llm(
    bible_path: Path,
    script_path: Path,
    episode: int,
    provider_name: str = "openai",
    api_key: str = "",
) -> dict:
    """Run QC check using LLM."""
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    script_content = script_path.read_text() if script_path.exists() else ""
    
    prompt = QC_PROMPT.format(
        bible=bible_content[:8000],
        script=script_content[:12000],
        episode=episode,
    )
    
    provider = create_provider(provider_name, {"api_key": api_key})
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.5)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    return json.loads(content)


def run_basic_checks(episode_path: Path) -> list:
    """Run basic file-based QC checks."""
    issues = []
    
    # Check required files exist
    required_files = [
        "outline.md",
        "script.fountain",
        "shots.yaml",
    ]
    
    for filename in required_files:
        if not (episode_path / filename).exists():
            issues.append({
                "type": "missing_file",
                "severity": "critical",
                "description": f"Required file missing: {filename}",
            })
    
    # Check video shots have corresponding files
    shots_path = episode_path / "shots.yaml"
    video_path = episode_path / "video"
    
    if shots_path.exists() and video_path.exists():
        import yaml
        with open(shots_path) as f:
            shots_data = yaml.safe_load(f)
        
        shots = shots_data.get("shots", [])
        for shot in shots:
            shot_num = shot["shot_number"]
            expected_file = video_path / f"shot_{shot_num:03d}.mp4"
            if not expected_file.exists():
                issues.append({
                    "type": "missing_video",
                    "severity": "warning",
                    "description": f"Shot {shot_num} video not found",
                })
    
    return issues


def run_qc_cli(episode: int = 1, season: int = 1):
    """CLI entry point for QC."""
    import os
    
    project_path = Path.cwd()
    
    episode_path = (
        project_path
        / "seasons"
        / f"season_{season:02d}"
        / "episodes"
        / f"ep_{episode:02d}"
    )
    qc_path = episode_path / "qc"
    qc_path.mkdir(exist_ok=True)
    
    typer.echo(f"Running QC for episode {episode}...")
    
    # Run basic checks
    typer.echo("  Running basic file checks...")
    basic_issues = run_basic_checks(episode_path)
    
    # Run LLM-based continuity check
    api_key = os.environ.get("OPENAI_API_KEY", "")
    llm_issues = []
    
    if api_key:
        typer.echo("  Running continuity analysis...")
        bible_path = project_path / "bible" / "show_bible.md"
        script_path = episode_path / f"script_ep{episode:02d}.fountain"
        
        try:
            qc_result = asyncio.run(
                run_qc_llm(bible_path, script_path, episode, "openai", api_key)
            )
            llm_issues = qc_result.get("issues", [])
            
            typer.echo(f"  Continuity score: {qc_result.get('score', 'N/A')}/100")
        except Exception as e:
            typer.echo(f"  Warning: LLM QC failed: {e}")
    else:
        typer.echo("  Skipping LLM continuity check (no OPENAI_API_KEY)")
    
    # Combine all issues
    all_issues = basic_issues + llm_issues
    
    # Count by severity
    critical = len([i for i in all_issues if i.get("severity") == "critical"])
    warnings = len([i for i in all_issues if i.get("severity") == "warning"])
    info = len([i for i in all_issues if i.get("severity") == "info"])
    
    # Save report
    report = {
        "episode": episode,
        "total_issues": len(all_issues),
        "critical": critical,
        "warnings": warnings,
        "info": info,
        "issues": all_issues,
    }
    
    report_path = qc_path / "qc_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    typer.echo(f"\n{'='*50}")
    typer.echo("QC REPORT")
    typer.echo(f"{'='*50}")
    typer.echo(f"Critical: {critical}")
    typer.echo(f"Warnings: {warnings}")
    typer.echo(f"Info: {info}")
    typer.echo(f"Total: {len(all_issues)}")
    
    if all_issues:
        typer.echo(f"\nIssues:")
        for issue in all_issues[:10]:  # Show first 10
            severity = issue.get("severity", "unknown").upper()
            issue_type = issue.get("type", "unknown")
            description = issue.get("description", "No description")
            typer.echo(f"  [{severity}] {issue_type}: {description}")
        
        if len(all_issues) > 10:
            typer.echo(f"  ... and {len(all_issues) - 10} more")
    
    typer.echo(f"\nReport: {report_path}")
    
    # Exit with error if critical issues
    if critical > 0:
        raise typer.Exit(code=1)
