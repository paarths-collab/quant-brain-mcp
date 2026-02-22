from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class AgentState:
    query: str
    emotional_status: Dict[str, Any] = field(default_factory=dict)
    plan: List[Dict] = field(default_factory=list)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    divergence_flags: List[Dict] = field(default_factory=list)
    reflection_result: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    final_report: str = ""
    human_approved: Optional[bool] = None
    session_id: str = "default"
    execution_log: List[Dict] = field(default_factory=list)
