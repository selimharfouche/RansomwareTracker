# core/browser.py
import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config.settings import BROWSER_SETTINGS, TOR_SETTINGS, WAIT_TIMES

logger = logging.getLogger(__name__)

class TorBrowser:
    """Manages Tor-enabled browser sessions"""
    
    def __init__(self, headless=BROWSER_SETTINGS["headless"]):
        self.driver = None
        self.headless = headless
        
    def __enter__(self):
        """Setup browser when entering context"""
        self.driver = self._setup_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up browser when exiting context"""
        if self.driver:
            self.driver.quit()
            
    def _setup_browser(self):
        """Configure Firefox to use Tor"""
        options = Options()
        
        # Configure Tor proxy
        options.set_preference('network.proxy.type', 1)
        options.set_preference('network.proxy.socks', TOR_SETTINGS["socks_host"])
        options.set_preference('network.proxy.socks_port', TOR_SETTINGS["socks_port"])
        options.set_preference('network.proxy.socks_remote_dns', True)
        
        # Browser fingerprinting countermeasures
        options.set_preference('general.useragent.override', BROWSER_SETTINGS["user_agent"])
        options.set_preference('javascript.enabled', True)
        options.set_preference('dom.webnotifications.enabled', False)
        options.set_preference('app.shield.optoutstudies.enabled', False)
        options.set_preference('dom.popup_allowed_events', '')
        
        # Headless mode if configured
        if self.headless:
            options.add_argument("-headless")
            
        # Create the driver
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(BROWSER_SETTINGS["page_load_timeout"])
        
        return driver
        
    def test_tor_connection(self):
        """Verify the browser can connect through Tor"""
        if not self.driver:
            return False
            
        try:
            self.driver.get('https://check.torproject.org/')
            time.sleep(3)  # Give the page time to load
            
            if "Congratulations" in self.driver.page_source:
                logger.info("Successfully connected to Tor!")
                return True
            else:
                logger.warning("Connected to the site, but not through Tor")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            return False
            
    def fetch_page(self, url, wait_time=WAIT_TIMES["initial_page_load"]):
        """Navigate to URL and return page content, handling anti-bot measures"""
        if not self.driver:
            return None
            
        try:
            logger.info(f"Navigating to {url}...")
            self.driver.get(url)
            
            # Wait for anti-bot measures
            logger.info(f"Waiting {wait_time} seconds for anti-bot measures...")
            time.sleep(wait_time)
            
            # Return the page source after waiting
            return self.driver.page_source
            
        except WebDriverException as e:
            logger.error(f"Browser error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error visiting {url}: {e}")
            return None
            
    def random_delay(self):
        """Sleep for a random interval to avoid detection"""
        min_delay, max_delay = WAIT_TIMES["between_requests"]
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        return delay
