#!/usr/bin/env python3
"""
Basic usage example for Excel Scraper.

This example demonstrates how to use the Excel Scraper programmatically
to scrape a website and export the results to Excel.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from excel_scraper import FastExcelScraper, Config


async def basic_scraping_example():
    """Basic scraping example."""
    print("🚀 Basic Excel Scraper Example")
    print("=" * 50)
    
    # Create default configuration
    config = Config()
    
    # Customize configuration
    config.set('max_concurrent_requests', 6)
    config.set('max_pages', 3)
    config.set('output_dir', 'examples/output')
    
    # Initialize scraper
    scraper = FastExcelScraper(config)
    
    # Target URL
    url = "https://polishventure.com/shop/"
    
    try:
        print(f"📡 Scraping: {url}")
        print(f"⚙️ Max concurrent requests: {config.get('max_concurrent_requests')}")
        print(f"📄 Max pages: {config.get('max_pages')}")
        print()
        
        # Scrape the website
        products = await scraper.scrape_website_async(url)
        
        if products:
            print(f"✅ Successfully scraped {len(products)} products")
            
            # Save to Excel
            output_file = scraper.save_to_excel(products)
            print(f"📊 Excel file saved: {output_file}")
            
            # Display sample of scraped data
            print("\n📋 Sample of scraped products:")
            print("-" * 80)
            for i, product in enumerate(products[:5], 1):
                name = product.get('name', 'Unknown')[:50]
                price = product.get('raw_price_text', 'No price')
                print(f"{i:2d}. {name:<50} | {price}")
            
            if len(products) > 5:
                print(f"    ... and {len(products) - 5} more products")
                
        else:
            print("❌ No products found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await scraper.close_session()
        print("\n✨ Scraping completed!")


async def custom_config_example():
    """Example with custom configuration file."""
    print("\n🔧 Custom Configuration Example")
    print("=" * 50)
    
    # Load custom configuration
    config_path = Path(__file__).parent.parent / "config" / "example.json"
    config = Config(str(config_path))
    
    # Override some settings
    config.set('max_pages', 2)
    config.set('output_dir', 'examples/output')
    config.set('file_prefix', 'custom_scrape')
    
    scraper = FastExcelScraper(config)
    
    try:
        print(f"📋 Configuration loaded from: {config_path}")
        print(f"🎯 Target: {config.get('polish_venture.base_url')}")
        
        # Scrape with custom config
        products = await scraper.scrape_website_async(
            config.get('polish_venture.base_url')
        )
        
        if products:
            # Save with custom filename
            output_file = scraper.save_to_excel(
                products,
                filename="custom_products.xlsx"
            )
            print(f"📊 Custom Excel file: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await scraper.close_session()


async def main():
    """Run all examples."""
    await basic_scraping_example()
    await custom_config_example()


if __name__ == "__main__":
    asyncio.run(main())