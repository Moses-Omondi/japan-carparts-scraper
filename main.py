#!/usr/bin/env python3
"""
Main execution script for the Japanese OEM Car Parts Scraper.
This script orchestrates the scraping, currency conversion, and PDF generation process.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper import CarPartsScraper, YahooAuctionsScraper, UpgarageeScraper
from currency_converter import CurrencyConverter
from pdf_generator import PDFGenerator


def setup_logging(log_level: str = 'INFO'):
    """Set up logging configuration."""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    log_filename = os.path.join(log_dir, f"main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        'target_urls': [
            # Example URLs - these would need to be replaced with real Japanese car parts sites
            'https://www.upgarage.com/search',
            'https://auctions.yahoo.co.jp/category/list/2084007888/',
        ],
        'request_delay': 2,
        'max_parts_per_site': 50,
        'output_formats': ['pdf', 'compact_pdf', 'csv'],
        'cache_duration_hours': 1,
        'fallback_exchange_rate': 0.0067,
        'pdf_settings': {
            'include_images': True,
            'parts_per_page': 3
        },
        'scraper_settings': {
            'timeout': 30,
            'max_retries': 3,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # Merge with defaults
                default_config.update(file_config)
        except Exception as e:
            logging.warning(f"Could not load config file {config_path}: {e}")
            logging.info("Using default configuration")
    
    return default_config


def scrape_parts_data(config: Dict[str, Any], logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Scrape car parts data from configured websites.
    
    Args:
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        List of scraped parts data
    """
    logger.info("Starting web scraping process...")
    
    # Initialize scraper
    scraper = CarPartsScraper(config)
    
    # Get target URLs
    target_urls = config.get('target_urls', [])
    if not target_urls:
        logger.warning("No target URLs configured. Using sample data for demonstration.")
        return get_sample_data()
    
    try:
        # Scrape all sites
        all_parts_data = scraper.scrape_multiple_sites(target_urls)
        
        # Save raw scraped data
        scraper.save_data_to_file('raw_scraped_data.json')
        
        logger.info(f"Successfully scraped {len(all_parts_data)} parts")
        return all_parts_data
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        logger.info("Falling back to sample data for demonstration")
        return get_sample_data()


