#!/usr/bin/env python3
"""
Simple run script for the Fast Excel Scraper.
Usage: python run_fast.py [URL] [MAX_PRODUCTS]
"""

import sys
import asyncio
from fast_excel_scraper import FastExcelScraper
import time

def print_banner():
    print("🚀 FAST EXCEL SCRAPER")
    print("=" * 60)
    print("Optimized for maximum speed and Excel export only")
    print("Features:")
    print("  ✅ Async scraping for maximum speed")
    print("  ✅ Excel export with formatting") 
    print("  ✅ No unnecessary features (PDF, images, etc.)")
    print("  ✅ Concurrent requests")
    print("=" * 60)
    print()

async def run_scraper(url: str, max_products: int = 100):
    """Run the scraper with given parameters."""
    
    # Calculate pages needed (assuming ~20 products per page)
    max_pages = max(1, max_products // 20)
    
    # Optimized configuration
    config = {
        'max_concurrent_requests': 8,  # Concurrent requests
        'request_delay': 0.3,  # Fast delays
        'timeout': 20,
        'max_products_per_page': 50,
        'max_pages': max_pages,
        'retry_attempts': 2
    }
    
    scraper = FastExcelScraper(config)
    
    print(f"🎯 Target: {url}")
    print(f"📊 Max products: {max_products}")
    print(f"📄 Max pages: {max_pages}")
    print(f"⚡ Concurrent requests: {config['max_concurrent_requests']}")
    print(f"⏱️ Request delay: {config['request_delay']}s")
    print()
    
    try:
        start_time = time.time()
        print("🔄 Starting scraping...")
        
        # Scrape website
        products = await scraper.scrape_website_async(url)
        
        if products:
            print(f"✅ Found {len(products)} products!")
            print("📝 Saving to Excel...")
            
            # Save to Excel
            filename = scraper.save_to_excel(products)
            
            end_time = time.time()
            runtime = end_time - start_time
            
            print(f"\n🎉 SUCCESS!")
            print("=" * 40)
            print(f"📊 Products scraped: {len(products)}")
            print(f"⏱️ Runtime: {runtime:.1f} seconds")
            print(f"⚡ Rate: {len(products) / runtime:.1f} products/second")
            print(f"📁 Excel file: {filename}")
            print("=" * 40)
            
            return filename
        else:
            print("❌ No products found!")
            print("💡 Try:")
            print("   - Check if the website is accessible")
            print("   - Verify the URL is correct")
            print("   - Check if the site uses JavaScript (may need different approach)")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    finally:
        await scraper.close_session()

def main():
    """Main function."""
    print_banner()
    
    # Parse command line arguments
    if len(sys.argv) >= 2:
        url = sys.argv[1]
    else:
        # Interactive mode
        url = input("Enter website URL to scrape: ").strip()
        if not url:
            url = "https://polishventure.com/shop/"
            print(f"Using default URL: {url}")
    
    if len(sys.argv) >= 3:
        try:
            max_products = int(sys.argv[2])
        except ValueError:
            max_products = 100
    else:
        # Interactive mode
        try:
            max_input = input("Max products to scrape (default: 100): ").strip()
            max_products = int(max_input) if max_input else 100
        except ValueError:
            max_products = 100
    
    # Validate inputs
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    max_products = max(1, min(max_products, 5000))  # Reasonable limits
    
    # Run the scraper
    try:
        result = asyncio.run(run_scraper(url, max_products))
        
        if result:
            print(f"\n✨ Done! Open {result} to see your scraped data.")
        
        return 0 if result else 1
        
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())