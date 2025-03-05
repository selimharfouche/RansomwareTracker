import time
import json
import os
import logging
import datetime
import random
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configuration
LOCKBIT_MIRRORS = [
    "lockbit3753ekiocyo5epmpy6klmejchjtzddoekjlnt6mu3qh4de2id.onion",
    "lockbit3g3ohd3katajf6zaehxz4h4cnhmz5t735zpltywhwpc6oy3id.onion",
    "lockbit3olp7oetlc4tl5zydnoluphh7fvdt5oa6arcp2757r7xkutid.onion",
    "lockbit435xk3ki62yun7z5nhwz6jyjdp2c64j5vge536if2eny3gtid.onion",
    "lockbit4lahhluquhoka3t4spqym2m3dhe66d6lr337glmnlgg2nndad.onion",
    "lockbit6knrauo3qafoksvl742vieqbujxw7rd6ofzdtapjb4rrawqad.onion",
    "lockbit7ouvrsdgtojeoj5hvu6bljqtghitekwpdy3b6y62ixtsu5jqd.onion"
]
OUTPUT_DIR = "website/public/data"
OUTPUT_FILE = "lockbit_tracker.json"
HISTORY_FILE = "lockbit_history.json"
MIRRORS_FILE = "working_mirrors.json"
WAIT_TIME = 15  # Increased wait time to handle anti-bot measures

# Ensure our directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_tor_browser():
    """Configure Firefox to use Tor"""
    options = Options()
    options.set_preference('network.proxy.type', 1)
    options.set_preference('network.proxy.socks', '127.0.0.1')
    options.set_preference('network.proxy.socks_port', 9050)
    options.set_preference('network.proxy.socks_remote_dns', True)
    
    # Additional settings to make us look more like a normal browser
    options.set_preference('general.useragent.override', 'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0')
    options.set_preference('javascript.enabled', True)
    options.set_preference('dom.webnotifications.enabled', False)
    options.set_preference('app.shield.optoutstudies.enabled', False)
    
    # Prevent popup notifications that might interfere with scraping
    options.set_preference('dom.popup_allowed_events', '')
    
    # Uncomment the line below for headless mode (good for production)
    # options.add_argument("-headless")
    
    # Create the driver
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(120)  # Longer timeout for onion sites
    
    return driver

def test_tor_connection(driver):
    """Test if we can connect through Tor"""
    try:
        driver.get('https://check.torproject.org/')
        time.sleep(3)  # Give page time to load
        if "Congratulations" in driver.page_source:
            logger.info("Successfully connected to Tor!")
            return True
        else:
            logger.warning("Connected to the site, but not through Tor")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Tor: {e}")
        return False

def get_working_mirrors():
    """Load previously working mirrors if available"""
    try:
        with open(os.path.join(OUTPUT_DIR, MIRRORS_FILE), 'r') as f:
            mirrors_data = json.load(f)
            # Sort mirrors by success rate
            working_mirrors = sorted(
                mirrors_data.items(), 
                key=lambda x: x[1]['success_rate'], 
                reverse=True
            )
            return [mirror for mirror, _ in working_mirrors]
    except (FileNotFoundError, json.JSONDecodeError):
        # If no data is available, return the default list
        return LOCKBIT_MIRRORS

