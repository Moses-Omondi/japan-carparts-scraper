"""
Excel Scraper - Fast async web scraper for Excel export.

A professional, high-performance web scraper optimized for scraping 
e-commerce websites and exporting data to Excel format.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "Fast async web scraper for Excel export"

from .scraper import FastExcelScraper
from .config import Config
from .utils import setup_logging

__all__ = [
    "FastExcelScraper",
    "Config", 
    "setup_logging"
]