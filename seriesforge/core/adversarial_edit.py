import json
"""Adversarial editing - cut filler and tighten scripts."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from seriesforge.providers.llm import ChatMessage, create_provider


@dataclass
class CutBrief:
    """Brief for what to cut from a script."""
    cuts: List[Dict[str, str]]
    estimated_page_reduction: float
    summary: str


async def generate_cut_brief(
    script_text: str,
    target_reduction: float = 10.0,
    provider_name: str = "openrouter",
    api_key: Optional[str] = None,
) -> CutBrief:
    """Generate adversarial edit brief - optimized for speed."""
    
    model = "anthropic/claude-3.5-haiku" if provider_name == "openrouter" else None
    
    provider = create_provider(provider_name, {"api_key": api_key or "", "model": model})
    
    prompt = f"""Adversarial TV editor. Find cuts to tighten script.

SCRIPT (first 3000 chars):
{script_text[:3000]}

Target: {target_reduction}% reduction

Find filler: weak dialogue, redundant action, over-explanation.

Output JSON only:
{{
  "cuts": [
    {{"type": "filler", "location": "...", "text": "...", "reason": "..."}}
  ],
  "estimated_page_reduction": 0.5,
  "summary": "..."
}}
"""
    
    messages = [
        ChatMessage(role="system", content="JSON API only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.3, max_tokens=500)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    return CutBrief(
        cuts=data["cuts"],
        estimated_page_reduction=data["estimated_page_reduction"],
        summary=data["summary"],
    )


async def apply_cuts(
    script_text: str,
    cut_brief: CutBrief,
    provider_name: str = "openrouter",
    api_key: Optional[str] = None,
) -> str:
    """Apply cuts to script and return revised version."""
    
    model = "anthropic/claude-3.5-haiku" if provider_name == "openrouter" else None
    
    provider = create_provider(provider_name, {"api_key": api_key or "", "model": model})
    
    cuts_text = "\n".join([f"- {c['type']}: {c['text'][:50]}..." for c in cut_brief.cuts[:10]])
    
    prompt = f"""Apply these cuts to tighten the script:

CUTS TO MAKE:
{cuts_text}

Original script:
{script_text[:35000]}

Output ONLY the revised script with cuts applied. Maintain Fountain format."""
    
    messages = [
        ChatMessage(role="system", content="Output Fountain format only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.5, max_tokens=8000)
    
    return response.content


def mechanical_cuts(script_text: str) -> List[Dict[str, str]]:
    """Fast mechanical cuts using regex - no LLM needed."""
    
    cuts = []
    
    # Common filler patterns
    filler_patterns = [
        (r"\b(I mean|you know|like|sort of|kind of|basically|literally)\b", "filler_words"),
        (r"\b(um|uh|ah|er|hm)\b", "verbal_hesitations"),
        (r"^(She/He/They looked at him/her/them\.)", "redundant_action"),
        (r"\b(nods|smiles|frowns|sighs)\b", "overused_beats"),
    ]
    
    for pattern, cut_type in filler_patterns:
        matches = re.findall(pattern, script_text, re.IGNORECASE)
        if matches:
            cuts.append({
                "type": cut_type,
                "count": len(matches),
                "examples": list(set(matches))[:3],
            })
    
    return cuts
