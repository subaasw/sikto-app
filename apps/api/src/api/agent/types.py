from dataclasses import dataclass, field
from typing import Any

from api.planning.schema import ProductionPlan


@dataclass
class Message:
    role: str  # "system" | "user"
    content: str


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for the tool's arguments


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class Passage:
    content: str
    source_id: str
    score: float


@dataclass
class AgentRun:
    plan: ProductionPlan
    trace: list[ToolCall] = field(default_factory=list)
    retrieved: list[Passage] = field(default_factory=list)


class AgentError(RuntimeError):
    pass
