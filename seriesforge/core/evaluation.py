"""Episode evaluation with mechanical + LLM scoring."""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import asyncio

import yaml


@dataclass
class EvaluationScore:
    """Score breakdown for an episode."""
    mechanical_score: float  # 0-10, regex-based slop detection
    llm_score: float  # 0-10, LLM judge
    voice_adherence: float  # 0-10
    character_distinctiveness: float  # 0-10
    pacing: float  # 0-10
    beat_coverage: float  # 0-10
    overall: float  # weighted average
    issues: List[str]
    suggestions: List[str]


# Mechanical slop patterns (from autonovel slop-forensics)
SLOP_PATTERNS = {
    "filler_phrases": [
        r"\b(and so|and then|and just|but then|so then)\b",
        r"\b(very|really|really|quite|just|actually)\b",
        r"\b(kind of|sort of|sort of like|kind of like)\b",
        r"\b(like,|you know,|I mean|you know what I mean)\b",
    ],
    "ai_tells": [
        r"\b(in the end|in conclusion|ultimately|in essence)\b",
        r"\b(not only|but also|moreover|furthermore|additionally)\b",
        r"\b(it is important|it is clear|it is evident)\b",
        r"\b(as a|in order to|with regard to|when it comes to)\b",
    ],
    "clichés": [
        r"\b(time stood still|heart raced|stomach dropped|blood ran cold)\b",
        r"\b(looked him up and down|glared at|smirked|rolled their eyes)\b",
        r"\b(nodded sagely|shook their head in disbelief|let out a sigh)\b",
    ],
    "tell_not_show": [
        r"\b(was feeling|felt|was happy|was sad|was angry|was scared)\b",
        r"\b(thought to themself|wondered|realized|understood)\b",
    ],
}


def mechanical_slop_scan(script_text: str) -> Dict[str, Any]:
    """Scan for mechanical slop patterns without LLM."""
    results = {
        "total_issues": 0,
        "categories": {},
        "score": 10.0,  # Start at 10, deduct for issues
    }
    
    for category, patterns in SLOP_PATTERNS.items():
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, script_text, re.IGNORECASE)
            matches.extend(found)
        
        if matches:
            results["categories"][category] = {
                "count": len(matches),
                "examples": list(set(matches))[:5],  # Top 5 unique
            }
            results["total_issues"] += len(matches)
    
    # Score deduction: -0.5 per issue, floor at 0
    results["score"] = max(0, 10 - (results["total_issues"] * 0.5))
    
    return results


async def llm_judge_evaluation(
    script_text: str,
    bible_path: Path,
    outline_path: Path,
    provider_name: str = "openrouter",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """LLM-based episode evaluation - optimized for speed."""
    
    # Load context (minimal)
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    outline_content = outline_path.read_text() if outline_path.exists() else ""
    
    from seriesforge.providers.llm import ChatMessage, create_provider
    
    # Use faster model for evaluation
    model = None
    if provider_name == "openrouter":
        model = "anthropic/claude-3.5-haiku"  # Faster, cheaper
    elif provider_name == "anthropic":
        model = "claude-3-5-sonnet-20241022"
    
    provider = create_provider(provider_name, {"api_key": api_key or "", "model": model})
    
    # Extract just character names for evaluation
    import re
    char_names = re.findall(r'### (.+?)\n', bible_content[:2000])
    
    prompt = f"""Evaluate this TV script. Be concise.

CHARACTERS: {', '.join(char_names[:5])}

SCRIPT (first 2000 chars):
{script_text[:2000]}

Score 0-10:
1. voice_adherence: Character voices distinct?
2. pacing: Good rhythm and momentum?
3. prose_quality: Crisp action, natural dialogue?

Output JSON only:
{{
  "voice_adherence": 7.0,
  "character_distinctiveness": 7.0,
  "pacing": 7.0,
  "beat_coverage": 7.0,
  "prose_quality": 7.0,
  "overall": 7.0,
  "issues": ["issue1", "issue2"],
  "suggestions": ["fix1", "fix2"]
}}
"""
    
    messages = [
        ChatMessage(role="system", content="JSON API only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.3, max_tokens=500)
    
    # Parse JSON
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    return json.loads(content)


async def evaluate_episode(
    episode_path: Path,
    bible_path: Path,
    outline_path: Path,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> EvaluationScore:
    """Full episode evaluation (mechanical + LLM)."""
    
    script_text = episode_path.read_text()
    
    # Run both evaluations in parallel
    mechanical = mechanical_slop_scan(script_text)
    llm_results = await llm_judge_evaluation(
        script_text, bible_path, outline_path, provider_name, api_key
    )
    
    # Combine scores (40% mechanical, 60% LLM)
    overall = (
        mechanical["score"] * 0.4 +
        llm_results["overall"] * 0.6
    )
    
    return EvaluationScore(
        mechanical_score=mechanical["score"],
        llm_score=llm_results["overall"],
        voice_adherence=llm_results["voice_adherence"],
        character_distinctiveness=llm_results["character_distinctiveness"],
        pacing=llm_results["pacing"],
        beat_coverage=llm_results["beat_coverage"],
        overall=overall,
        issues=llm_results["issues"],
        suggestions=llm_results["suggestions"],
    )


def save_evaluation_report(
    score: EvaluationScore,
    output_path: Path,
):
    """Save evaluation report to file."""
    report = {
        "scores": asdict(score),
        "passed": score.overall >= 6.0,
        "threshold": 6.0,
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)
    
    return report