def update_mirror_stats(mirror, success=True):
    """Update statistics about mirror reliability"""
    try:
        with open(os.path.join(OUTPUT_DIR, MIRRORS_FILE), 'r') as f:
            mirrors_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        mirrors_data = {m: {"success": 0, "failure": 0, "success_rate": 0.0} for m in LOCKBIT_MIRRORS}
    
    # Ensure the mirror is in our data
    if mirror not in mirrors_data:
        mirrors_data[mirror] = {"success": 0, "failure": 0, "success_rate": 0.0}
    
    # Update stats
    if success:
        mirrors_data[mirror]["success"] += 1
    else:
        mirrors_data[mirror]["failure"] += 1
    
    # Calculate success rate
    total = mirrors_data[mirror]["success"] + mirrors_data[mirror]["failure"]
    if total > 0:
        mirrors_data[mirror]["success_rate"] = mirrors_data[mirror]["success"] / total
    
    # Add timestamp
    mirrors_data[mirror]["last_check"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Save updated data
    with open(os.path.join(OUTPUT_DIR, MIRRORS_FILE), 'w') as f:
        json.dump(mirrors_data, f, indent=4)

def browse_with_selenium(driver, url, wait_time=WAIT_TIME):
    """Browse to a URL with Selenium, handling waiting periods and potential anti-bot measures"""
    try:
        logger.info(f"Navigating to {url}...")
        driver.get(url)
        
        # First wait for initial page load
        logger.info(f"Waiting {wait_time} seconds for anti-bot measures...")
        time.sleep(wait_time)  # This wait helps with anti-bot measures
        
        # Check if the page has content we expect
        if "LockBit" not in driver.page_source:
            logger.warning("LockBit text not found in page, might not be the correct site")
            # Still proceed - maybe the structure changed
        
        # Return the page source after waiting
        return driver.page_source
    
    except WebDriverException as e:
        logger.error(f"Browser error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error visiting {url}: {e}")
        return None

def parse_victim_block(block):
    """Extract data from a victim block on the LockBit site"""
    victim = {}
    
    # Extract domain name
    domain_elem = block.select_one('.post-title')
    if domain_elem:
        victim['domain'] = domain_elem.text.strip()
    
    # Extract status (published or countdown)
    status_elem = block.select_one('.post-timer-end')
    if status_elem:
        victim['status'] = status_elem.text.strip().upper()
    
    # Extract description snippet
    desc_elem = block.select_one('.post-block-text')
    if desc_elem:
        # Get a preview of the description
        victim['description_preview'] = desc_elem.text.strip()[:200] + "..." if len(desc_elem.text.strip()) > 200 else desc_elem.text.strip()
    
    # Extract update timestamp - try multiple possible selectors
    time_elem = block.select_one('.updated-post-date span')
    if not time_elem:
        time_elem = block.select_one('.views .updated-post-date')
    
    if time_elem:
        # Clean up the timestamp text
        timestamp_text = time_elem.text.strip()
        # Remove any non-timestamp text
        if "Updated:" in timestamp_text:
            timestamp_text = timestamp_text.split("Updated:")[1].strip()
        victim['updated'] = timestamp_text
    
    # Extract view count - try multiple possible selectors
    views_elem = block.select_one('div[style*="opacity"] span[style*="font-weight: bold"]')
    if not views_elem:
        views_elem = block.select_one('.views span[style*="font-weight: bold"]')
    if not views_elem:
        views_elem = block.select_one('.views span[style*="font-size: 12px"]')
    
    if views_elem:
        try:
            # Clean up and extract just the number
            views_text = views_elem.text.strip()
            # Extract digits only
            import re
            digits = re.findall(r'\d+', views_text)
            if digits:
                victim['views'] = int(digits[0])
        except ValueError:
            victim['views'] = 0
    
    # Extract link to detailed page
    link_elem = block.get('href')
    if link_elem:
        victim['detail_link'] = link_elem
    
    return victim

def scrape_lockbit_main_page(driver):
    """Scrape the main LockBit leak site to get victim information by trying multiple mirrors"""
    # Get previously working mirrors
    mirrors = get_working_mirrors()
    logger.info(f"Trying {len(mirrors)} potential mirrors")
    
    # Try each mirror
    for mirror in mirrors:
        try:
            # Use just the base mirror domain - the main page is the leaked data
            url = f"http://{mirror}"
            logger.info(f"Trying LockBit mirror: {mirror}")
            
            html_content = browse_with_selenium(driver, url)
            
            if not html_content:
                logger.warning(f"No content received from {mirror}")
                update_mirror_stats(mirror, success=False)
                continue
                
            # Check if we got actual content (not a redirect or error page)
            if "LockBit" not in html_content:
                logger.warning(f"Mirror {mirror} returned non-LockBit content")
                update_mirror_stats(mirror, success=False)
                continue
                
            logger.info(f"Successfully connected to {mirror}")
            update_mirror_stats(mirror, success=True)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all victim entries
            victim_entries = []
            for entry in soup.select('a.post-block'):
                victim = parse_victim_block(entry)
                if victim and 'domain' in victim:
                    victim_entries.append(victim)
                    logger.info(f"Found victim: {victim['domain']}")
            
            if victim_entries:
                # The first 5 victims on the page are the most recent
                logger.info(f"Found {len(victim_entries)} total victims")
                return victim_entries[:5], mirror  # Return the 5 most recent victims and working mirror
            else:
                logger.warning(f"No victim entries found on {mirror}")
                
        except Exception as e:
            logger.warning(f"Mirror {mirror} failed: {e}")
            update_mirror_stats(mirror, success=False)
    
    logger.error("All LockBit mirrors failed")
    return None, None

def parse_victim_details(soup):
    """Parse victim details from the detail page with support for multiple formats"""
    details = {}
    
    # Try to detect which format we're dealing with
    is_format_1 = soup.select_one('.post-company-content .desc') is not None
    is_format_2 = soup.select_one('.post-wrapper') is not None
    
    # Extract full description
    desc_elem = None
    if is_format_1:
        desc_elem = soup.select_one('.post-company-content .desc')
    elif is_format_2:
        desc_elem = soup.select_one('.post-company-content .desc')
    
    if desc_elem:
        details['full_description'] = desc_elem.text.strip()
        
        # Try to extract data volume if mentioned
        if "data volume:" in details['full_description'].lower():
            for line in details['full_description'].split('\n'):
                if "data volume:" in line.lower():
                    details['data_size'] = line.split("data volume:")[1].strip()
        
        # Try to extract contact information
        contact_info = {}
        for line in details['full_description'].split('\n'):
            if "e-mail:" in line.lower() or "email:" in line.lower():
                email_parts = line.split(":")
                if len(email_parts) > 1:
                    contact_info['email'] = email_parts[1].strip()
            elif "phone:" in line.lower():
                phone_parts = line.split(":")
                if len(phone_parts) > 1:
                    contact_info['phone'] = phone_parts[1].strip()
            elif "headquarters:" in line.lower() or "address:" in line.lower():
                address_parts = line.split(":")
                if len(address_parts) > 1:
                    contact_info['address'] = address_parts[1].strip()
        
        if contact_info:
            details['contact_info'] = contact_info
    
    # Extract deadline if present
    deadline_elem = soup.select_one('.post-banner-p')
    if deadline_elem and "Deadline:" in deadline_elem.text:
        details['deadline'] = deadline_elem.text.replace("Deadline:", "").strip()
    
    # Extract uploaded date - try both formats
    upload_elem = soup.select_one('.uploaded-date-utc')
    if upload_elem:
        details['uploaded'] = upload_elem.text.strip()
    
    # Extract updated date if available
    update_elem = soup.select_one('.updated-date-utc')
    if update_elem:
        details['last_updated'] = update_elem.text.strip()
    
    return details

def get_victim_details(driver, detail_url, working_mirror):
    """Get detailed information about a victim from their specific page"""
    try:
        # Strip leading slash if present
        if detail_url.startswith('/'):
            detail_url = detail_url[1:]
        
        url = f"http://{working_mirror}/{detail_url}"
        html_content = browse_with_selenium(driver, url)
        
        if not html_content:
            logger.error(f"Could not fetch victim detail page: {detail_url}")
            return {}
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Use the more robust parsing function
        details = parse_victim_details(soup)
        
        return details
        
    except Exception as e:
        logger.error(f"Error getting victim details: {e}")
        return {}

def update_victim_database(victims, history_file):
    """Update the victim database with new information and track changes"""
    # Load existing history if available
    try:
        with open(os.path.join(OUTPUT_DIR, history_file), 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    
    # Create a dictionary of existing victims by domain for easy lookup
    existing_victims = {victim['domain']: victim for victim in history if 'domain' in victim}
    
    # Track changes for reporting
    new_victims = []
    updated_victims = []
    
    # Process current victims
    for victim in victims:
        domain = victim.get('domain')
        if not domain:
            continue
            
        if domain not in existing_victims:
            # This is a new victim
            victim['first_seen'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            history.append(victim)
            new_victims.append(domain)
            logger.info(f"New victim added: {domain}")
        else:
            # This is an existing victim, check for updates
            existing = existing_victims[domain]
            
            # Check if status changed
            if victim.get('status') != existing.get('status'):
                existing['status_history'] = existing.get('status_history', [])
                existing['status_history'].append({
                    'status': existing.get('status'),
                    'timestamp': existing.get('updated')
                })
                existing['status'] = victim.get('status')
                updated_victims.append(domain)
                logger.info(f"Status updated for {domain}: {victim.get('status')}")
            
            # Update other fields
            for key, value in victim.items():
                if key != 'first_seen' and key != 'status_history':
                    existing[key] = value
    
    # Save the updated history
    with open(os.path.join(OUTPUT_DIR, history_file), 'w') as f:
        json.dump(history, f, indent=4)
    
    return history, new_victims, updated_victims

def generate_stats(victims):
    """Generate statistics about the victims"""
    stats = {
        'total_victims': len(victims),
        'published_count': sum(1 for v in victims if v.get('status') == 'PUBLISHED'),
        'countdown_count': sum(1 for v in victims if v.get('status') and v.get('status') != 'PUBLISHED'),
        'domains_by_tld': {},
        'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    # Count domains by TLD
    for victim in victims:
        domain = victim.get('domain', '')
        if domain:
            tld = domain.split('.')[-1] if '.' in domain else 'unknown'
            stats['domains_by_tld'][tld] = stats['domains_by_tld'].get(tld, 0) + 1
    
    return stats

def extract_iocs_from_victims(victims):
    """Extract potential IOCs from victim data"""
    iocs = {
        'domains': set(),
        'emails': set(),
        'ips': set(),
        'urls': set()
    }
    
    import re
    for victim in victims:
        # Add the victim domain
        if victim.get('domain'):
            iocs['domains'].add(victim.get('domain'))
        
        # Extract from description if available
        if victim.get('full_description'):
            # Look for emails
            desc = victim.get('full_description')
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc)
            for email in emails:
                iocs['emails'].add(email)
            
            # Look for IPs
            ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', desc)
            for ip in ips:
                iocs['ips'].add(ip)
            
            # Look for URLs
            urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*', desc)
            for url in urls:
                iocs['urls'].add(url)
    
    # Convert sets to lists for JSON serialization
    return {k: list(v) for k, v in iocs.items()}

def generate_misp_feed(victims):
    """Generate MISP feed format"""
    events = []
    
    for victim in victims:
        if not victim.get('domain'):
            continue
            
        event = {
            "info": f"LockBit Ransomware Victim: {victim.get('domain')}",
            "threat_level_id": 2,  # Medium
            "analysis": 2,  # Complete
            "distribution": 0,  # Your organization only
            "date": victim.get('first_seen', datetime.datetime.now().strftime("%Y-%m-%d")),
            "Attribute": []
        }
        
        # Add domain as attribute
        event["Attribute"].append({
            "type": "domain",
            "category": "Network activity",
            "to_ids": False,
            "value": victim.get('domain')
        })
        
        # Add description
        if victim.get('description_preview'):
            event["Attribute"].append({
                "type": "text",
                "category": "Other",
                "to_ids": False,
                "value": victim.get('description_preview')
            })
            
        # Add any emails found in contact info
        if victim.get('contact_info', {}).get('email'):
            event["Attribute"].append({
                "type": "email",
                "category": "Payload delivery",
                "to_ids": False,
                "value": victim.get('contact_info').get('email')
            })
        
        # Add tags
        event["Tag"] = [
            {"name": "tlp:amber"},
            {"name": "ransomware"},
            {"name": "lockbit"},
            {"name": "misp-galaxy:ransomware=\"LockBit\""}
        ]
        
        events.append(event)
    
    return {"response": events}

def main():
    """Main function to scrape LockBit and update the database"""
    logger.info(f"Starting LockBit tracker at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    driver = None
    try:
        # Initialize Selenium with Tor
        logger.info("Setting up Tor browser...")
        driver = setup_tor_browser()
        
        # Test Tor connectivity
        if not test_tor_connection(driver):
            logger.error("Cannot connect to Tor. Make sure Tor is running on port 9050.")
            return
        
        # Scrape the LockBit leak site
        logger.info("Scraping LockBit leak site...")
        victims, working_mirror = scrape_lockbit_main_page(driver)
        
        if not victims or not working_mirror:
            logger.error("No victims found or error occurred while scraping")
            return
            
        logger.info(f"Found {len(victims)} recent victims using mirror {working_mirror}")
        
        # These are already the 5 most recent victims
        recent_victims = victims
        
        for victim in recent_victims:
            if 'detail_link' in victim:
                logger.info(f"Getting details for {victim['domain']}...")
                details = get_victim_details(driver, victim['detail_link'], working_mirror)
                victim.update(details)
                # Be nice to the server
                time.sleep(random.uniform(3, 5))
        
        # Update the victim database
        logger.info("Updating victim database...")
        updated_db, new_victims, updated_victims = update_victim_database(victims, HISTORY_FILE)
        
        # Generate statistics
        stats = generate_stats(updated_db)
        
        # Extract IOCs
        iocs = extract_iocs_from_victims(updated_db)
        
        # Create the final output structure
        output = {
            'stats': stats,
            'recent_victims': recent_victims,
            'new_victims': new_victims,
            'updated_victims': updated_victims,
            'iocs': iocs,
            'last_update': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            'working_mirror': working_mirror
        }
        
        # Save the results
        with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), 'w') as f:
            json.dump(output, f, indent=4)
        
        # Generate MISP feed
        with open(os.path.join(OUTPUT_DIR, "misp_feed.json"), 'w') as f:
            json.dump(generate_misp_feed(updated_db), f, indent=4)
            
        logger.info(f"Results saved to {os.path.join(OUTPUT_DIR, OUTPUT_FILE)}")
        logger.info(f"Database updated with {len(new_victims)} new victims and {len(updated_victims)} updates")
        
        # Print recent victims summary
        logger.info("\n--- Recent Victims Summary ---")
        for victim in recent_victims:
            status = victim.get('status', 'UNKNOWN')
            domain = victim.get('domain', 'UNKNOWN')
            updated = victim.get('updated', 'UNKNOWN')
            logger.info(f"Domain: {domain} | Status: {status} | Updated: {updated}")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
    finally:
        # Always close the browser properly
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()