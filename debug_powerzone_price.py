#!/usr/bin/env python3
"""
Debug script to test price extraction for the specific Powerzone battery product.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from scraper import CarPartsScraper
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

import requests
from bs4 import BeautifulSoup
import re

def debug_powerzone_price():
    """Debug the price extraction for Powerzone battery."""
    
    # Initialize scraper
    config = {
        'max_pages_per_site': 1,
        'max_products_per_page': 1,
        'request_delay': 1,
        'enable_image_download': False
    }
    scraper = CarPartsScraper(config)
    
    # Test URL for Powerzone battery
    test_url = "https://polishventure.com/product/powerzone-battery-din-50/"
    
    print(f"Debugging price extraction for: {test_url}")
    print("=" * 80)
    
    # First, let's manually fetch and examine the HTML
    try:
        response = scraper.session.get(test_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\n1. RAW PRICE ELEMENTS FOUND:")
        print("-" * 40)
        
        # Check all potential price selectors
        price_selectors = [
            '.summary .price .woocommerce-Price-amount bdi',
            '.summary .price .woocommerce-Price-amount',
            '.entry-summary .price .amount',
            '.product-summary .price .amount',
            '.woocommerce-Price-amount bdi',
            '.woocommerce-Price-amount',
            '.price .amount',
            '.price bdi',
            '.price',
            '.product-price',
            'span.price'
        ]
        
        all_found_prices = []
        for i, selector in enumerate(price_selectors, 1):
            elements = soup.select(selector)
            print(f"\n{i}. Selector: '{selector}'")
            print(f"   Found: {len(elements)} elements")
            
            for j, element in enumerate(elements):
                price_text = element.get_text(strip=True)
                print(f"   Element {j+1}: '{price_text}'")
                
                # Check parent context
                parent = element.find_parent()
                if parent:
                    parent_classes = ' '.join(parent.get('class', []))
                    print(f"   Parent classes: '{parent_classes}'")
                
                # Extract price value
                if 'KSh' in price_text or 'KES' in price_text:
                    cleaned_text = price_text.replace('KSh', '').replace('KES', '').replace(',', '').strip()
                    numbers = re.findall(r'\d+(?:\.\d+)?', cleaned_text)
                    if numbers:
                        try:
                            price_value = float(numbers[0])
                            all_found_prices.append((selector, price_text, price_value))
                            print(f"   Extracted value: {price_value}")
                        except ValueError:
                            print(f"   Could not convert to float")
        
        print(f"\n2. ALL EXTRACTED PRICES:")
        print("-" * 40)
        for selector, text, value in all_found_prices:
            print(f"   {value} KES from '{text}' (selector: {selector})")
        
        print(f"\n3. CURRENT SCRAPER EXTRACTION:")
        print("-" * 40)
        
        # Test with our current scraper
        product_data = scraper.scrape_product_details(test_url)
        
        print(f"Scraper extracted price: {product_data.get('price_kes', 'None')}")
        print(f"Product name: {product_data.get('name', 'None')}")
        print(f"SKU: {product_data.get('sku', 'None')}")
        
        print(f"\n4. EXPECTED vs ACTUAL:")
        print("-" * 40)
        expected_price = 14445.0  # From the page content
        actual_price = product_data.get('price_kes', 0)
        
        print(f"Expected price: KES {expected_price}")
        print(f"Actual extracted: KES {actual_price}")
        
        if actual_price == expected_price:
            print("✓ Price extraction is CORRECT!")
        else:
            print(f"✗ Price extraction is WRONG - difference: {abs(expected_price - actual_price)}")
            
            # Look for the correct price in the HTML more specifically
            print(f"\n5. SEARCHING FOR CORRECT PRICE (14,445 or 14445):")
            print("-" * 50)
            
            # Look for text containing the expected price
            page_text = soup.get_text()
            if "14,445" in page_text or "14445" in page_text:
                print("✓ Expected price found in page text")
                
                # Find elements containing this price
                for element in soup.find_all(string=re.compile(r'14[,\s]*445')):
                    parent_element = element.parent if hasattr(element, 'parent') else element
                    print(f"   Found in element: {parent_element.name if hasattr(parent_element, 'name') else 'text'}")
                    print(f"   Element classes: {parent_element.get('class', []) if hasattr(parent_element, 'get') else 'N/A'}")
                    print(f"   Full text: '{element.strip() if hasattr(element, 'strip') else element}'")
            else:
                print("✗ Expected price NOT found in page text")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_powerzone_price()