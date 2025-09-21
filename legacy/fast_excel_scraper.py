#!/usr/bin/env python3
"""
Fast Excel Scraper - Optimized for speed and Excel export only.
Removes all unnecessary features like PDF generation, image processing, etc.
Uses async processing for maximum speed.
"""

import asyncio
import aiohttp
import pandas as pd
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import os
import sys

class FastExcelScraper:
    """Ultra-fast scraper optimized for Excel export only."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self.get_default_config()
        self.scraped_data = []
        self.session = None
        self.setup_logging()
        
    def get_default_config(self) -> Dict[str, Any]:
        """Get optimized default configuration."""
        return {
            'max_concurrent_requests': 10,  # Async requests limit
            'request_delay': 0.5,  # Reduced delay for speed
            'timeout': 15,  # Reduced timeout
            'max_products_per_page': 50,
            'max_pages': 20,  # Reasonable limit for testing
            'retry_attempts': 2,  # Reduced retries
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def setup_logging(self):
        """Setup minimal logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def create_session(self):
        """Create aiohttp session with optimized settings."""
        connector = aiohttp.TCPConnector(
            limit=self.config['max_concurrent_requests'],
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
        
        headers = {
            'User-Agent': self.config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
    
    async def close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """Fetch a single page with semaphore control."""
        async with semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        self.logger.warning(f"HTTP {response.status} for {url}")
                        return None
            except Exception as e:
                self.logger.error(f"Error fetching {url}: {e}")
                return None
            finally:
                # Add delay between requests
                await asyncio.sleep(self.config['request_delay'])
    
    def extract_product_data(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Extract product data from HTML - optimized for speed."""
        products = []
        soup = BeautifulSoup(html, 'lxml')  # Use lxml for speed
        
        # Polish Venture specific selectors (based on existing working code)
        if 'polishventure.com' in base_url:
            products = self._extract_polish_venture_products(soup, base_url)
        else:
            # Generic extraction for other sites
            products = self._extract_generic_products(soup, base_url)
        
        return products
    
    def _extract_polish_venture_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Polish Venture specific extraction (optimized)."""
        products = []
        
        # Look for product containers
        product_selectors = [
            '.product-item', '.product', '.woocommerce-loop-product__link',
            '.product-small', '.box-image', '.col-inner'
        ]
        
        for selector in product_selectors:
            product_elements = soup.select(selector)
            if product_elements:
                for element in product_elements:
                    product = self._extract_single_product(element, base_url)
                    if product and product.get('name'):
                        products.append(product)
                break  # Use first working selector
        
        return products
    
    def _extract_generic_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Generic product extraction for any site."""
        products = []
        
        # Generic selectors
        product_selectors = [
            '[class*="product"]', '[class*="item"]', '[data-product]'
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            if len(elements) > 3:  # Ensure we found actual product elements
                for element in elements[:self.config['max_products_per_page']]:
                    product = self._extract_single_product(element, base_url)
                    if product and product.get('name'):
                        products.append(product)
                break
        
        return products
    
    def _extract_single_product(self, element, base_url: str) -> Dict[str, Any]:
        """Extract data from a single product element."""
        product = {
            'scraped_at': time.time(),
            'source_url': base_url
        }
        
        # Extract name
        name_selectors = ['h2', 'h3', '.product-title', '.title', 'a[title]']
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True) or name_elem.get('title', '').strip()
                if name and len(name) > 5:
                    product['name'] = name[:200]  # Limit length
                    break
        
        # Extract price
        price_selectors = [
            '.price', '.amount', '[class*="price"]', '.cost'
        ]
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._extract_price_from_text(price_text)
                if price:
                    product.update(price)
                    break
        
        # Extract SKU/ID
        sku_selectors = ['[data-product-id]', '.sku', '[data-sku]']
        for selector in sku_selectors:
            sku_elem = element.select_one(selector)
            if sku_elem:
                sku = sku_elem.get_text(strip=True) or sku_elem.get('data-product-id', '') or sku_elem.get('data-sku', '')
                if sku:
                    product['sku'] = sku
                    break
        
        # Extract product URL for more details
        link_elem = element.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href')
            if href:
                product['product_url'] = urljoin(base_url, href)
        
        return product
    
    def _extract_price_from_text(self, price_text: str) -> Optional[Dict[str, Any]]:
        """Extract price information from text."""
        import re
        
        if not price_text:
            return None
        
        # Common price patterns
        patterns = {
            'kes': r'KES?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            'usd': r'USD?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            'jpy': r'¥\s*(\d{1,3}(?:,\d{3})*)',
            'eur': r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
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
    
    def construct_page_urls(self, base_url: str, max_pages: int) -> List[str]:
        """Construct URLs for multiple pages."""
        urls = [base_url]  # First page
        
        # Common pagination patterns
        for page in range(2, max_pages + 1):
            # Try different pagination formats
            page_urls = [
                f"{base_url}?page={page}",
                f"{base_url}/page/{page}/",
                f"{base_url}?p={page}",
                f"{base_url}&page={page}" if '?' in base_url else f"{base_url}?page={page}"
            ]
            urls.extend(page_urls[:1])  # Add only the first format to avoid duplicates
        
        return urls[:max_pages]
    
    async def scrape_website_async(self, base_url: str) -> List[Dict[str, Any]]:
        """Main async scraping method."""
        self.logger.info(f"Starting async scraping of {base_url}")
        
        if not self.session:
            await self.create_session()
        
        # Generate page URLs
        page_urls = self.construct_page_urls(base_url, self.config['max_pages'])
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config['max_concurrent_requests'])
        
        # Fetch all pages concurrently
        tasks = [self.fetch_page(url, semaphore) for url in page_urls]
        html_pages = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract products from all pages
        all_products = []
        for i, html in enumerate(html_pages):
            if isinstance(html, str) and html:
                products = self.extract_product_data(html, page_urls[i])
                all_products.extend(products)
                self.logger.info(f"Page {i+1}: Found {len(products)} products")
            elif isinstance(html, Exception):
                self.logger.error(f"Page {i+1} failed: {html}")
        
        # Remove duplicates based on product URL or name
        unique_products = self._deduplicate_products(all_products)
        
        self.logger.info(f"Total unique products found: {len(unique_products)}")
        return unique_products
    
    def _deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products."""
        seen = set()
        unique_products = []
        
        for product in products:
            # Create unique key based on product URL or name
            key = product.get('product_url') or product.get('name', '')
            if key and key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        return unique_products
    
    def save_to_excel(self, products: List[Dict[str, Any]], filename: str = None) -> str:
        """Save products to Excel file with optimized formatting."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"scraped_products_FAST_{timestamp}.xlsx"
        
        # Prepare data for Excel
        excel_data = []
        for i, product in enumerate(products, 1):
            row = {
                'ID': i,
                'Product Name': product.get('name', ''),
                'Price (KES)': product.get('price_kes', 0),
                'Price (USD)': product.get('price_usd', 0),
                'Price (JPY)': product.get('price_jpy', 0),
                'Price (EUR)': product.get('price_eur', 0),
                'Original Currency': product.get('original_currency', ''),
                'Raw Price Text': product.get('raw_price_text', ''),
                'SKU': product.get('sku', ''),
                'Product URL': product.get('product_url', ''),
                'Source URL': product.get('source_url', ''),
                'Scraped Date': datetime.fromtimestamp(product.get('scraped_at', 0)).strftime('%Y-%m-%d %H:%M:%S')
            }
            excel_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(excel_data)
        
        # Save to Excel with minimal formatting for speed
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Quick formatting
            worksheet = writer.sheets['Products']
            
            # Bold headers
            from openpyxl.styles import Font
            header_font = Font(bold=True)
            for cell in worksheet[1]:
                cell.font = header_font
            
            # Auto-adjust columns (quick method)
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 40)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        self.logger.info(f"Excel file saved: {filename}")
        return filename


async def main():
    """Main async function to run the scraper."""
    print("🚀 FAST EXCEL SCRAPER")
    print("=" * 50)
    print("Optimized for maximum speed and Excel export only")
    print()
    
    # Get target URL
    url = input("Enter website URL to scrape: ").strip()
    if not url:
        url = "https://polishventure.com/shop/"  # Default
        print(f"Using default URL: {url}")
    
    # Get max products
    try:
        max_products = input("Max products to scrape (default: 100): ").strip()
        max_products = int(max_products) if max_products else 100
    except ValueError:
        max_products = 100
    
    # Calculate max pages (assuming ~20 products per page)
    max_pages = max(1, max_products // 20)
    
    # Configure scraper
    config = {
        'max_concurrent_requests': 8,
        'request_delay': 0.3,
        'timeout': 20,
        'max_products_per_page': 50,
        'max_pages': max_pages,
        'retry_attempts': 2
    }
    
    scraper = FastExcelScraper(config)
    
    try:
        start_time = time.time()
        
        # Scrape website
        products = await scraper.scrape_website_async(url)
        
        # Save to Excel
        if products:
            filename = scraper.save_to_excel(products)
            
            end_time = time.time()
            runtime = end_time - start_time
            
            print(f"\n✅ SUCCESS!")
            print(f"📊 Scraped {len(products)} products in {runtime:.1f} seconds")
            print(f"⚡ Rate: {len(products) / runtime:.1f} products/second")
            print(f"📁 Excel file: {filename}")
        else:
            print("❌ No products found!")
    
    finally:
        await scraper.close_session()


if __name__ == "__main__":
    # Handle event loop for different Python versions
    try:
        asyncio.run(main())
    except AttributeError:
        # Python < 3.7
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.close()