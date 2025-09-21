#!/usr/bin/env python3
"""
Fast Excel Scraper CLI - Optimized for sub-50 second performance.

Usage:
    python -m excel_scraper.scripts.scrape [OPTIONS] URL

Examples:
    python -m excel_scraper.scripts.scrape https://polishventure.com/shop/ --speed-test
    python -m excel_scraper.scripts.scrape https://polishventure.com/shop/ --max-time 45
"""

import asyncio
import sys
import time
import argparse
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from excel_scraper import FastExcelScraper, Config
from excel_scraper.utils import is_valid_url, format_duration


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Fast Excel Scraper - High-performance web scraper for Excel export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://polishventure.com/shop/
  %(prog)s https://example.com/products --max-products 100 --max-pages 5
  %(prog)s https://example.com --config config/custom.json
        """
    )
    
    parser.add_argument(
        'url',
        help='Website URL to scrape'
    )
    
    parser.add_argument(
        '--max-products',
        type=int,
        default=100,
        help='Maximum number of products to scrape (default: 100)'
    )
    
    parser.add_argument(
        '--max-pages', 
        type=int,
        default=None,
        help='Maximum number of pages to scrape (default: auto-calculated)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory for Excel files (default: output)'
    )
    
    parser.add_argument(
        '--filename',
        type=str,
        help='Custom filename for Excel file (default: auto-generated)'
    )
    
    parser.add_argument(
        '--concurrent-requests',
        type=int,
        default=8,
        help='Number of concurrent requests (default: 8)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.3,
        help='Delay between requests in seconds (default: 0.3)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=20,
        help='Request timeout in seconds (default: 20)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--full-catalog',
        action='store_true',
        help='Scrape entire catalog (ignores --max-products and --max-pages)'
    )
    
    parser.add_argument(
        '--speed-test',
        action='store_true',
        help='Speed test mode: optimized settings for fast scraping'
    )
    
    parser.add_argument(
        '--max-time',
        type=int,
        help='Maximum scraping time in seconds (for testing)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Excel Scraper 1.0.0'
    )
    
    return parser


def print_banner():
    """Print application banner."""
    print("🚀 EXCEL SCRAPER v1.0.0")
    print("=" * 60)
    print("High-performance async web scraper for Excel export")
    print("Features: Concurrent scraping, Excel formatting, Multi-currency")
    print("=" * 60)
    print()


async def run_scraper(args) -> int:
    """
    Run the scraper with given arguments.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    
    # Validate URL
    if not is_valid_url(args.url):
        print(f"❌ Error: Invalid URL '{args.url}'")
        return 1
    
    # Calculate max pages if not specified
    max_pages = args.max_pages
    if max_pages is None:
        max_pages = max(1, args.max_products // 20)  # Assume ~20 products per page
    
    # Create configuration
    config = Config(args.config) if args.config else Config()
    
    # Override config with command line arguments
    config.set('max_concurrent_requests', args.concurrent_requests)
    config.set('request_delay', args.delay) 
    config.set('timeout', args.timeout)
    config.set('max_pages', max_pages)
    config.set('output_dir', args.output_dir)
    
    # Speed test mode optimizations
    if args.speed_test:
        config.set('max_concurrent_requests', 40)
        config.set('max_concurrent_products', 35)
        config.set('request_delay', 0.05)
        config.set('product_request_delay', 0.02)
        config.set('timeout', 10)
        config.set('extract_images', False)  # Skip images for speed
        config.set('extract_descriptions', False)  # Skip descriptions for speed
        print("🚀 SPEED TEST MODE ENABLED - Ultra-fast settings activated!")
    
    if args.max_time:
        config.set('max_scraping_time', args.max_time)
    
    if args.verbose:
        config.set('log_level', 'DEBUG')
    
    # Create scraper
    scraper = FastExcelScraper(config)
    
    # Print configuration
    print(f"🎯 Target URL: {args.url}")
    print(f"📊 Max products: {args.max_products}")
    print(f"📄 Max pages: {max_pages}")
    print(f"⚡ Concurrent requests: {args.concurrent_requests}")
    print(f"⏱️ Request delay: {args.delay}s")
    print(f"📁 Output directory: {args.output_dir}")
    print()
    
    try:
        start_time = time.time()
        print("🔄 Starting scraping...")
        
        # Scrape website - full catalog or limited
        if args.full_catalog:
            print("🌟 FULL CATALOG MODE - Scraping entire website...")
            products = await scraper.scrape_full_catalog(args.url)
        else:
            products = await scraper.scrape_website_async(args.url)
        
        if products:
            print(f"✅ Found {len(products)} products!")
            print("📝 Saving to Excel...")
            
            # Save to Excel
            output_file = scraper.save_to_excel(
                products, 
                filename=args.filename,
                output_dir=args.output_dir
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n🎉 SUCCESS!")
            print("=" * 50)
            print(f"📊 Products scraped: {len(products)}")
            print(f"⏱️ Duration: {format_duration(duration)}")
            print(f"⚡ Rate: {len(products) / duration:.1f} products/second")
            print(f"📁 Excel file: {output_file}")
            print("=" * 50)
            
            return 0
        else:
            print("❌ No products found!")
            print("\n💡 Troubleshooting tips:")
            print("   • Check if the website is accessible")
            print("   • Verify the URL is correct")
            print("   • Try increasing timeout with --timeout")
            print("   • Some sites require JavaScript (not supported)")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    finally:
        await scraper.close_session()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    print_banner()
    
    try:
        exit_code = asyncio.run(run_scraper(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted")
        sys.exit(1)


if __name__ == "__main__":
    main()