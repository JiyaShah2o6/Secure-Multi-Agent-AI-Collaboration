from dataclasses import dataclass
from typing import Any


@dataclass
class AgentRequest:
    sender: str
    receiver: str
    customer_id: str
    requested_fields: list[str]
    purpose: str


@dataclass
class AgentResponse:
    status: str
    data: dict[str, Any]
    message: str = ""