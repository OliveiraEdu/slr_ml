"""Provenance tracking for SLR screening decisions."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import hashlib
import json


class ActionType(str, Enum):
    IMPORT = "import"
    DEDUPE = "deduplication"
    SCREEN = "screening"
    REVIEW = "manual_review"
    EXTRACT = "extraction"
    EXPORT = "export"


@dataclass
class ScreeningAction:
    """Record of a screening action."""
    action_id: str
    action_type: ActionType
    timestamp: str
    user_id: Optional[str]
    session_id: str
    details: dict
    hash: str
    previous_hash: str


@dataclass
class ProvenanceChain:
    """Complete provenance chain for the SLR."""
    actions: list[ScreeningAction] = field(default_factory=list)
    paper_versions: dict = field(default_factory=dict)
    
    def add_action(
        self,
        action_type: ActionType,
        details: dict,
        user_id: Optional[str] = None,
        session_id: str = "default",
    ) -> str:
        """Add a new action to the chain."""
        previous_hash = self.actions[-1].hash if self.actions else "genesis"
        
        action_id = self._generate_action_id(action_type, details)
        
        action_data = {
            "action_type": action_type.value,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        
        action_hash = self._compute_hash(action_data, previous_hash)
        
        action = ScreeningAction(
            action_id=action_id,
            action_type=action_type,
            timestamp=action_data["timestamp"],
            user_id=user_id,
            session_id=session_id,
            details=details,
            hash=action_hash,
            previous_hash=previous_hash,
        )
        
        self.actions.append(action)
        return action_id
    
    def verify_chain(self) -> dict:
        """Verify integrity of the provenance chain."""
        if not self.actions:
            return {"valid": True, "message": "Empty chain", "breaks": []}
        
        breaks = []
        for i, action in enumerate(self.actions[1:], 1):
            expected_previous = self.actions[i - 1].hash
            if action.previous_hash != expected_previous:
                breaks.append({
                    "index": i,
                    "action_id": action.action_id,
                    "expected_previous": expected_previous,
                    "actual_previous": action.previous_hash,
                })
        
        computed_hash = self._compute_hash(
            {
                "action_type": action.action_type.value,
                "details": action.details,
                "timestamp": action.timestamp,
            },
            action.previous_hash,
        )
        
        if computed_hash != action.hash:
            breaks.append({
                "index": i,
                "action_id": action.action_id,
                "error": "Hash mismatch",
            })
        
        return {
            "valid": len(breaks) == 0,
            "total_actions": len(self.actions),
            "breaks": breaks,
            "message": "Chain intact" if not breaks else f"Chain broken at {len(breaks)} point(s)",
        }
    
    def get_paper_history(self, paper_id: str) -> list[dict]:
        """Get all actions affecting a specific paper."""
        history = []
        for action in self.actions:
            if paper_id in str(action.details.get("paper_ids", [])):
                history.append({
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "timestamp": action.timestamp,
                    "details": action.details,
                })
        return history
    
    def export_to_json(self, path: str):
        """Export provenance chain to JSON."""
        data = {
            "actions": [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type.value,
                    "timestamp": a.timestamp,
                    "user_id": a.user_id,
                    "session_id": a.session_id,
                    "details": a.details,
                    "hash": a.hash,
                    "previous_hash": a.previous_hash,
                }
                for a in self.actions
            ],
            "paper_versions": self.paper_versions,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _generate_action_id(self, action_type: ActionType, details: dict) -> str:
        """Generate unique action ID."""
        data = f"{action_type.value}:{datetime.now().isoformat()}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _compute_hash(self, data: dict, previous_hash: str) -> str:
        """Compute SHA-256 hash for action."""
        content = json.dumps(data, sort_keys=True) + previous_hash
        return hashlib.sha256(content.encode()).hexdigest()


class ScreeningAuditLog:
    """Audit log for screening decisions."""
    
    def __init__(self):
        self.logs: list[dict] = []
    
    def log_decision(
        self,
        paper_id: str,
        decision: str,
        confidence: float,
        method: str,
        reviewer: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        """Log a screening decision."""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "paper_id": paper_id,
            "decision": decision,
            "confidence": confidence,
            "method": method,
            "reviewer": reviewer,
            "notes": notes,
        })
    
    def log_batch_decision(
        self,
        decisions: list[dict],
        method: str,
        reviewer: Optional[str] = None,
    ):
        """Log batch screening decisions."""
        for decision in decisions:
            self.log_decision(
                paper_id=decision["paper_id"],
                decision=decision["decision"],
                confidence=decision.get("confidence", 0.5),
                method=method,
                reviewer=reviewer,
                notes=decision.get("notes"),
            )
    
    def get_paper_log(self, paper_id: str) -> list[dict]:
        """Get all logs for a specific paper."""
        return [log for log in self.logs if log["paper_id"] == paper_id]
    
    def get_reviewer_activity(self, reviewer: str) -> dict:
        """Get activity summary for a reviewer."""
        reviewer_logs = [log for log in self.logs if log.get("reviewer") == reviewer]
        
        decisions = {}
        for log in reviewer_logs:
            d = log["decision"]
            decisions[d] = decisions.get(d, 0) + 1
        
        return {
            "reviewer": reviewer,
            "total_decisions": len(reviewer_logs),
            "decisions_by_type": decisions,
            "avg_confidence": sum(log["confidence"] for log in reviewer_logs) / len(reviewer_logs) if reviewer_logs else 0,
        }
    
    def export_csv(self, path: str):
        """Export audit log to CSV."""
        import csv
        
        if not self.logs:
            return
        
        fieldnames = ["timestamp", "paper_id", "decision", "confidence", "method", "reviewer", "notes"]
        
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.logs)
