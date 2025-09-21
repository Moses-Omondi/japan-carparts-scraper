import logging
import re
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Setup minimal logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("excel_scraper")


def generate_filename(prefix: str = "scraped_products") -> str:
    """Generate filename with timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefix}_{timestamp}.xlsx"


def ensure_directory_exists(directory: str) -> None:
    """Ensure directory exists."""
    Path(directory).mkdir(parents=True, exist_ok=True)


def clean_product_name(name: str) -> str:
    """Clean product name."""
    if not name:
        return ""
    
    # Remove unwanted text and clean spaces
    for unwanted in ['BARGAIN PRICE', 'Used', 'NEW', 'SALE']:
        name = name.replace(unwanted, '')
    
    return re.sub(r'\s+', ' ', name).strip()[:200]


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    return url.startswith(('http://', 'https://')) and '.' in url


def format_duration(seconds: float) -> str:
    """Format duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"
