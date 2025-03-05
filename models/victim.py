# models/victim.py
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class Victim:
    """Data model for ransomware victims"""
    domain: str
    group: str
    status: str
    description_preview: Optional[str] = None
    description_full: Optional[str] = None
    updated: Optional[str] = None
    first_seen: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    detail_link: Optional[str] = None
    views: Optional[int] = None
    deadline: Optional[str] = None
    data_size: Optional[str] = None
    contact_info: Dict = field(default_factory=dict)
    status_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "domain": self.domain,
            "group": self.group,
            "status": self.status,
            "description_preview": self.description_preview,
            "description_full": self.description_full,
            "updated": self.updated,
            "first_seen": self.first_seen,
            "detail_link": self.detail_link,
            "views": self.views,
            "deadline": self.deadline,
            "data_size": self.data_size,
            "contact_info": self.contact_info,
            "status_history": self.status_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Victim':
        """Create instance from dictionary"""
        return cls(
            domain=data.get("domain", ""),
            group=data.get("group", ""),
            status=data.get("status", ""),
            description_preview=data.get("description_preview"),
            description_full=data.get("description_full"),
            updated=data.get("updated"),
            first_seen=data.get("first_seen", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
            detail_link=data.get("detail_link"),
            views=data.get("views"),
            deadline=data.get("deadline"),
            data_size=data.get("data_size"),
            contact_info=data.get("contact_info", {}),
            status_history=data.get("status_history", [])
        )
