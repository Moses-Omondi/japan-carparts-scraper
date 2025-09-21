#!/usr/bin/env python3
"""
Debug script to investigate Polish Venture price and link extraction issues.
"""

import sys
import os
import requests
from bs4 import BeautifulSoup

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper import CarPartsScraper

def debug_polish_venture():
    """Debug the Polish Venture extraction issues."""
    print("🔍 Debugging Polish Venture Extraction Issues")
    print("=" * 55)
    
    test_url = "https://polishventure.com/product/powerzone-battery-din-66/"
    
    try:
        # First, let's manually check what's on the page
        print(f"📍 Fetching: {test_url}")
        response = requests.get(test_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\n💰 Price Investigation:")
        print("-" * 25)
        
        # Check various price selectors
        price_selectors = [
            '.woocommerce-Price-amount bdi',
            '.woocommerce-Price-amount',
            '.price .amount',
            '.price bdi',
            '.price',
            '.product-price',
            'span.price',
            '.amount'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Selector '{selector}':")
                for i, element in enumerate(elements[:3]):  # Show first 3 matches
                    text = element.get_text(strip=True)
                    print(f"  {i+1}. '{text}'")
                print()
        
        # Check what product links are being found
        print("\n🔗 Product Links Investigation:")
        print("-" * 30)
        
        config = {}
        scraper = CarPartsScraper(config)
        
        product_links = scraper.extract_product_links(soup, test_url)
        print(f"Found {len(product_links)} links:")
        
        for i, link in enumerate(product_links[:10]):  # Show first 10
            print(f"  {i+1}. {link}")
            
            # Check if this looks like a real product
            if 'filter' in link.lower() or 'category' in link.lower():
                print(f"      ⚠️  This looks like a filter/category, not a product!")
            elif '#' in link:
                print(f"      ⚠️  This is a page fragment, not a separate product!")
            elif 'add-to-cart' in link:
                print(f"      ⚠️  This is an add-to-cart link, not a product page!")
        
        # Test the actual extraction
        print(f"\n🎯 Testing Product Extraction on: {test_url}")
        print("-" * 50)
        
        product_data = scraper.scrape_product_details(test_url)
        
        print("Extracted data:")
        for key, value in product_data.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            elif isinstance(value, list):
                print(f"  {key}: {len(value)} items - {value[:2] if len(value) > 2 else value}")
            else:
                print(f"  {key}: {value}")
        
        # Compare with expected values
        print(f"\n📋 Expected vs Actual:")
        print("-" * 20)
        expected_price = 19260.0  # Based on the external context you provided
        actual_price = product_data.get('price_kes', 'Not found')
        
        print(f"Expected Price: KES {expected_price:,.0f}")
        print(f"Actual Price:   {actual_price}")
        print(f"Match: {'✅' if actual_price == expected_price else '❌'}")
        
        return product_data
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_price_extraction_directly():
    """Test price extraction directly from known HTML structure."""
    print(f"\n🧪 Testing Price Extraction with Known Structure")
    print("=" * 50)
    
    # Based on the external context, the price should be displayed as "KSh 17,120.00"
    html_content = '''
    <div class="price">
        <span class="woocommerce-Price-amount amount">
            <bdi>
                <span class="woocommerce-Price-currencySymbol">KSh</span>17,120.00
            </bdi>
        </span>
    </div>
    '''
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    config = {}
    scraper = CarPartsScraper(config)
    
    # Test the price extraction
    pricing_info = scraper._extract_pricing_info(soup)
    print(f"Extracted pricing info: {pricing_info}")
    
    # Also test the Polish Venture specific extraction
    product_data = scraper._extract_polish_venture_data(soup, "https://test.com")
    print(f"Polish Venture extraction: {product_data}")
    
if __name__ == "__main__":
    debug_polish_venture()
    test_price_extraction_directly()