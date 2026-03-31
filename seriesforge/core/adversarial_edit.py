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
    cuts: List[Dict[str, str]]  # [{"type": "filler_dialogue", "text": "...", "reason": "..."}]
    estimated_page_reduction: float
    summary: str


async def generate_cut_brief(
    script_text: str,
    target_reduction: float = 10.0,  # Target 10% reduction
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> CutBrief:
    """Generate adversarial edit brief."""
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    prompt = f"""You are an adversarial TV editor. Your job is to find and recommend cuts.

SCRIPT:
{script_text[:40000]}

Target: Reduce by {target_reduction}% without losing story beats.

Find:
1. Filler dialogue (characters saying things that don't advance plot/reveal character)
2. Redundant action lines
3. Over-explained moments
4. Slow pacing sections
5. Tell-not-show moments

Output valid JSON:
{{
  "cuts": [
    {{
      "type": "filler_dialogue|redundant_action|over_explanation|slow_pacing|tell_not_show",
      "location": "scene description or page estimate",
      "text": "exact text to cut",
      "reason": "why this should be cut"
    }}
  ],
  "estimated_page_reduction": 2.5,
  "summary": "brief summary of what was cut and why"
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
    
    return CutBrief(
        cuts=data["cuts"],
        estimated_page_reduction=data["estimated_page_reduction"],
        summary=data["summary"],
    )


async def apply_cuts(
    script_text: str,
    cut_brief: CutBrief,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> str:
    """Apply cuts to script and return revised version."""
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    cuts_text = "\n".join([
        f"- {c['type']}: {c['text'][:100]}... (reason: {c['reason']})"
        for c in cut_brief.cuts
    ])
    
    prompt = f"""You are applying adversarial edits to a TV script.

CUTS TO APPLY:
{cuts_text}

ORIGINAL SCRIPT:
{script_text[:40000]}

Apply all cuts. Remove the specified text entirely. Tighten remaining dialogue where needed.
Output ONLY the revised script, no explanations.
"""
    
    messages = [
        ChatMessage(role="system", content="Output only the revised script text."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.3)
    return response.content


def mechanical_cuts(script_text: str) -> str:
    """Apply mechanical cuts (regex-based, no LLM)."""
    
    # Remove common filler
    fillers = [
        r"\b(and so|and then|and just|but then)\b\s+",
        r"\b(um|uh|like|you know|I mean)\b\s*",
        r"\s+\(beat\)\s*",
        r"\s+\(pause\)\s*",
    ]
    
    result = script_text
    for pattern in fillers:
        result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
    
    # Normalize whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r"\s+", " ", result)
    
    return result