def convert_currencies(parts_data: List[Dict[str, Any]], config: Dict[str, Any], 
                      logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Convert JPY prices to USD for all parts.
    
    Args:
        parts_data: List of parts data with JPY prices
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        List of parts data with USD prices added
    """
    logger.info("Starting currency conversion...")
    
    # Initialize currency converter
    converter = CurrencyConverter(config)
    
    try:
        # Convert all parts
        converted_parts = converter.convert_parts_list(parts_data)
        
        # Log exchange rate info
        rate_info = converter.get_rate_info()
        logger.info(f"Using exchange rate: {rate_info['current_rate']}")
        
        return converted_parts
        
    except Exception as e:
        logger.error(f"Error during currency conversion: {e}")
        return parts_data  # Return original data if conversion fails


def generate_reports(parts_data: List[Dict[str, Any]], config: Dict[str, Any], 
                    logger: logging.Logger) -> Dict[str, Optional[str]]:
    """
    Generate PDF and CSV reports from parts data.
    
    Args:
        parts_data: List of parts data
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        Dictionary with paths to generated files
    """
    logger.info("Starting report generation...")
    
    # Initialize PDF generator
    pdf_generator = PDFGenerator(config)
    
    generated_files = {}
    output_formats = config.get('output_formats', ['pdf'])
    
    try:
        # Generate different output formats based on config
        if 'pdf' in output_formats:
            pdf_path = pdf_generator.generate_pdf(parts_data)
            generated_files['pdf'] = pdf_path
            logger.info(f"Generated PDF report: {pdf_path}")
        
        if 'compact_pdf' in output_formats:
            compact_pdf_path = pdf_generator.generate_compact_pdf(parts_data)
            generated_files['compact_pdf'] = compact_pdf_path
            logger.info(f"Generated compact PDF report: {compact_pdf_path}")
        
        if 'csv' in output_formats:
            csv_path = pdf_generator.generate_csv_export(parts_data)
            generated_files['csv'] = csv_path
            logger.info(f"Generated CSV export: {csv_path}")
        
        return generated_files
        
    except Exception as e:
        logger.error(f"Error during report generation: {e}")
        return {}


def get_sample_data() -> List[Dict[str, Any]]:
    """Return sample data for testing/demonstration purposes."""
    return [
        {
            'name': 'Toyota Supra A90 Front Bumper (OEM)',
            'part_number': 'TS-FB-A90-001',
            'price_jpy': 89000,
            'description': 'Original front bumper for Toyota Supra A90 (2019-2024)',
            'source_url': 'https://example-toyota-parts.jp/supra-bumper',
            'scraped_at': datetime.now().timestamp()
        },
        {
            'name': 'Nissan R34 GT-R Rear Wing (Nismo)',
            'part_number': 'N-RW-R34-NIS',
            'price_jpy': 156000,
            'description': 'Nismo rear wing for Nissan Skyline R34 GT-R',
            'source_url': 'https://example-nissan-parts.jp/gtr-wing',
            'scraped_at': datetime.now().timestamp()
        },
        {
            'name': 'Honda NSX NA1 Brake Rotors (Brembo)',
            'part_number': 'H-BR-NA1-BRE',
            'price_jpy': 78000,
            'description': 'Brembo brake rotors for Honda NSX NA1 (1990-1997)',
            'source_url': 'https://example-honda-parts.jp/nsx-brakes',
            'scraped_at': datetime.now().timestamp()
        },
        {
            'name': 'Mazda RX-7 FD3S Turbo Upgrade Kit',
            'part_number': 'M-TU-FD3S-001',
            'price_jpy': 234000,
            'description': 'Complete turbo upgrade kit for Mazda RX-7 FD3S',
            'source_url': 'https://example-mazda-parts.jp/rx7-turbo',
            'scraped_at': datetime.now().timestamp()
        },
        {
            'name': 'Subaru WRX STI EJ25 Engine Block',
            'part_number': 'S-EB-EJ25-STI',
            'price_jpy': 445000,
            'description': 'Rebuilt EJ25 engine block for Subaru WRX STI',
            'source_url': 'https://example-subaru-parts.jp/sti-engine',
            'scraped_at': datetime.now().timestamp()
        }
    ]


def print_summary(parts_data: List[Dict[str, Any]], generated_files: Dict[str, str], 
                 logger: logging.Logger):
    """Print a summary of the scraping results."""
    print("\n" + "="*80)
    print("JAPANESE OEM CAR PARTS SCRAPER - EXECUTION SUMMARY")
    print("="*80)
    
    print(f"Total parts processed: {len(parts_data)}")
    
    if parts_data:
        # Price statistics
        jpy_prices = [p.get('price_jpy', 0) for p in parts_data if p.get('price_jpy')]
        usd_prices = [p.get('price_usd', 0) for p in parts_data if p.get('price_usd')]
        
        if jpy_prices:
            print(f"Price range (JPY): ¥{min(jpy_prices):,.0f} - ¥{max(jpy_prices):,.0f}")
            print(f"Average price (JPY): ¥{sum(jpy_prices)/len(jpy_prices):,.0f}")
        
        if usd_prices:
            print(f"Price range (USD): ${min(usd_prices):.2f} - ${max(usd_prices):.2f}")
            print(f"Average price (USD): ${sum(usd_prices)/len(usd_prices):.2f}")
    
    print("\nGenerated files:")
    for format_name, file_path in generated_files.items():
        if file_path:
            print(f"  {format_name.upper()}: {file_path}")
    
    print("\nExecution completed successfully!")
    print("="*80)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Japanese OEM Car Parts Scraper')
    parser.add_argument('--config', '-c', default='config.json', 
                       help='Path to configuration file (default: config.json)')
    parser.add_argument('--log-level', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--sample-only', '-s', action='store_true',
                       help='Skip scraping and use sample data only')
    parser.add_argument('--no-convert', '-n', action='store_true',
                       help='Skip currency conversion')
    parser.add_argument('--output-dir', '-o', default='outputs',
                       help='Output directory for generated files')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    logger.info("Starting Japanese OEM Car Parts Scraper")
    
    try:
        # Load configuration
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
        
        # Step 1: Scrape parts data
        if args.sample_only:
            logger.info("Using sample data (--sample-only flag)")
            parts_data = get_sample_data()
        else:
            parts_data = scrape_parts_data(config, logger)
        
        if not parts_data:
            logger.error("No parts data available. Exiting.")
            return 1
        
        # Step 2: Convert currencies
        if not args.no_convert:
            parts_data = convert_currencies(parts_data, config, logger)
        else:
            logger.info("Skipping currency conversion (--no-convert flag)")
        
        # Step 3: Generate reports
        generated_files = generate_reports(parts_data, config, logger)
        
        # Step 4: Print summary
        print_summary(parts_data, generated_files, logger)
        
        logger.info("Scraping process completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
