"""Network review - dual-persona (showrunner + network exec) with stopping conditions."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from seriesforge.providers.llm import ChatMessage, create_provider


@dataclass
class NetworkReview:
    """Dual-persona network review."""
    showrunner_review: Dict[str, Any]
    network_exec_review: Dict[str, Any]
    major_issues: List[str]
    minor_issues: List[str]
    actionable_items: List[str]
    should_continue: bool  # True if more revision needed
    stopping_reason: Optional[str]  # Why we should stop revising


async def network_review(
    script_text: str,
    bible_path: Path,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> NetworkReview:
    """Get dual-persona review from showrunner and network exec."""
    
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    prompt = f"""You are conducting a dual-persona network review of a TV episode.

SHOW BIBLE:
{bible_content[:8000]}

SCRIPT:
{script_text[:40000]}

Two reviewers:

1. SHOWRUNNER - Creative vision, character authenticity, tone consistency, artistic integrity
2. NETWORK EXECUTIVE - Audience appeal, marketability, budget, scheduling, advertiser-friendly

Each gives specific, actionable feedback. Then determine if more revision is needed.

CRITICAL: Be fair but honest. You don't have to find defects if the script is good.

Output valid JSON:
{{
  "showrunner_review": {{
    "score": 8.0,
    "strengths": ["what works well"],
    "concerns": ["creative concerns"],
    "suggestions": ["actionable creative fixes"]
  }},
  "network_exec_review": {{
    "score": 7.5,
    "strengths": ["what works"],
    "concerns": ["business/audience concerns"],
    "suggestions": ["actionable business fixes"]
  }},
  "major_issues": ["issues that MUST be fixed"],
  "minor_issues": ["nice-to-fix but not critical"],
  "actionable_items": ["prioritized list of fixes"],
  "should_continue": false,
  "stopping_reason": "no major issues remaining, only qualified hedges"
}}

Stopping conditions (set should_continue=false if ANY are met):
- No major issues (only minor or qualified hedges)
- Score >= 7.5 from both reviewers
- Actionable items are all cosmetic/preferences
- Further revision would diminish the script
"""
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.3)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    return NetworkReview(
        showrunner_review=data["showrunner_review"],
        network_exec_review=data["network_exec_review"],
        major_issues=data["major_issues"],
        minor_issues=data["minor_issues"],
        actionable_items=data["actionable_items"],
        should_continue=data["should_continue"],
        stopping_reason=data.get("stopping_reason"),
    )
