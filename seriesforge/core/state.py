"""Pipeline state tracking - tracks progress and propagation debts."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class StageState:
    """State of a pipeline stage."""
    name: str
    status: str  # pending, running, completed, failed, needs_revision
    completed_at: Optional[str] = None
    score: Optional[float] = None
    attempts: int = 0
    error: Optional[str] = None


@dataclass
class PropagationDebt:
    """A change that needs to propagate downstream."""
    source_stage: str
    affected_stages: List[str]
    description: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False


class PipelineState:
    """Tracks overall pipeline state."""
    
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.episode: int = 1
        self.season: int = 1
        self.stages: Dict[str, StageState] = {}
        self.propagation_debts: List[PropagationDebt] = []
        self.last_updated: str = datetime.utcnow().isoformat()
        self.load()
    
    def load(self):
        """Load state from file."""
        if self.state_path.exists():
            data = json.loads(self.state_path.read_text())
            self.episode = data.get("episode", 1)
            self.season = data.get("season", 1)
            self.stages = {
                name: StageState(**stage)
                for name, stage in data.get("stages", {}).items()
            }
            self.propagation_debts = [
                PropagationDebt(**debt)
                for debt in data.get("propagation_debts", [])
            ]
            self.last_updated = data.get("last_updated", datetime.utcnow().isoformat())
    
    def save(self):
        """Save state to file."""
        self.last_updated = datetime.utcnow().isoformat()
        data = {
            "episode": self.episode,
            "season": self.season,
            "stages": {name: asdict(stage) for name, stage in self.stages.items()},
            "propagation_debts": [asdict(debt) for debt in self.propagation_debts],
            "last_updated": self.last_updated,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, indent=2))
    
    def set_stage_status(self, stage_name: str, status: str, score: Optional[float] = None):
        """Update a stage's status."""
        if stage_name in self.stages:
            self.stages[stage_name].status = status
            self.stages[stage_name].attempts += 1
            if score is not None:
                self.stages[stage_name].score = score
            if status == "completed":
                self.stages[stage_name].completed_at = datetime.utcnow().isoformat()
        else:
            self.stages[stage_name] = StageState(
                name=stage_name,
                status=status,
                attempts=1,
                score=score,
                completed_at=datetime.utcnow().isoformat() if status == "completed" else None,
            )
        self.save()
    
    def add_propagation_debt(self, source: str, affected: List[str], description: str):
        """Add a propagation debt."""
        self.propagation_debts.append(PropagationDebt(
            source_stage=source,
            affected_stages=affected,
            description=description,
        ))
        self.save()
    
    def resolve_debt(self, debt_index: int):
        """Mark a debt as resolved."""
        if debt_index < len(self.propagation_debts):
            self.propagation_debts[debt_index].resolved = True
            self.save()
    
    def get_unresolved_debts(self) -> List[PropagationDebt]:
        """Get all unresolved propagation debts."""
        return [d for d in self.propagation_debts if not d.resolved]
    
    def stage_passed(self, stage_name: str, threshold: float = 6.0) -> bool:
        """Check if a stage passed its threshold."""
        stage = self.stages.get(stage_name)
        if not stage:
            return False
        return stage.score is not None and stage.score >= threshold
    
    def get_stage_attempts(self, stage_name: str) -> int:
        """Get number of attempts for a stage."""
        stage = self.stages.get(stage_name)
        return stage.attempts if stage else 0
