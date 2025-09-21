"""
Fast Excel Scraper - High-performance async web scraper for Excel export.
"""

import asyncio
import aiohttp
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .config import Config
from .utils import (
    setup_logging, extract_price_from_text, generate_filename, 
    ensure_directory_exists, clean_product_name
)


class FastExcelScraper:
    """High-performance async scraper optimized for Excel export."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the scraper.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.session = None
        self.logger = setup_logging()
        
    async def create_session(self) -> None:
        """Create aiohttp session with optimized settings."""
        connector = aiohttp.TCPConnector(
            limit=self.config.get('max_concurrent_requests'),
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.get('timeout'))
        
        headers = {
            'User-Agent': self.config.get('user_agent'),
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
    
    async def close_session(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """
        Fetch a single page with semaphore control.
        
        Args:
            url: URL to fetch
            semaphore: Semaphore for concurrency control
        
        Returns:
            Page content or None
        """
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
                await asyncio.sleep(self.config.get('request_delay'))
    
    def extract_product_data(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract product data from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for the page
        
        Returns:
            List of extracted products
        """
        products = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Site-specific extraction
        if 'polishventure.com' in base_url:
            products = self._extract_polish_venture_products(soup, base_url)
        else:
            products = self._extract_generic_products(soup, base_url)
        
        return products
    
    def _extract_polish_venture_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract products from Polish Venture with detailed extraction."""
        products = []
        
        # First extract product links for detailed scraping
        product_links = self._extract_product_links(soup, base_url)
        
        if product_links:
            # Scrape detailed information from individual product pages
            max_products = self.config.get('max_products_per_page', 50)
            
            for i, product_url in enumerate(product_links[:max_products]):
                self.logger.info(f"Extracting detailed Polish Venture product {i+1}/{min(len(product_links), max_products)}")
                
                # Extract detailed product data synchronously
                product_data = self._extract_polish_venture_product_sync(product_url)
                if product_data and product_data.get('name'):
                    products.append(product_data)
        
        # Fallback to basic extraction if no detailed links found
        if not products:
            selectors = self.config.get('polish_venture.product_selectors')
            
            for selector in selectors:
                product_elements = soup.select(selector)
                if product_elements:
                    for element in product_elements:
                        product = self._extract_single_product(element, base_url)
                        if product and product.get('name'):
                            products.append(product)
                    break
        
        return products
    
    def _extract_generic_products(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract products from generic sites."""
        products = []
        
        selectors = ['[class*="product"]', '[class*="item"]', '[data-product]']
        
        for selector in selectors:
            elements = soup.select(selector)
            if len(elements) > 3:
                for element in elements[:self.config.get('max_products_per_page')]:
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
                    product['name'] = clean_product_name(name)
                    break
        
        # Extract price
        price_selectors = ['.price', '.amount', '[class*="price"]', '.cost']
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_info = extract_price_from_text(price_text)
                if price_info:
                    product.update(price_info)
                    break
        
        # Extract SKU/ID
        sku_selectors = ['[data-product-id]', '.sku', '[data-sku]']
        for selector in sku_selectors:
            sku_elem = element.select_one(selector)
            if sku_elem:
                sku = (sku_elem.get_text(strip=True) or 
                       sku_elem.get('data-product-id', '') or 
                       sku_elem.get('data-sku', ''))
                if sku:
                    product['sku'] = sku
                    break
        
        # Extract product URL
        link_elem = element.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href')
            if href:
                product['product_url'] = urljoin(base_url, href)
        
        return product
    
    def construct_page_urls(self, base_url: str, max_pages: int) -> List[str]:
        """Construct URLs for multiple pages."""
        urls = [base_url]
        
        for page in range(2, max_pages + 1):
            page_url = f"{base_url}?page={page}" if '?' not in base_url else f"{base_url}&page={page}"
            urls.append(page_url)
        
        return urls
    
    async def scrape_website_async(self, base_url: str) -> List[Dict[str, Any]]:
        """
        Main async scraping method.
        
        Args:
            base_url: Base URL to scrape
        
        Returns:
            List of scraped products
        """
        self.logger.info(f"Starting async scraping of {base_url}")
        
        if not self.session:
            await self.create_session()
        
        # Generate page URLs
        max_pages = self.config.get('max_pages')
        page_urls = self.construct_page_urls(base_url, max_pages)
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.get('max_concurrent_requests'))
        
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
        
        # Remove duplicates
        unique_products = self._deduplicate_products(all_products)
        
        self.logger.info(f"Total unique products found: {len(unique_products)}")
        return unique_products
    
    def _deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products."""
        seen = set()
        unique_products = []
        
        for product in products:
            key = product.get('product_url') or product.get('name', '')
            if key and key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        return unique_products
    
    def _extract_product_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract product page links from listing page."""
        product_links = set()
        
        # Polish Venture specific product link selectors
        link_selectors = [
            'a[href*="/product/"]',
            '.product-item a[href]',
            '.product a[href]',
            '.woocommerce-loop-product__link[href]',
            'h2 a[href]',
            'h3 a[href]'
        ]
        
        for selector in link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    if self._is_product_url(absolute_url):
                        product_links.add(absolute_url)
        
        return list(product_links)
    
    def _is_product_url(self, url: str) -> bool:
        """Check if URL is a product page."""
        url_lower = url.lower()
        return (
            '/product/' in url_lower and
            not any(exclude in url_lower for exclude in [
                'add-to-cart', 'filter', 'page=', 'orderby=', 'category'
            ])
        )
    
    def _extract_polish_venture_product_sync(self, product_url: str) -> Dict[str, Any]:
        """Extract detailed product data from Polish Venture product page (synchronous)."""
        try:
            import requests
            response = requests.get(product_url, timeout=self.config.get('timeout', 20))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            return self._extract_polish_venture_data(soup, product_url)
            
        except Exception as e:
            self.logger.error(f"Error scraping Polish Venture product {product_url}: {e}")
            return {}
    
    def _extract_polish_venture_data(self, soup: BeautifulSoup, product_url: str) -> Dict[str, Any]:
        """Extract detailed data from Polish Venture product page."""
        import re
        import json as json_module
        
        product_data = {
            'source_url': product_url,
            'scraped_at': time.time()
        }
        
        # Extract product name
        name_selectors = [
            'h1.entry-title', 'h1.product_title', 'h1.product-title',
            '.product_title', '.entry-title', 'h1'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 3:
                    product_data['name'] = clean_product_name(name)
                    break
        
        # Extract price with multiple methods
        all_prices = []
        
        # Method 1: Structured data (JSON-LD)
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json_module.loads(script.string)
                if isinstance(data, dict) and '@graph' in data:
                    for item in data['@graph']:
                        if item.get('@type') == 'Product' and 'offers' in item:
                            for offer in item['offers']:
                                if 'priceSpecification' in offer:
                                    for price_spec in offer['priceSpecification']:
                                        price_str = price_spec.get('price')
                                        if price_str:
                                            try:
                                                price_value = float(price_str)
                                                if price_value > 0:
                                                    all_prices.append(price_value)
                                                    break
                                            except ValueError:
                                                continue
            except (json_module.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Method 2: Main product area
        if not all_prices:
            main_areas = ['.single-product-wrapper', '.product-detail', '.entry-summary', '.summary']
            main_area = None
            for area_selector in main_areas:
                main_area = soup.select_one(area_selector)
                if main_area:
                    break
            
            if main_area:
                price_selectors = [
                    '.woocommerce-Price-amount bdi', '.woocommerce-Price-amount',
                    '.price .amount', '.price bdi', '.price'
                ]
                
                for selector in price_selectors:
                    elements = main_area.select(selector)
                    for element in elements:
                        price_text = element.get_text(strip=True)
                        if 'KSh' in price_text or 'KES' in price_text:
                            cleaned_text = price_text.replace('KSh', '').replace('KES', '').replace(',', '').strip()
                            numbers = re.findall(r'\d+(?:\.\d+)?', cleaned_text)
                            if numbers:
                                try:
                                    price_value = float(numbers[0])
                                    if price_value > 100:  # Filter out obvious errors
                                        all_prices.append(price_value)
                                except ValueError:
                                    continue
        
        # Set pricing information
        if all_prices:
            price = all_prices[0]  # Take the first valid price
            product_data['price_kes'] = price
            product_data['original_currency'] = 'KES'
            product_data['raw_price_text'] = f'KSh {price:,.2f}'
        
        # Extract SKU
        sku_selectors = ['.sku', '.product_meta .sku', '[data-sku]']
        for selector in sku_selectors:
            element = soup.select_one(selector)
            if element:
                sku = element.get_text(strip=True)
                if sku:
                    product_data['sku'] = sku
                    break
        
        # Extract brand
        brand_selectors = ['.brand', '.product_meta .brand', '[data-brand]']
        for selector in brand_selectors:
            element = soup.select_one(selector)
            if element:
                brand = element.get_text(strip=True)
                if brand:
                    product_data['brand'] = brand
                    break
        
        # Extract category
        category_selectors = ['.product_meta .posted_in a', '.breadcrumb a', '.category a']
        categories = []
        for selector in category_selectors:
            elements = soup.select(selector)
            for element in elements:
                cat = element.get_text(strip=True)
                if cat and cat.lower() not in ['home', 'shop']:
                    categories.append(cat)
        
        if categories:
            product_data['category'] = ' > '.join(categories[:3])  # Limit to 3 levels
        
        # Extract description
        desc_selectors = [
            '.woocommerce-product-details__short-description',
            '.product-short-description', '.entry-summary p', '.summary p'
        ]
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                desc = element.get_text(strip=True)
                if desc and len(desc) > 20:
                    product_data['description'] = desc[:500]  # Limit length
                    break
        
        # Extract stock status
        stock_element = soup.select_one('.stock')
        if stock_element:
            stock_text = stock_element.get_text(strip=True).lower()
            if 'in stock' in stock_text:
                product_data['stock_status'] = 'In Stock'
            elif 'out of stock' in stock_text:
                product_data['stock_status'] = 'Out of Stock'
        
        # Extract images
        image_selectors = [
            '.woocommerce-product-gallery img', '.product-image img',
            '.wp-post-image', '.attachment-shop_single'
        ]
        images = []
        for selector in image_selectors:
            elements = soup.select(selector)
            for img in elements[:5]:  # Limit to 5 images
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append(urljoin(product_url, src))
        
        product_data['images'] = images
        product_data['primary_image'] = images[0] if images else None
        
        # Check for warranty and shipping info
        page_text = soup.get_text().lower()
        product_data['has_warranty'] = 'warranty' in page_text or 'guarantee' in page_text
        product_data['has_shipping_info'] = 'shipping' in page_text or 'delivery' in page_text
        
        return product_data
    
    def save_to_excel(self, products: List[Dict[str, Any]], 
                      filename: Optional[str] = None, 
                      output_dir: Optional[str] = None) -> str:
        """
        Save products to Excel file.
        
        Args:
            products: List of products to save
            filename: Optional custom filename
            output_dir: Optional custom output directory
        
        Returns:
            Path to created Excel file
        """
        if not filename:
            prefix = self.config.get('file_prefix')
            timestamp_format = self.config.get('timestamp_format')
            filename = generate_filename(prefix, 'xlsx', timestamp_format)
        
        if not output_dir:
            output_dir = self.config.get('output_dir')
        
        ensure_directory_exists(output_dir)
        file_path = f"{output_dir}/{filename}"
        
        # Prepare data in legacy format
        excel_data = []
        for i, product in enumerate(products, 1):
            row = {
                'Product ID': i,
                'Product Name': product.get('name', ''),
                'Price (KES)': product.get('price_kes', 0),
                'Original Currency': product.get('original_currency', ''),
                'SKU': product.get('sku', ''),
                'Brand': product.get('brand', ''),
                'Category': product.get('category', ''),
                'Stock Status': product.get('stock_status', ''),
                'Description': product.get('description', '')[:200] + ('...' if len(product.get('description', '')) > 200 else ''),
                'Primary Image URL': product.get('primary_image', ''),
                'Total Images': len(product.get('images', [])),
                'Source URL': product.get('source_url', ''),
                'Scraped Date': datetime.fromtimestamp(
                    product.get('scraped_at', 0)
                ).strftime('%Y-%m-%d %H:%M:%S'),
                'Has Warranty': product.get('has_warranty', False),
                'Has Shipping Info': product.get('has_shipping_info', False)
            }
            
            # Add pricing breakdown if available
            if product.get('price_jpy'):
                row['Price (JPY)'] = product.get('price_jpy', 0)
                row['Exchange Rate Used'] = product.get('exchange_rate', 0)
            
            # Add specifications if available
            if product.get('specifications'):
                specs = product.get('specifications', {})
                row['Specifications'] = '; '.join([f"{k}: {v}" for k, v in specs.items() if k and v])
            
            excel_data.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(excel_data)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Products']
            
            from openpyxl.styles import Font, PatternFill
            
            # Format headers
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                # Set width with some padding, max 50
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Create summary sheet
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_data = {
                'Metric': [
                    'Total Products Scraped',
                    'Products with Valid Prices',
                    'Products with SKU',
                    'Products with Brand Info',
                    'Products with Images',
                    'Average Price (KES)',
                    'Highest Price (KES)',
                    'Lowest Price (KES)',
                    'Scraping Date',
                    'Source Website'
                ],
                'Value': [
                    len(df),
                    len(df[df['Price (KES)'] > 0]) if 'Price (KES)' in df.columns else 0,
                    len(df[df['SKU'].astype(str).str.len() > 0]) if 'SKU' in df.columns else 0,
                    len(df[df['Brand'].astype(str).str.len() > 0]) if 'Brand' in df.columns else 0,
                    len(df[df['Total Images'] > 0]) if 'Total Images' in df.columns else 0,
                    f"{df[df['Price (KES)'] > 0]['Price (KES)'].mean():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 and 'Price (KES)' in df.columns else "0",
                    f"{df['Price (KES)'].max():.2f}" if 'Price (KES)' in df.columns and df['Price (KES)'].max() > 0 else "0",
                    f"{df[df['Price (KES)'] > 0]['Price (KES)'].min():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 and 'Price (KES)' in df.columns else "0",
                    timestamp,
                    products[0].get('source_url', '') if products else ''
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Format summary sheet
            summary_worksheet = writer.sheets['Summary']
            for cell in summary_worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
            
            # Auto-adjust summary columns
            for column in summary_worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 60)
                summary_worksheet.column_dimensions[column_letter].width = adjusted_width
        
        self.logger.info(f"Excel file saved: {file_path}")
        return file_path