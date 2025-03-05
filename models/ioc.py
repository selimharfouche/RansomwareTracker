# models/ioc.py
import re
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

@dataclass
class IOC:
    """Indicators of Compromise extracted from victim data"""
    domains: Set[str] = field(default_factory=set)
    emails: Set[str] = field(default_factory=set)
    ips: Set[str] = field(default_factory=set)
    urls: Set[str] = field(default_factory=set)
    
    def extract_from_text(self, text: str) -> None:
        """Extract IoCs from text content"""
        if not text:
            return
            
        # Extract domains
        # Simple domain extraction - can be enhanced with validation
        domain_pattern = r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
        domains = re.findall(domain_pattern, text)
        for domain in domains:
            self.domains.add(domain)
            
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        for email in emails:
            self.emails.add(email)
            
        # Extract IPs
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, text)
        for ip in ips:
            self.ips.add(ip)
            
        # Extract URLs
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*'
        urls = re.findall(url_pattern, text)
        for url in urls:
            self.urls.add(url)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary representation with sets converted to lists"""
        return {
            "domains": list(self.domains),
            "emails": list(self.emails),
            "ips": list(self.ips),
            "urls": list(self.urls)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[str]]) -> 'IOC':
        """Create instance from dictionary"""
        return cls(
            domains=set(data.get("domains", [])),
            emails=set(data.get("emails", [])),
            ips=set(data.get("ips", [])),
            urls=set(data.get("urls", []))
        )
