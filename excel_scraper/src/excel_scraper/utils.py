"""
Utility functions for the Excel Scraper.
"""

import logging
import re
import os
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    
    Returns:
        Configured logger
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger("excel_scraper")


def extract_price_from_text(price_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract price information from text.
    
    Args:
        price_text: Text containing price information
    
    Returns:
        Dictionary with price information or None
    """
    if not price_text:
        return None
    
    # Common price patterns
    patterns = {
        'kes': r'KES?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        'usd': r'USD?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        'jpy': r'¥\s*(\d{1,3}(?:,\d{3})*)',
        'eur': r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        'gbp': r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    }
    
    for currency, pattern in patterns.items():
        match = re.search(pattern, price_text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                return {
                    f'price_{currency}': price,
                    'original_currency': currency.upper(),
                    'raw_price_text': price_text.strip()
                }
            except ValueError:
                continue
    
    return None


def generate_filename(prefix: str = "scraped_products", 
                     suffix: str = "xlsx", 
                     timestamp_format: str = "%Y%m%d_%H%M%S") -> str:
    """
    Generate filename with timestamp.
    
    Args:
        prefix: File prefix
        suffix: File suffix/extension
        timestamp_format: Timestamp format
    
    Returns:
        Generated filename
    """
    timestamp = datetime.now().strftime(timestamp_format)
    return f"{prefix}_{timestamp}.{suffix}"


def ensure_directory_exists(directory: str) -> None:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def clean_product_name(name: str) -> str:
    """
    Clean and normalize product name.
    
    Args:
        name: Raw product name
    
    Returns:
        Cleaned product name
    """
    if not name:
        return ""
    
    # Remove common unwanted text
    unwanted = ['BARGAIN PRICE', 'Used', 'NEW', 'SALE']
    for unwanted_text in unwanted:
        name = name.replace(unwanted_text, '').strip()
    
    # Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Limit length
    return name[:200].strip()


def is_valid_url(url: str) -> bool:
    """
    Check if URL is valid.
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid URL
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"