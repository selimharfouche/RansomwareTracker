import logging
import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper
from core.parsers import HTMLParser, extract_text_from_br_tags, parse_structured_description

logger = logging.getLogger(__name__)

class LockBitListParserV1(HTMLParser):
    """Parser for LockBit victim list - first HTML structure"""
    
    def __init__(self):
        super().__init__("LockBit List Parser V1")
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the HTML structure"""
        return len(soup.select('a.post-block')) > 0
    
    def parse_victim_list(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract victim entries from the list page"""
        victim_entries = []
        
        for entry in soup.select('a.post-block'):
            victim = {}
            
            # Extract domain name
            domain_elem = entry.select_one('.post-title')
            if domain_elem:
                victim['domain'] = domain_elem.text.strip()
            
            # Extract status (published or countdown)
            status_elem = entry.select_one('.post-timer-end')
            if status_elem:
                victim['status'] = status_elem.text.strip().upper()
            
            # Extract description snippet
            desc_elem = entry.select_one('.post-block-text')
            if desc_elem:
                victim['description_preview'] = desc_elem.text.strip()[:200] + "..." if len(desc_elem.text.strip()) > 200 else desc_elem.text.strip()
            
            # Extract update timestamp
            time_elem = entry.select_one('.updated-post-date span')
            if time_elem:
                timestamp_text = time_elem.text.strip()
                if "Updated:" in timestamp_text:
                    timestamp_text = timestamp_text.split("Updated:")[1].strip()
                victim['updated'] = timestamp_text
            
            # Extract view count
            views_elem = entry.select_one('div[style*="opacity"] span[style*="font-weight: bold"]')
            if not views_elem:
                views_elem = entry.select_one('.views span[style*="font-weight: bold"]')
            
            if views_elem:
                try:
                    # Clean up and extract just the number
                    digits = re.findall(r'\d+', views_elem.text.strip())
                    if digits:
                        victim['views'] = int(digits[0])
                except ValueError:
                    victim['views'] = 0
            
            # Extract link to detailed page
            link_elem = entry.get('href')
            if link_elem:
                victim['detail_link'] = link_elem
            
            if victim and 'domain' in victim:
                victim_entries.append(victim)
        
        return victim_entries

class LockBitDetailParserV1(HTMLParser):
    """Parser for LockBit victim details - first HTML structure (post-company-content)"""
    
    def __init__(self):
        super().__init__("LockBit Detail Parser V1")
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the HTML structure"""
        return soup.select_one('.post-company-content .desc') is not None
    
    def parse_victim_details(self, soup: BeautifulSoup) -> Dict:
        """Extract detailed victim information"""
        details = {}
        
        # Extract full description
        desc_elem = soup.select_one('.post-company-content .desc')
        if desc_elem:
            # Handle HTML with <br> tags
            if desc_elem.find('br'):
                details['description_full'] = extract_text_from_br_tags(desc_elem)
            else:
                details['description_full'] = desc_elem.text.strip()
            
            # Parse structured data from description
            structured_data = parse_structured_description(details['description_full'])
            
            # Add structured data to details
            if structured_data.get('company_name'):
                details['company_name'] = structured_data['company_name']
            
            if structured_data.get('description'):
                details['business_description'] = structured_data['description']
            
            if structured_data.get('contact'):
                details['contact_info'] = structured_data['contact']
            
            if structured_data.get('data_size'):
                details['data_size'] = structured_data['data_size']
            
            if structured_data.get('file_links'):
                details['file_links'] = structured_data['file_links']
        
        # Extract deadline if present
        deadline_elem = soup.select_one('.post-banner-p')
        if deadline_elem and "Deadline:" in deadline_elem.text:
            details['deadline'] = deadline_elem.text.replace("Deadline:", "").strip()
        
        # Extract uploaded date
        upload_elem = soup.select_one('.uploaded-date-utc')
        if upload_elem:
            details['uploaded'] = upload_elem.text.strip()
        
        # Extract updated date
        update_elem = soup.select_one('.updated-date-utc')
        if update_elem:
            details['updated'] = update_elem.text.strip()
        
        return details

class LockBitDetailParserV2(HTMLParser):
    """Parser for LockBit victim details - second HTML structure (post-wrapper)"""
    
    def __init__(self):
        super().__init__("LockBit Detail Parser V2")
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the HTML structure"""
        return soup.select_one('.post-wrapper') is not None
    
    def parse_victim_details(self, soup: BeautifulSoup) -> Dict:
        """Extract detailed victim information"""
        details = {}
        
        # Extract full description
        desc_elem = soup.select_one('.post-company-content .desc')
        if desc_elem:
            # Handle HTML with <br> tags
            if desc_elem.find('br'):
                details['description_full'] = extract_text_from_br_tags(desc_elem)
            else:
                details['description_full'] = desc_elem.text.strip()
            
            # Parse structured data from description
            structured_data = parse_structured_description(details['description_full'])
            
            # Add structured data to details
            if structured_data.get('company_name'):
                details['company_name'] = structured_data['company_name']
            
            if structured_data.get('description'):
                details['business_description'] = structured_data['description']
            
            if structured_data.get('contact'):
                details['contact_info'] = structured_data['contact']
            
            if structured_data.get('data_size'):
                details['data_size'] = structured_data['data_size']
            
            if structured_data.get('file_links'):
                details['file_links'] = structured_data['file_links']
        
        # Extract deadline if present
        deadline_elem = soup.select_one('.post-banner-p')
        if deadline_elem and "Deadline:" in deadline_elem.text:
            details['deadline'] = deadline_elem.text.replace("Deadline:", "").strip()
        
        # Extract uploaded date
        upload_elem = soup.select_one('.uploaded-date-utc')
        if upload_elem:
            details['uploaded'] = upload_elem.text.strip()
        
        # Extract updated date
        update_elem = soup.select_one('.updated-date-utc')
        if update_elem:
            details['updated'] = update_elem.text.strip()
        
        return details

