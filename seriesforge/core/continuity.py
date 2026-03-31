"""Continuity tracking - canon database and contradiction detection."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

from seriesforge.providers.llm import ChatMessage, create_provider


@dataclass
class CanonFact:
    """A single canon fact."""
    category: str  # character, location, plot, lore, prop
    fact: str
    source: str  # which episode/file this came from
    episode: int
    season: int
    confidence: float  # 0-1, how certain this is canon
    added_at: str


@dataclass
class ContinuityError:
    """A detected continuity error."""
    error_type: str  # contradiction, unexplained_change, timeline_issue
    description: str
    location1: str  # where first version appears
    location2: str  # where contradiction appears
    severity: str  # critical, major, minor
    suggestion: str


class ContinuityDatabase:
    """Manages canon facts and detects contradictions."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.facts: List[CanonFact] = []
        self.load()
    
    def load(self):
        """Load database from file."""
        if self.db_path.exists():
            data = json.loads(self.db_path.read_text())
            self.facts = [
                CanonFact(**f) for f in data.get("facts", [])
            ]
    
    def save(self):
        """Save database to file."""
        data = {
            "facts": [asdict(f) for f in self.facts],
            "last_updated": datetime.utcnow().isoformat(),
        }
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(json.dumps(data, indent=2))
    
    def add_fact(self, fact: CanonFact):
        """Add a new canon fact."""
        # Check for duplicates
        for existing in self.facts:
            if existing.fact.lower() == fact.fact.lower():
                # Update confidence if same fact
                existing.confidence = max(existing.confidence, fact.confidence)
                return
        
        self.facts.append(fact)
        self.save()
    
    def get_facts_by_category(self, category: str) -> List[CanonFact]:
        """Get all facts in a category."""
        return [f for f in self.facts if f.category == category]
    
    def get_character_facts(self, character_name: str) -> List[CanonFact]:
        """Get all facts about a character."""
        return [
            f for f in self.facts
            if f.category == "character" and character_name.lower() in f.fact.lower()
        ]


async def extract_canon_facts(
    script_text: str,
    episode: int,
    season: int,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> List[CanonFact]:
    """Extract canon facts from a script."""
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    prompt = f"""Extract all canon facts from this TV script.

SCRIPT:
{script_text[:40000]}

Extract facts about:
- Characters (names, relationships, traits, backstory reveals)
- Locations (descriptions, rules, significance)
- Plot (events that happened, their outcomes)
- Lore (world rules, magic systems, technology)
- Props (important objects, their properties)

Output valid JSON array:
[
  {{
    "category": "character|location|plot|lore|prop",
    "fact": "clear, concise statement of the fact",
    "confidence": 0.9
  }}
]

Only extract facts that are explicitly stated or clearly implied.
Be specific, not vague.
"""
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.2)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    return [
        CanonFact(
            category=f["category"],
            fact=f["fact"],
            source=f"season_{season}_episode_{episode}",
            episode=episode,
            season=season,
            confidence=f.get("confidence", 0.8),
            added_at=datetime.utcnow().isoformat(),
        )
        for f in data
    ]


async def detect_continuity_errors(
    script_text: str,
    continuity_db: ContinuityDatabase,
    episode: int,
    season: int,
    provider_name: str = "anthropic",
    api_key: Optional[str] = None,
) -> List[ContinuityError]:
    """Detect continuity errors between script and canon database."""
    
    # Get all relevant facts from database
    all_facts = "\n".join([f.fact for f in continuity_db.facts])
    
    provider = create_provider(provider_name, {"api_key": api_key or ""})
    
    prompt = f"""Check this script for continuity errors against established canon.

ESTABLISHED CANON:
{all_facts[:20000]}

NEW SCRIPT (Season {season}, Episode {episode}):
{script_text[:40000]}

Find contradictions, unexplained changes, or timeline issues.

Output valid JSON array:
[
  {{
    "error_type": "contradiction|unexplained_change|timeline_issue",
    "description": "clear description of the error",
    "location1": "where original fact appears (e.g., S1E3)",
    "location2": "where contradiction appears",
    "severity": "critical|major|minor",
    "suggestion": "how to fix this"
  }}
]

Only report real errors, not preferences.
"""
    
    messages = [
        ChatMessage(role="system", content="You are a JSON API. Output valid JSON only."),
        ChatMessage(role="user", content=prompt),
    ]
    
    response = await provider.chat(messages, temperature=0.2)
    
    content = response.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    content = content.rstrip("```").strip()
    
    data = json.loads(content)
    
    return [
        ContinuityError(**error)
        for error in data
    ]
