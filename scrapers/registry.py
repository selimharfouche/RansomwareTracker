# scrapers/registry.py
import logging
import importlib
import inspect
from typing import Dict, List, Any

from scrapers.base import BaseScraper
from config.settings import ENABLED_GROUPS

logger = logging.getLogger(__name__)

class ScraperRegistry:
    """Registry for all ransomware scrapers"""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.scrapers = {}
        self.load_scrapers()
    
    def load_scrapers(self) -> None:
        """Load all enabled scrapers"""
        for group_id in ENABLED_GROUPS:
            try:
                # Dynamically import the module
                module_name = f"scrapers.{group_id}"
                module = importlib.import_module(module_name)
                
                # Find scraper class in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and issubclass(obj, BaseScraper) and 
                            obj != BaseScraper and name.lower().endswith('scraper')):
                        # Create instance
                        scraper = obj(self.output_dir)
                        self.scrapers[group_id] = scraper
                        logger.info(f"Loaded scraper for {group_id}")
                        break
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load scraper for {group_id}: {e}")
    
    def get_scraper(self, group_id: str) -> BaseScraper:
        """Get scraper by group ID"""
        return self.scrapers.get(group_id)
    
    def get_all_scrapers(self) -> List[BaseScraper]:
        """Get all registered scrapers"""
        return list(self.scrapers.values())
