"""Database models for DevAssist."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json


@dataclass
class BriefItem:
    """Individual item in a brief."""
    
    source: str  # github, jira
    item_type: str  # issue, pr, message, notification
    title: str
    priority: str  # high, medium, low
    status: str
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "item_type": self.item_type,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "url": self.url,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefItem":
        return cls(**data)


@dataclass
class Brief:
    """A morning brief snapshot."""
    
    id: str | None = None
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    summary: str = ""
    items: list[BriefItem] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    raw_response: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "sources_used": self.sources_used,
            "raw_response": self.raw_response,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Brief":
        items = [BriefItem.from_dict(item) for item in data.get("items", [])]
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            created_at=created_at or datetime.utcnow(),
            summary=data.get("summary", ""),
            items=items,
            sources_used=data.get("sources_used", []),
            raw_response=data.get("raw_response", ""),
        )