class LockBitDetailParserV3(HTMLParser):
    """Parser for LockBit victim details with multiple <br> tags pattern"""
    
    def __init__(self):
        super().__init__("LockBit Detail Parser V3")
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the HTML structure"""
        desc_elem = soup.select_one('.post-company-content .desc')
        return desc_elem is not None and desc_elem.find('br') is not None
    
    def parse_victim_details(self, soup: BeautifulSoup) -> Dict:
        """Extract detailed victim information with special handling for <br> tags"""
        details = {}
        
        # Extract full description
        desc_elem = soup.select_one('.post-company-content .desc')
        if desc_elem:
            # Convert <br> tags to newlines
            details['description_full'] = extract_text_from_br_tags(desc_elem)
            
            # Parse structured data from description
            structured_data = parse_structured_description(details['description_full'])
            
            # Add structured data to details
            if structured_data.get('company_name'):
                details['company_name'] = structured_data['company_name']
            
            if structured_data.get('description'):
                details['business_description'] = structured_data['description']
            
            if structured_data.get('contact'):
                details['contact_info'] = structured_data['contact']
            
            if structured_data.get('data_size'):
                details['data_size'] = structured_data['data_size']
            
            if structured_data.get('file_links'):
                details['file_links'] = structured_data['file_links']
                
            # Special handling for file links section
            text = details['description_full']
            if 'FILES:' in text:
                file_section = text.split('FILES:')[1].strip()
                links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', file_section)
                if links:
                    details['file_links'] = links
        
        # Extract deadline if present
        deadline_elem = soup.select_one('.post-banner-p')
        if deadline_elem and "Deadline:" in deadline_elem.text:
            details['deadline'] = deadline_elem.text.replace("Deadline:", "").strip()
        
        # Extract uploaded date
        upload_elem = soup.select_one('.uploaded-date-utc')
        if upload_elem:
            details['uploaded'] = upload_elem.text.strip()
        
        # Extract updated date
        update_elem = soup.select_one('.updated-date-utc')
        if update_elem:
            details['updated'] = update_elem.text.strip()
        
        return details

class GenericLockBitDetailParser(HTMLParser):
    """Fallback parser that tries a variety of selectors"""
    
    def __init__(self):
        super().__init__("LockBit Generic Detail Parser")
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """This parser is a catch-all fallback"""
        return True
    
    def parse_victim_details(self, soup: BeautifulSoup) -> Dict:
        """Try multiple approaches to extract information"""
        details = {}
        
        # Find description using multiple possible selectors
        desc_selectors = [
            '.post-company-content .desc',
            '.desc',
            '.post-description',
            '.post-text',
            'div[class*="desc"]',
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                # Handle HTML with <br> tags
                if desc_elem.find('br'):
                    details['description_full'] = extract_text_from_br_tags(desc_elem)
                else:
                    details['description_full'] = desc_elem.text.strip()
                
                # Try to extract structured data
                structured_data = parse_structured_description(details['description_full'])
                
                # Add structured data to details
                if structured_data.get('company_name'):
                    details['company_name'] = structured_data['company_name']
                
                if structured_data.get('description'):
                    details['business_description'] = structured_data['description']
                
                if structured_data.get('contact'):
                    details['contact_info'] = structured_data['contact']
                
                if structured_data.get('data_size'):
                    details['data_size'] = structured_data['data_size']
                
                if structured_data.get('file_links'):
                    details['file_links'] = structured_data['file_links']
                break
        
        # Try to find deadline with multiple selectors
        deadline_selectors = [
            '.post-banner-p',
            '.deadline',
            'p:contains("Deadline")',
            '[class*="deadline"]',
        ]
        
        for selector in deadline_selectors:
            try:
                deadline_elem = soup.select_one(selector)
                if deadline_elem and "Deadline:" in deadline_elem.text:
                    details['deadline'] = deadline_elem.text.replace("Deadline:", "").strip()
                    break
            except:
                continue
        
        # Try to extract dates
        date_selectors = {
            'uploaded': ['.uploaded-date-utc', '.upload-date', '[class*="upload"]'],
            'updated': ['.updated-date-utc', '.update-date', '[class*="update"]'],
        }
        
        for field, selectors in date_selectors.items():
            for selector in selectors:
                try:
                    date_elem = soup.select_one(selector)
                    if date_elem:
                        details[field] = date_elem.text.strip()
                        break
                except:
                    continue
        
        # Look for file links section
        if 'description_full' in details:
            text = details['description_full']
            if 'FILES:' in text:
                file_section = text.split('FILES:')[1].strip()
                links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', file_section)
                if links:
                    details['file_links'] = links
        
        return details

class LockBitScraper(BaseScraper):
    """Scraper for LockBit ransomware leak site"""
    
    def __init__(self, output_dir):
        super().__init__("LockBit", output_dir)
    
    def register_parsers(self):
        """Register HTML parsers for LockBit"""
        # Register list parsers
        self.parser_registry.register_list_parser(LockBitListParserV1())
        
        # Register detail parsers - order matters (most specific to most generic)
        self.parser_registry.register_detail_parser(LockBitDetailParserV3())  # First try the <br> tag handler
        self.parser_registry.register_detail_parser(LockBitDetailParserV2())  # Then try post-wrapper pattern
        self.parser_registry.register_detail_parser(LockBitDetailParserV1())  # Then try post-company pattern
        self.parser_registry.register_detail_parser(GenericLockBitDetailParser())  # Fallback parser
    
    def get_default_mirrors(self):
        """Return default mirror list for LockBit"""
        return [
            "lockbit3753ekiocyo5epmpy6klmejchjtzddoekjlnt6mu3qh4de2id.onion",
            "lockbit3g3ohd3katajf6zaehxz4h4cnhmz5t735zpltywhwpc6oy3id.onion",
            "lockbit3olp7oetlc4tl5zydnoluphh7fvdt5oa6arcp2757r7xkutid.onion",
            "lockbit435xk3ki62yun7z5nhwz6jyjdp2c64j5vge536if2eny3gtid.onion",
            "lockbit4lahhluquhoka3t4spqym2m3dhe66d6lr337glmnlgg2nndad.onion",
            "lockbit6knrauo3qafoksvl742vieqbujxw7rd6ofzdtapjb4rrawqad.onion",
            "lockbit7ouvrsdgtojeoj5hvu6bljqtghitekwpdy3b6y62ixtsu5jqd.onion"
        ]
    
    def contains_group_identifiers(self, html_content):
        """Check if HTML contains LockBit identifiers"""
        return "LockBit" in html_content or "lockbit" in html_content.lower()