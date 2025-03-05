import logging
import re
from typing import Dict, List, Optional, Any, Callable
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

class HTMLParser:
    """Base class for HTML structure parsers"""
    
    def __init__(self, name):
        self.name = name
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the given HTML structure"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def parse_victim_list(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract victim entries from the list page"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def parse_victim_details(self, soup: BeautifulSoup) -> Dict:
        """Extract detailed victim information from the detail page"""
        raise NotImplementedError("Subclasses must implement this method")

class ParserRegistry:
    """Registry of HTML parsers that can be tried in sequence"""
    
    def __init__(self):
        self.list_parsers = []
        self.detail_parsers = []
    
    def register_list_parser(self, parser):
        """Add a parser for victim list pages"""
        self.list_parsers.append(parser)
    
    def register_detail_parser(self, parser):
        """Add a parser for victim detail pages"""
        self.detail_parsers.append(parser)
    
    def parse_victim_list(self, html_content: str) -> List[Dict]:
        """Try each registered list parser until one works"""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for parser in self.list_parsers:
            if parser.can_parse(soup):
                logger.info(f"Using list parser: {parser.name}")
                return parser.parse_victim_list(soup)
        
        logger.warning("No suitable parser found for victim list page")
        return []
    
    def parse_victim_details(self, html_content: str) -> Dict:
        """Try each registered detail parser until one works"""
        if not html_content:
            return {}
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for parser in self.detail_parsers:
            if parser.can_parse(soup):
                logger.info(f"Using detail parser: {parser.name}")
                return parser.parse_victim_details(soup)
        
        logger.warning("No suitable parser found for victim detail page")
        return {}

# Common utility functions for parsing
def extract_text_from_br_tags(element):
    """Extract text from elements with <br> tags, preserving structure"""
    result = []
    if not element:
        return ""
        
    for content in element.contents:
        if content.name == 'br':
            result.append('\n')
        elif isinstance(content, Tag):
            result.append(content.get_text())
        else:
            result.append(str(content))
    
    return ''.join(result)

def parse_structured_description(text):
    """Parse structured text to extract common fields like email, website, etc."""
    if not text:
        return {}
        
    info = {}
    lines = text.split('\n')
    
    # Initialize fields
    info['company_name'] = ""
    info['description'] = ""
    info['contact'] = {}
    info['data_size'] = ""
    info['file_links'] = []
    
    # Default fields to look for
    patterns = {
        'website': [r'web\s*site\s*:\s*([^\n]+)', r'site\s*:\s*([^\n]+)'],
        'email': [r'e-?mail\s*:\s*([^\n]+)', r'contact\s*:\s*([^\n]+)'],
        'phone': [r'phone\s*:\s*([^\n]+)', r'tel\s*:\s*([^\n]+)'],
        'address': [r'headquarters\s*:\s*([^\n]+)', r'address\s*:\s*([^\n]+)'],
        'data_size': [r'data\s+volume\s*:?\s*([0-9.]+\s*[KMGT]B)', r'total\s+data\s+volume\s*:?\s*([0-9.]+\s*[KMGT]B)']
    }
    
    # Look for company name at the start
    for i, line in enumerate(lines):
        if 'we are posting here the new company' in line.lower():
            if i+1 < len(lines) and lines[i+1].strip():
                company_match = re.search(r'"([^"]+)"', line)
                if company_match:
                    info['company_name'] = company_match.group(1)
            break
    
    # Look for description
    description_index = -1
    for i, line in enumerate(lines):
        if 'company description' in line.lower() and i+1 < len(lines):
            description_index = i
            break
    
    if description_index >= 0:
        description_lines = []
        i = description_index + 1
        # Collect lines until we hit another known section or empty line
        while i < len(lines) and not any(p in lines[i].lower() for p in ['headquarters:', 'web site:', 'e-mail:', 'phone:']):
            if lines[i].strip():
                description_lines.append(lines[i].strip())
            i += 1
        info['description'] = " ".join(description_lines)
    
    # Extract contact info
    contact_info = {}
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            for line in lines:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if field == 'data_size':
                        info['data_size'] = match.group(1)
                    else:
                        contact_info[field] = match.group(1).strip()
                    break
            if field in contact_info:
                break
    
    if contact_info:
        info['contact'] = contact_info
    
    # Look for file links (usually at the end)
    file_links = []
    file_section = False
    for line in lines:
        if 'files:' in line.lower() or file_section:
            file_section = True
            # Look for URLs in this line
            urls = re.findall(r'https?://[^\s<>"]+|http://[^\s<>"]+', line)
            if urls:
                file_links.extend(urls)
            # Also look for onion links
            onion_urls = re.findall(r'http://[a-zA-Z0-9]{16,56}\.onion[^\s<>"]*', line)
            if onion_urls:
                file_links.extend(onion_urls)
    
    if file_links:
        info['file_links'] = file_links
    
    return info

def extract_email(text: str) -> Optional[str]:
    """Extract email address from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def extract_ip(text: str) -> List[str]:
    """Extract IP addresses from text"""
    pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    return re.findall(pattern, text)

def extract_url(text: str) -> List[str]:
    """Extract URLs from text"""
    pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*'
    return re.findall(pattern, text)

def extract_onion_url(text: str) -> List[str]:
    """Extract .onion URLs from text"""
    pattern = r'http://[a-zA-Z0-9]{16,56}\.onion[^\s<>"]*'
    return re.findall(pattern, text)