import os

# Use the exact relative path
OUTPUT_DIR = "website/public/data"

# Browser settings
BROWSER_SETTINGS = {
    "headless": False,  # Set to True for production
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "page_load_timeout": 120,
}

# Tor settings
TOR_SETTINGS = {
    "socks_host": "127.0.0.1",
    "socks_port": 9050,
    "control_port": 9051,
}

# Wait times
WAIT_TIMES = {
    "initial_page_load": 15,  # Seconds to wait for anti-bot measures
    "between_requests": (3, 8),  # Random range (min, max) in seconds
}

# Scraper settings
SCRAPER_SETTINGS = {
    "max_victims_per_group": 5,  # Number of most recent victims to process
    "max_retries": 3,            # Maximum retry attempts per mirror
}

# MISP export settings
MISP_SETTINGS = {
    "distribution": 0,  # Your organization only
    "threat_level": 2,  # Medium
    "analysis": 2,      # Complete
    "tags": [
        {"name": "tlp:amber"},
        {"name": "ransomware"}
    ]
}

# Enabled ransomware groups
ENABLED_GROUPS = [
    "lockbit",
    # Add other groups as they're implemented
]

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "ransom_intel.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}