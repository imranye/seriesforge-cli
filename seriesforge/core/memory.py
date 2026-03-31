"""Continuity memory system for tracking canon across episodes."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CharacterCanon(BaseModel):
    """Canonical character data."""
    name: str
    description: str
    voice: Optional[str] = None
    wardrobe: List[str] = Field(default_factory=list)  # Current wardrobe state
    relationships: Dict[str, str] = Field(default_factory=dict)
    last_appearance: Optional[str] = None  # Episode reference
    developments: List[str] = Field(default_factory=list)  # Character arc notes


class LocationCanon(BaseModel):
    """Canonical location data."""
    name: str
    description: str
    visual_style: Optional[str] = None
    last_appearance: Optional[str] = None
    state_changes: List[str] = Field(default_factory=list)


class PropCanon(BaseModel):
    """Canonical prop data."""
    name: str
    description: str
    owner: Optional[str] = None  # Character who owns it
    location: Optional[str] = None  # Current location
    history: List[str] = Field(default_factory=list)


class StoryCanon(BaseModel):
    """Canonical story data."""
    open_loops: List[str] = Field(default_factory=list)
    resolved_loops: List[str] = Field(default_factory=list)
    major_events: List[str] = Field(default_factory=list)
    timeline: List[str] = Field(default_factory=list)


class CanonMemory(BaseModel):
    """Complete canon memory for a show."""
    show_title: str
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_episode: int = 0
    
    characters: Dict[str, CharacterCanon] = Field(default_factory=dict)
    locations: Dict[str, LocationCanon] = Field(default_factory=dict)
    props: Dict[str, PropCanon] = Field(default_factory=dict)
    story: StoryCanon = Field(default_factory=StoryCanon)
    
    banned_contradictions: List[str] = Field(default_factory=list)
    running_jokes: List[str] = Field(default_factory=list)
    
    def add_character(self, character: CharacterCanon):
        """Add or update a character."""
        self.characters[character.name] = character
        self.updated_at = datetime.utcnow()
    
    def get_character(self, name: str) -> Optional[CharacterCanon]:
        """Get character by name."""
        return self.characters.get(name)
    
    def add_location(self, location: LocationCanon):
        """Add or update a location."""
        self.locations[location.name] = location
        self.updated_at = datetime.utcnow()
    
    def add_prop(self, prop: PropCanon):
        """Add or update a prop."""
        self.props[prop.name] = prop
        self.updated_at = datetime.utcnow()
    
    def add_open_loop(self, loop: str):
        """Add an open story loop."""
        if loop not in self.story.open_loops:
            self.story.open_loops.append(loop)
            self.updated_at = datetime.utcnow()
    
    def resolve_loop(self, loop: str):
        """Resolve an open loop."""
        if loop in self.story.open_loops:
            self.story.open_loops.remove(loop)
            self.story.resolved_loops.append(loop)
            self.updated_at = datetime.utcnow()
    
    def add_contradiction(self, contradiction: str):
        """Add a banned contradiction."""
        if contradiction not in self.banned_contradictions:
            self.banned_contradictions.append(contradiction)
            self.updated_at = datetime.utcnow()
    
    def get_continuity_notes(self, episode: int) -> str:
        """Generate continuity notes for a new episode."""
        notes = []
        
        notes.append(f"=== Continuity Notes for Episode {episode} ===\n")
        
        if self.story.open_loops:
            notes.append("OPEN STORY LOOPS:")
            for loop in self.story.open_loops:
                notes.append(f"- {loop}")
            notes.append("")
        
        if self.characters:
            notes.append("CHARACTER STATUS:")
            for name, char in self.characters.items():
                notes.append(f"- {name}: {char.description[:100]}...")
                if char.wardrobe:
                    notes.append(f"  Wardrobe: {', '.join(char.wardrobe)}")
            notes.append("")
        
        if self.banned_contradictions:
            notes.append("DO NOT CONTRADICT:")
            for contradiction in self.banned_contradictions:
                notes.append(f"- {contradiction}")
            notes.append("")
        
        if self.running_jokes:
            notes.append("RUNNING JOKES (consider callbacks):")
            for joke in self.running_jokes:
                notes.append(f"- {joke}")
            notes.append("")
        
        return "\n".join(notes)


def load_canon(project_path: Path) -> Optional[CanonMemory]:
    """Load canon memory from project."""
    canon_path = project_path / "bible" / "canon.json"
    if not canon_path.exists():
        return None
    
    with open(canon_path) as f:
        data = json.load(f)
    
    # Parse nested models
    characters = {
        name: CharacterCanon(**char_data)
        for name, char_data in data.get("characters", {}).items()
    }
    
    locations = {
        name: LocationCanon(**loc_data)
        for name, loc_data in data.get("locations", {}).items()
    }
    
    props = {
        name: PropCanon(**prop_data)
        for name, prop_data in data.get("props", {}).items()
    }
    
    story_data = data.get("story", {})
    story = StoryCanon(**story_data) if story_data else StoryCanon()
    
    return CanonMemory(
        show_title=data.get("show_title", ""),
        version=data.get("version", "1.0"),
        characters=characters,
        locations=locations,
        props=props,
        story=story,
        banned_contradictions=data.get("banned_contradictions", []),
        running_jokes=data.get("running_jokes", []),
    )


def save_canon(canon: CanonMemory, project_path: Path):
    """Save canon memory to project."""
    canon_path = project_path / "bible" / "canon.json"
    
    data = canon.model_dump()
    
    with open(canon_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return canon_path


def init_canon_from_bible(project_path: Path) -> CanonMemory:
    """Initialize canon memory from show bible."""
    import yaml
    
    bible_yaml = project_path / "bible" / "characters.yaml"
    if not bible_yaml.exists():
        raise FileNotFoundError("No characters.yaml found. Run bible generate first.")
    
    with open(bible_yaml) as f:
        bible_data = yaml.safe_load(f)
    
    canon = CanonMemory(show_title=bible_data.get("title", "Untitled"))
    
    # Add characters
    for char_data in bible_data.get("characters", []):
        character = CharacterCanon(
            name=char_data["name"],
            description=char_data["description"],
            voice=char_data.get("voice"),
            wardrobe=char_data.get("wardrobe", "").split(", ") if char_data.get("wardrobe") else [],
            relationships=char_data.get("relationships", {}),
        )
        canon.add_character(character)
    
    # Add locations
    for loc_data in bible_data.get("locations", []):
        location = LocationCanon(
            name=loc_data["name"],
            description=loc_data["description"],
            visual_style=loc_data.get("visual_style"),
        )
        canon.add_location(location)
    
    # Add running jokes
    canon.running_jokes = bible_data.get("running_jokes", [])
    
    return canon
