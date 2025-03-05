import abc
import logging
import time
import random
from typing import Dict, List, Tuple, Optional, Any, Set

from config.settings import SCRAPER_SETTINGS
from core.database import Database
from core.parsers import ParserRegistry

logger = logging.getLogger(__name__)

class BaseScraper(abc.ABC):
    """Abstract base class for all ransomware scrapers"""
    
    def __init__(self, name: str, output_dir: str):
        self.name = name
        self.group_id = name.lower()
        self.output_dir = output_dir
        self.db = Database(output_dir)
        self.parser_registry = ParserRegistry()
        
        # Initialize parsers
        self.register_parsers()
    
    @abc.abstractmethod
    def register_parsers(self) -> None:
        """Register HTML parsers for this ransomware group"""
        pass
    
    @abc.abstractmethod
    def get_default_mirrors(self) -> List[str]:
        """Return default mirror list for this ransomware site"""
        pass
    
    def get_mirrors(self) -> List[str]:
        """Get list of mirrors, prioritizing known working ones"""
        default_mirrors = self.get_default_mirrors()
        mirrors = self.db.get_working_mirrors(self.group_id, default_mirrors)
        logger.info(f"Got {len(mirrors)} mirrors for {self.name}")
        return mirrors
    
    def update_mirror_stats(self, mirror: str, success: bool = True) -> None:
        """Update statistics about mirror reliability"""
        self.db.update_mirror_stats(self.group_id, mirror, success)
    
    def test_mirror(self, browser: Any, mirror: str) -> bool:
        """Test if a mirror is working and contains expected content"""
        url = f"http://{mirror}"
        html_content = browser.fetch_page(url)
        
        if not html_content:
            return False
            
        # Test for group-specific identifiers
        return self.contains_group_identifiers(html_content)
    
    @abc.abstractmethod
    def contains_group_identifiers(self, html_content: str) -> bool:
        """Check if HTML contains identifiers for this ransomware group"""
        pass
    
    def scrape_victims(self, browser: Any, mirror: str) -> List[Dict]:
        """Scrape victim list from ransomware site"""
        url = self.build_victim_list_url(mirror)
        html_content = browser.fetch_page(url)
        
        if not html_content:
            return []
            
        victims = self.parser_registry.parse_victim_list(html_content)
        
        # Limit to the most recent victims
        max_victims = SCRAPER_SETTINGS.get("max_victims_per_group", 5)
        return victims[:max_victims] if len(victims) > max_victims else victims
    
    def get_victim_details(self, browser: Any, victim: Dict, mirror: str) -> Dict:
        """Get detailed information about a victim"""
        detail_url = victim.get('detail_link')
        if not detail_url:
            return {}
            
        # Process URL
        if detail_url.startswith('/'):
            detail_url = detail_url[1:]
            
        url = f"http://{mirror}/{detail_url}"
        html_content = browser.fetch_page(url)
        
        if not html_content:
            return {}
            
        return self.parser_registry.parse_victim_details(html_content)
    
    def build_victim_list_url(self, mirror: str) -> str:
        """Build URL for victim list page - override if needed"""
        return f"http://{mirror}"
    
    def run(self, browser: Any, incremental: bool = True) -> Dict:
        """Execute full scraping process and return results"""
        results = {
            "group": self.name,
            "victims": [],
            "new_victims": [],
            "updated_victims": [],
            "successful_mirror": None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "incremental": incremental
        }
        
        # Get mirrors to try
        mirrors = self.get_mirrors()
        logger.info(f"Trying {len(mirrors)} mirrors for {self.name}")
        
        # Try each mirror
        for mirror in mirrors:
            try:
                logger.info(f"Testing mirror: {mirror}")
                if not self.test_mirror(browser, mirror):
                    logger.warning(f"Mirror {mirror} failed test")
                    self.update_mirror_stats(mirror, success=False)
                    continue
                    
                logger.info(f"Mirror {mirror} is working")
                self.update_mirror_stats(mirror, success=True)
                results["successful_mirror"] = mirror
                
                # Scrape victim list
                all_victims = self.scrape_victims(browser, mirror)
                if not all_victims:
                    logger.warning(f"No victims found on {mirror}")
                    continue
                    
                logger.info(f"Found {len(all_victims)} victims on {mirror}")
                
                # If incremental is True, filter to only process new or updated victims
                if incremental:
                    victims_to_process = self.db.get_new_victims(all_victims, self.group_id)
                    if not victims_to_process:
                        logger.info("No new or updated victims found, skipping detail processing")
                        results["victims"] = all_victims
                        results["success"] = True
                        break
                    logger.info(f"Processing {len(victims_to_process)} new or updated victims")
                else:
                    victims_to_process = all_victims
                    logger.info(f"Processing all {len(victims_to_process)} victims (full mode)")
                
                # Get details for each victim to process
                for victim in victims_to_process:
                    # Add group identifier
                    victim['group'] = self.group_id
                    
                    logger.info(f"Getting details for {victim.get('domain')}")
                    details = self.get_victim_details(browser, victim, mirror)
                    victim.update(details)
                    
                    browser.random_delay()
                
                # Update all victims with any new details we processed
                if incremental and len(victims_to_process) < len(all_victims):
                    # Create lookup for processed victims
                    processed_domains = {v.get('domain'): v for v in victims_to_process if 'domain' in v}
                    # Update the all_victims list with processed details
                    for victim in all_victims:
                        domain = victim.get('domain')
                        if domain in processed_domains:
                            # Update with processed details
                            for key, value in processed_domains[domain].items():
                                victim[key] = value
                
                # Update database
                updated_db, new_victims, updated_victims = self.db.update_victim_database(
                    all_victims, self.group_id
                )
                
                results["victims"] = all_victims
                results["new_victims"] = new_victims
                results["updated_victims"] = updated_victims
                results["success"] = True
                
                # First working mirror is enough
                break
                
            except Exception as e:
                logger.error(f"Error with mirror {mirror}: {e}")
                self.update_mirror_stats(mirror, success=False)
        
        return results