"""Showrunner panel - 4-persona episode evaluation."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from seriesforge.providers.llm import ChatMessage, create_provider


@dataclass
class PanelReview:
    """Review from 4-persona showrunner panel."""
    comedy_score: float
    drama_score: float
    pacing_score: float
    budget_score: float
    overall_score: float
    reviews: Dict[str, Dict[str, Any]]
    consensus_issues: List[str]
    consensus_suggestions: List[str]


async def showrunner_panel_review(
    script_text: str,
    bible_path: Path,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> PanelReview:
    """Get review from 4-persona showrunner panel."""
    
    bible_content = bible_path.read_text() if bible_path.exists() else ""
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    prompt = f"""You are a 4-persona showrunner panel evaluating a TV episode.

SHOW BIBLE:
{bible_content[:8000]}

SCRIPT:
{script_text[:40000]}

Four panelists review independently, then reach consensus:

1. COMEDY EDITOR - Focus on jokes, timing, laugh density, comedic beats
2. DRAMA EDITOR - Focus on emotional arcs, character depth, dramatic tension
3. PACING EDITOR - Focus on act breaks, momentum, scene transitions, runtime
4. BUDGET EDITOR - Focus on feasibility, location count, VFX, cast size

Output valid JSON:
{{
  "comedy_score": 7.5,
  "drama_score": 8.0,
  "pacing_score": 6.5,
  "budget_score": 9.0,
  "overall_score": 7.75,
  "reviews": {{
    "comedy": {{
      "score": 7.5,
      "notes": "specific comedy feedback",
      "issues": ["issue1"],
      "suggestions": ["suggestion1"]
    }},
    "drama": {{ ... }},
    "pacing": {{ ... }},
    "budget": {{ ... }}
  }},
  "consensus_issues": ["issues all panelists agree on"],
  "consensus_suggestions": ["actionable fixes everyone supports"]
}}
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
    
    return PanelReview(
        comedy_score=data["comedy_score"],
        drama_score=data["drama_score"],
        pacing_score=data["pacing_score"],
        budget_score=data["budget_score"],
        overall_score=data["overall_score"],
        reviews=data["reviews"],
        consensus_issues=data["consensus_issues"],
        consensus_suggestions=data["consensus_suggestions"],
    )
