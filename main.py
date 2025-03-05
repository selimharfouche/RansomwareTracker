#!/usr/bin/env python
import os
import json
import logging
import logging.config
import argparse
import time
import datetime
from typing import Dict, List, Any

from config.settings import OUTPUT_DIR, LOGGING, ENABLED_GROUPS
from core.browser import TorBrowser
from core.database import Database
from core.exporters import MISPExporter, OpenCTIExporter
from models.ioc import IOC
from scrapers.registry import ScraperRegistry

# Configure logging
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

def run_single_scraper(scraper_id: str, browser: TorBrowser, db: Database, incremental: bool = True) -> Dict:
    """Run a single scraper by ID"""
    registry = ScraperRegistry(OUTPUT_DIR)
    scraper = registry.get_scraper(scraper_id)
    
    if not scraper:
        logger.error(f"Scraper for {scraper_id} not found")
        return {"success": False, "error": f"Scraper {scraper_id} not found"}
    
    logger.info(f"Running scraper for {scraper_id}")
    result = scraper.run(browser, incremental=incremental)
    
    # Save result
    db.save_json(f"{scraper_id}_latest.json", result)
    
    return result

def run_all_scrapers(browser: TorBrowser, db: Database, incremental: bool = True) -> Dict:
    """Run all enabled scrapers"""
    registry = ScraperRegistry(OUTPUT_DIR)
    scrapers = registry.get_all_scrapers()
    
    results = {}
    for scraper in scrapers:
        group_id = scraper.group_id
        logger.info(f"Running scraper for {group_id}")
        
        try:
            result = scraper.run(browser, incremental=incremental)
            results[group_id] = result
            
            # Save individual result
            db.save_json(f"{group_id}_latest.json", result)
        except Exception as e:
            logger.error(f"Error running scraper for {group_id}: {e}")
            results[group_id] = {"success": False, "error": str(e)}
    
    # Save combined results
    summary = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "groups_scanned": len(scrapers),
        "successful_scans": sum(1 for r in results.values() if r.get("success", False)),
        "new_victims": sum(len(r.get("new_victims", [])) for r in results.values() if r.get("success", False)),
        "updated_victims": sum(len(r.get("updated_victims", [])) for r in results.values() if r.get("success", False)),
        "groups": {k: {"success": v.get("success", False), 
                      "victims_found": len(v.get("victims", [])),
                      "new_victims": len(v.get("new_victims", [])),
                      "updated_victims": len(v.get("updated_victims", []))} 
                 for k, v in results.items()},
        "incremental": incremental
    }
    
    db.save_json("scan_summary.json", summary)
    
    return results

def extract_and_export_iocs(db: Database) -> None:
    """Extract IOCs from all victim data and export to MISP and OpenCTI"""
    # Load all victim data
    all_victims = []
    
    for group_id in ENABLED_GROUPS:
        history_file = f"{group_id}_history.json"
        victims = db.load_json(history_file, default=[])
        all_victims.extend(victims)
    
    # Extract IOCs
    ioc = IOC()
    for victim in all_victims:
        if victim.get('description_full'):
            ioc.extract_from_text(victim['description_full'])
        if victim.get('description_preview'):
            ioc.extract_from_text(victim['description_preview'])
    
    # Save IOCs
    db.save_json("all_iocs.json", ioc.to_dict())
    
    # Export to MISP
    misp_exporter = MISPExporter()
    misp_feed = misp_exporter.generate_feed(all_victims)
    db.save_json("misp_feed.json", misp_feed)
    
    # Export to OpenCTI
    opencti_exporter = OpenCTIExporter()
    opencti_feed = opencti_exporter.generate_feed(all_victims)
    db.save_json("opencti_feed.json", opencti_feed)
    
    logger.info(f"Generated feeds for {len(all_victims)} victims across {len(ENABLED_GROUPS)} ransomware groups")

def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Ransomware Intelligence Collection System")
    parser.add_argument('-g', '--group', help='Specific ransomware group to track')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', help='Output directory path', default=OUTPUT_DIR)
    parser.add_argument('--full', action='store_true', help='Process all victims, not just new ones')
    args = parser.parse_args()
    
    # Determine incremental mode
    incremental = not args.full
    
    # Use command line output path if provided
    output_dir = args.output
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Using output directory: {output_dir}")
    logger.info(f"Running in {'incremental' if incremental else 'full'} mode")
    
    db = Database(output_dir)
    
    with TorBrowser(headless=args.headless) as browser:
        # Check Tor connection
        if not browser.test_tor_connection():
            logger.error("Cannot connect to Tor. Make sure Tor is running on port 9050.")
            return
        
        # Run scrapers
        if args.group:
            result = run_single_scraper(args.group, browser, db, incremental=incremental)
            status = 'Success' if result.get('success') else 'Failed'
            logger.info(f"Result for {args.group}: {status}")
            if result.get('success'):
                logger.info(f"Found {len(result.get('victims', []))} victims, {len(result.get('new_victims', []))} new, {len(result.get('updated_victims', []))} updated")
        else:
            results = run_all_scrapers(browser, db, incremental=incremental)
            logger.info(f"Ran {len(results)} scrapers")
    
    # Extract and export IOCs
    extract_and_export_iocs(db)
    
    logger.info("Done")

if __name__ == "__main__":
    main()