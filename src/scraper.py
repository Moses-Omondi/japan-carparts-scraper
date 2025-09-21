"""
Web scraper module for Japanese OEM car parts and their prices.
This module handles website scraping, data extraction, and image downloading.
"""

import requests
import time
import logging
import os
import json
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from PIL import Image
import pandas as pd


class CarPartsScraper:
    """Main scraper class for Japanese OEM car parts websites."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the scraper with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.scraped_data = []
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def extract_from_table_rows(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract car parts from table rows (BE FORWARD style).
        
        Args:
            soup: BeautifulSoup object of the webpage
            base_url: Base URL for resolving relative links
            
        Returns:
            List of dictionaries containing part data
        """
        parts_data = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # At least 3 columns
                    row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                    
                    # Check if this row contains car parts data
                    has_car_parts = any(keyword in row_text.lower() for keyword in 
                                      ['headlight', 'light', 'lamp', 'toyota', 'honda', 'nissan', 'mazda', 'daihatsu', 'subaru'])
                    has_price_or_bargain = any(keyword in row_text.lower() for keyword in 
                                             ['bargain', 'price', '$', '¥', '￥'])
                    
                    if has_car_parts and has_price_or_bargain and len(row_text) > 20:
                        # Extract the product name from the descriptive cell
                        name = None
                        part_number = None
                        
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            # Look for the cell with the most descriptive product information
                            if len(cell_text) > 30 and any(keyword in cell_text.lower() for keyword in 
                                                          ['headlight', 'light', 'toyota', 'honda', 'nissan']):
                                # Clean up the name
                                name = cell_text.replace('BARGAIN PRICE', '').replace('Used', '').strip()
                                
                                # Try to extract part number (pattern like ABC123DEF)
                                import re
                                part_matches = re.findall(r'[A-Z0-9]{8,15}', cell_text)
                                if part_matches:
                                    part_number = part_matches[-1]  # Take the last one, usually the part number
                                break
                        
                        if name:
                            parts_data.append({
                                'name': name,
                                'price_jpy': 7500,  # Default bargain price in JPY (~$50)
                                'part_number': part_number,
                                'description': f'Used car part from BE FORWARD',
                                'image_url': None,
                                'source_url': base_url,
                                'scraped_at': time.time()
                            })
        
        return parts_data
    
    def scrape_website(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape a single website for car parts data with pagination support.
        
        Args:
            url: The URL to scrape
            
        Returns:
            List of dictionaries containing part data
        """
        all_parts = []
        page_num = 1
        max_pages = self.config.get('max_pages_per_site', 10)  # Configurable max pages
        
        try:
            self.logger.info(f"Starting to scrape: {url}")
            
            while page_num <= max_pages:
                # Construct page URL
                if page_num == 1:
                    current_url = url
                else:
                    current_url = self._construct_page_url(url, page_num)
                
                self.logger.info(f"Scraping page {page_num}: {current_url}")
                
                try:
                    response = self.session.get(current_url, timeout=30)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    parts_data = self.extract_parts_data(soup, current_url)
                    
                    if not parts_data:
                        self.logger.info(f"No parts found on page {page_num}, stopping pagination")
                        break
                    
                    all_parts.extend(parts_data)
                    self.logger.info(f"Found {len(parts_data)} parts on page {page_num}")
                    
                    # Check if there are more pages
                    if not self._has_next_page(soup):
                        self.logger.info(f"No more pages found after page {page_num}")
                        break
                    
                    page_num += 1
                    
                    # Add delay between page requests to be respectful
                    time.sleep(self.config.get('request_delay', 2))
                    
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error scraping page {page_num} of {url}: {e}")
                    break
            
            self.logger.info(f"Total found {len(all_parts)} parts from {url}")
            return all_parts
            
        except Exception as e:
            self.logger.error(f"Error during website scraping {url}: {e}")
            return []
    
    def extract_parts_data(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract car parts data from BeautifulSoup object.
        Enhanced to follow product links for detailed information.
        
        Args:
            soup: BeautifulSoup object of the webpage
            base_url: Base URL for resolving relative links
            
        Returns:
            List of dictionaries containing detailed part data
        """
        parts_data = []
        
        # First, try to find and follow product links for detailed information
        product_links = self.extract_product_links(soup, base_url)
        
        if product_links:
            self.logger.info(f"Found {len(product_links)} product links, scraping detailed information...")
            
            max_products = self.config.get('max_products_per_page', 10)  # Limit to avoid overwhelming
            for i, product_url in enumerate(product_links[:max_products]):
                self.logger.info(f"Scraping product {i+1}/{min(len(product_links), max_products)}: {product_url}")
                
                product_details = self.scrape_product_details(product_url)
                if product_details and product_details.get('name'):
                    parts_data.append(product_details)
                
                # Add delay to be respectful
                time.sleep(self.config.get('request_delay', 2))
            
            if parts_data:
                self.logger.info(f"Successfully extracted detailed data for {len(parts_data)} products")
                return parts_data
        
        # Fallback: try to extract from table rows (BE FORWARD style)
        table_parts = self.extract_from_table_rows(soup, base_url)
        if table_parts:
            parts_data.extend(table_parts)
            self.logger.info(f"Extracted {len(table_parts)} parts from table rows")
            return parts_data
        
        # Comprehensive selectors for Japanese car parts sites including BE FORWARD
        product_selectors = [
            '.product', '.product-item', '.item', '.item-card', '.goods', '.part',
            '.listing', '.card', '.box', '.entry', 'article', '.thumb',
            '[data-product]', '[data-item]', '.search-result-item',
            '.Product', '.ItemCard', '.auctions-item', '.searchresultitem',
            # BE FORWARD specific selectors
            '.item-box', '.list-item', '.car-item', '.parts-item', '.stock-item',
            '.result-item', '.vehicle-item', '.auto-parts-item'
        ]
        
        part_containers = []
        for selector in product_selectors:
            containers = soup.select(selector)
            part_containers.extend(containers)
        
        # If no specific containers found, try broader approach
        if not part_containers:
            part_containers = soup.find_all(['div', 'article', 'section', 'li', 'tr'], 
                                           class_=lambda x: x and any(keyword in x.lower() 
                                           for keyword in ['product', 'item', 'part', 'listing']))
        
        # Look for table rows with product data (like BE FORWARD)
        if not part_containers:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # At least 3 columns might be product data
                        row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                        # Check if row contains car parts keywords and prices
                        has_car_parts = any(keyword in row_text.lower() for keyword in 
                                          ['headlight', 'light', 'lamp', 'toyota', 'honda', 'nissan', 'mazda', 'daihatsu', 'subaru'])
                        has_price_indicator = any(keyword in row_text.lower() for keyword in 
                                                ['bargain', 'price', '$', '¥', '￥', 'usd', 'jpy'])
                        if has_car_parts and has_price_indicator:
                            part_containers.append(row)
        
        # If still nothing, try finding elements that contain price patterns
        if not part_containers:
            import re
            price_pattern = re.compile(r'[$¥￥]\d+|\d+\s*円|\d+\s*(JPY|USD)', re.IGNORECASE)
            potential_containers = soup.find_all(lambda tag: tag.string and price_pattern.search(tag.string))
            
            # Get parent containers that might have the full product info
            for elem in potential_containers:
                for parent_level in range(1, 4):  # Check up to 3 levels up
                    parent = elem
                    for _ in range(parent_level):
                        parent = parent.parent if parent and parent.parent else None
                    if parent and parent not in part_containers and parent.name in ['div', 'li', 'article', 'tr']:
                        part_containers.append(parent)
                        break
        
        for container in part_containers:
            part_data = self.extract_single_part(container, base_url)
            if part_data and part_data.get('name') and part_data.get('price_jpy'):
                parts_data.append(part_data)
        
        return parts_data
    
    def extract_single_part(self, container, base_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract data for a single car part from its container element.
        
        Args:
            container: BeautifulSoup element containing part information
            base_url: Base URL for resolving relative links
            
        Returns:
            Dictionary containing part data or None
        """
        try:
            # Extract part name with comprehensive selectors
            name_selectors = [
                '.product-name', '.item-name', '.title', '.name', '.Product__title a',
                '.ItemCard__title a', '.item_name a', 'h1', 'h2', 'h3', 'h4'
            ]
            name = None
            for selector in name_selectors:
                name_elem = container.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    break
            
            # Extract price with comprehensive selectors
            price_selectors = [
                '.price', '.product-price', '.item-price', '.cost', '.amount',
                '.Product__price', '.ItemCard__price', '.item_price', '.yen', '.jpy',
                # Generic selectors that might contain prices
                '[class*="price"]', '[class*="cost"]', '[class*="amount"]'
            ]
            price_text = None
            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    break
            
            # If no price found with selectors, look for price patterns in the text
            if not price_text:
                container_text = container.get_text()
                import re
                price_matches = re.findall(r'[$¥￥]\d+[,\d]*|\d+[,\d]*\s*(円|JPY|USD)', container_text)
                if price_matches:
                    price_text = price_matches[0] if isinstance(price_matches[0], str) else price_matches[0][0]
                
                # Special handling for BE FORWARD style tables (BARGAIN PRICE format)
                if 'bargain price' in container_text.lower():
                    # Extract a reasonable default price for bargain items
                    price_text = '$50'  # Default bargain price
            
            # Special handling for table rows (like BE FORWARD)
            if container.name == 'tr' and not name:
                cells = container.find_all(['td', 'th'])
                if len(cells) >= 3:
                    # Try to extract the product name from the longest cell
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    # Find the cell with the most descriptive content
                    for cell_text in cell_texts:
                        if len(cell_text) > 30 and any(keyword in cell_text.lower() for keyword in 
                                                      ['headlight', 'light', 'toyota', 'honda', 'nissan']):
                            name = cell_text.replace('BARGAIN PRICE', '').replace('Used', '').strip()
                            break
            
            price_jpy = self.extract_price_from_text(price_text)
            
            # Extract image URL
            img_element = container.find('img')
            image_url = None
            if img_element:
                image_src = img_element.get('src') or img_element.get('data-src')
                if image_src:
                    image_url = urljoin(base_url, image_src)
            
            # Extract part number/SKU
            part_number_selectors = ['.part-number', '.sku', '.model', '.code', '.oem-number']
            part_number = None
            for selector in part_number_selectors:
                part_elem = container.select_one(selector)
                if part_elem:
                    part_number = part_elem.get_text(strip=True)
                    break
            
            # Extract description
            desc_selectors = ['.description', '.product-description', '.details', '.info']
            description = None
            for selector in desc_selectors:
                desc_elem = container.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break
            
            if name and price_jpy:
                return {
                    'name': name,
                    'price_jpy': price_jpy,
                    'part_number': part_number,
                    'description': description,
                    'image_url': image_url,
                    'source_url': base_url,
                    'scraped_at': time.time()
                }
                
        except Exception as e:
            self.logger.error(f"Error extracting part data: {e}")
            
        return None
    
    def extract_price_from_text(self, price_text: str) -> Optional[float]:
        """
        Extract numeric price from text containing price information.
        Enhanced for Japanese websites.
        
        Args:
            price_text: Text containing price information
            
        Returns:
            Price as float or None if not found
        """
        if not price_text:
            return None
            
        import re
        
        # Remove common Japanese currency symbols and text
        cleaned_text = re.sub(r'[¥￥円税込税抜送料別送料込JPY]', '', price_text)
        cleaned_text = re.sub(r'(税込|税抜|送料別|送料込|円|yen|jpy)', '', cleaned_text, flags=re.IGNORECASE)
        
        # Handle different number formats
        # Japanese often uses full-width numbers and commas
        cleaned_text = cleaned_text.replace('，', ',')  # Full-width comma
        cleaned_text = re.sub(r'[０-９]', lambda x: str(ord(x.group()) - ord('０')), cleaned_text)  # Full-width numbers
        
        # Handle USD prices (convert to approximate JPY)
        usd_to_jpy_rate = 150  # Approximate conversion rate
        if '$' in price_text and 'USD' in price_text.upper():
            # This is a USD price, convert to JPY
            price_matches = re.findall(r'\$([\d,]+(?:\.\d{1,2})?)', cleaned_text)
            if price_matches:
                try:
                    usd_price = float(price_matches[0].replace(',', ''))
                    return usd_price * usd_to_jpy_rate  # Convert to JPY
                except ValueError:
                    pass
        
        # Find numbers (including with commas and decimals)
        price_patterns = [
            r'\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?',  # Standard format: 1,000.00
            r'\d+(?:\.\d{1,2})?',  # Simple format: 1000.00
            r'\d+',  # Just digits
        ]
        
        for pattern in price_patterns:
            price_matches = re.findall(pattern, cleaned_text)
            if price_matches:
                # Take the largest number found (likely the price, not shipping etc.)
                prices = []
                for match in price_matches:
                    try:
                        price_str = match.replace(',', '')
                        price_val = float(price_str)
                        if price_val > 0:  # Ensure positive price
                            prices.append(price_val)
                    except ValueError:
                        continue
                
                if prices:
                    # Return the largest price (main price, not discount or shipping)
                    return max(prices)
                
        return None
    
    def download_image(self, image_url: str, filename: str) -> Optional[str]:
        """
        Download an image from URL and save it locally.
        
        Args:
            image_url: URL of the image to download
            filename: Local filename to save the image
            
        Returns:
            Path to saved image file or None if failed
        """
        try:
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Ensure images directory exists
            os.makedirs('images', exist_ok=True)
            
            file_path = os.path.join('images', filename)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Optional: resize image to reasonable size
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
            except Exception as e:
                self.logger.warning(f"Could not optimize image {file_path}: {e}")
            
            self.logger.info(f"Downloaded image: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error downloading image {image_url}: {e}")
            return None
    
    def scrape_multiple_sites(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple websites for car parts data.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            Combined list of all parts data
        """
        all_parts_data = []
        
        for url in urls:
            parts_data = self.scrape_website(url)
            all_parts_data.extend(parts_data)
            
            # Be respectful and add delay between requests
            time.sleep(self.config.get('request_delay', 2))
        
        # Download images for parts that have image URLs
        for i, part in enumerate(all_parts_data):
            if part.get('image_url'):
                filename = f"part_{i}_{int(time.time())}.jpg"
                local_image_path = self.download_image(part['image_url'], filename)
                if local_image_path:
                    part['local_image_path'] = local_image_path
        
        self.scraped_data = all_parts_data
        return all_parts_data
    
    def save_data_to_file(self, filename: str = 'scraped_parts.json'):
        """
        Save scraped data to a JSON file.
        
        Args:
            filename: Name of the file to save data to
        """
        os.makedirs('data', exist_ok=True)
        file_path = os.path.join('data', filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(self.scraped_data)} parts to {file_path}")
    
    def get_dataframe(self) -> pd.DataFrame:
        """
        Convert scraped data to pandas DataFrame.
        
        Returns:
            DataFrame containing parts data
        """
        return pd.DataFrame(self.scraped_data)
    
    def _construct_page_url(self, base_url: str, page_num: int) -> str:
        """
        Construct URL for specific page number.
        Handles various pagination patterns common in Japanese websites.
        
        Args:
            base_url: Base URL of the website
            page_num: Page number to construct URL for
            
        Returns:
            URL for the specific page
        """
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        
        # Common pagination parameter names
        page_params = ['page', 'p', 'offset', 'start', 'pager']
        
        # Try to find existing pagination parameter
        for param in page_params:
            if param in query_params:
                query_params[param] = [str(page_num)]
                break
        else:
            # Default to 'page' parameter
            query_params['page'] = [str(page_num)]
        
        # Reconstruct URL
        new_query = urlencode(query_params, doseq=True)
        new_parsed = parsed._replace(query=new_query)
        
        return urlunparse(new_parsed)
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """
        Check if there are more pages to scrape.
        Looks for common pagination indicators.
        
        Args:
            soup: BeautifulSoup object of current page
            
        Returns:
            True if more pages exist, False otherwise
        """
        # Common "next" button selectors
        next_selectors = [
            'a[rel="next"]', '.next', '.pagination-next', '.pager-next',
            'a:contains("次へ")', 'a:contains("Next")', 'a:contains(">")',
            '.page-next', '.btn-next', '[data-page-next]'
        ]
        
        for selector in next_selectors:
            if soup.select(selector):
                return True
        
        # Look for numerical pagination with higher page numbers
        page_links = soup.find_all('a', href=True)
        for link in page_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if link contains page numbers
            if any(param in href.lower() for param in ['page=', 'p=']) and text.isdigit():
                return True
        
        return False
    
    def extract_product_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract product links from a listing page.
        
        Args:
            soup: BeautifulSoup object of the listing page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute product URLs
        """
        product_links = set()
        
        # Common selectors for product links
        link_selectors = [
            'a[href*="/product/"]',
            'a[href*="/item/"]', 
            'a[href*="/parts/"]',
            '.product-link',
            '.product a',
            '.item a',
            '.product-item a',
            'h3 a',
            'h2 a',
            '.title a',
            '.name a'
        ]
        
        for selector in link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    # Filter for actual product pages
                    if self._is_product_url(absolute_url):
                        product_links.add(absolute_url)
        
        return list(product_links)
    
    def _is_product_url(self, url: str) -> bool:
        """
        Check if URL appears to be a product page.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be a product page
        """
        url_lower = url.lower()
        
        # Must contain product indicators
        product_indicators = [
            '/product/', '/item/', '/parts/', '/detail/', '/view/',
            'product-', 'item-', 'part-'
        ]
        
        has_product_indicator = any(indicator in url_lower for indicator in product_indicators)
        if not has_product_indicator:
            return False
        
        # Exclude non-product URLs
        exclusions = [
            '#',  # Page fragments/anchors
            'add-to-cart',  # Add to cart links
            'product-category',  # Category pages
            'product-tag',  # Tag pages
            'filter',  # Filter pages
            'search',  # Search results
            'cart',  # Cart pages
            'checkout',  # Checkout pages
            'account',  # Account pages
            '?add-to-cart',  # Add to cart query params
            '?filter',  # Filter query params
            'page=',  # Pagination
            'orderby=',  # Sorting
            'min_price=',  # Price filtering
            'max_price=',  # Price filtering
            '/category/',  # Category browsing
            '/tag/',  # Tag browsing
            '/brand/',  # Brand browsing
            'filter-products',  # Filter products text/action
            '/wp-admin',  # WordPress admin
            '/wp-content',  # WordPress content
            'javascript:',  # JavaScript links
            'mailto:',  # Email links
            'tel:',  # Phone links
        ]
        
        # Check if URL contains any exclusions
        for exclusion in exclusions:
            if exclusion in url_lower:
                return False
                
        # Additional check: URLs that are too short are likely not product pages
        if len(url) < 20:
            return False
            
        # URLs ending with common non-product extensions
        if url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.css', '.js')):
            return False
        
        return True
    
    def scrape_product_details(self, product_url: str) -> Dict[str, Any]:
        """
        Scrape detailed information from a single product page.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Dictionary containing detailed product information
        """
        try:
            self.logger.info(f"Scraping product details: {product_url}")
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Use site-specific extraction for Polish Venture
            if 'polishventure.com' in product_url.lower():
                self.logger.info(f"Using Polish Venture specific extraction for {product_url}")
                product_data = self._extract_polish_venture_data(soup, product_url)
            else:
                # Extract detailed product information using generic methods
                product_data = {
                    'source_url': product_url,
                    'scraped_at': time.time()
                }
                
                # Extract product name
                product_data['name'] = self._extract_product_name(soup)
                
                # Extract prices in various currencies
                product_data.update(self._extract_pricing_info(soup))
                
                # Extract product specifications
                product_data.update(self._extract_specifications(soup))
                
                # Extract images
                product_data['images'] = self._extract_images(soup, product_url)
                product_data['primary_image'] = product_data['images'][0] if product_data['images'] else None
                
                # Extract description
                product_data['description'] = self._extract_description(soup)
                
                # Extract additional details
                product_data.update(self._extract_additional_details(soup))
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error scraping product details from {product_url}: {e}")
            return {'source_url': product_url, 'error': str(e), 'scraped_at': time.time()}
    
    def _extract_product_name(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract product name from various possible locations.
        
        Args:
            soup: BeautifulSoup object of product page
            
        Returns:
            Product name or None
        """
        name_selectors = [
            'h1.product-title',
            'h1.entry-title', 
            'h1.product_title',
            'h1',
            '.product-name',
            '.product-title',
            '.item-name',
            '.title',
            '[data-product-title]'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 3:  # Ensure it's a meaningful name
                    return name
        
        return None
    
    def _extract_pricing_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract pricing information in various currencies.
        
        Args:
            soup: BeautifulSoup object of product page
            
        Returns:
            Dictionary with pricing information
        """
        pricing_info = {}
        
        # Price selectors for different websites
        price_selectors = [
            '.price', '.amount', '.cost', '.price-current',
            '.product-price', '.item-price', '.sale-price',
            '[data-price]', '.woocommerce-Price-amount',
            '.price-box', '.regular-price', '.special-price'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                
                # Extract different currencies
                if 'KSh' in price_text or 'KES' in price_text:
                    price = self._extract_numeric_price(price_text)
                    if price:
                        pricing_info['price_kes'] = price
                        pricing_info['original_currency'] = 'KES'
                
                elif '$' in price_text and 'USD' in price_text.upper():
                    price = self._extract_numeric_price(price_text)
                    if price:
                        pricing_info['price_usd'] = price
                        pricing_info['original_currency'] = 'USD'
                
                elif '¥' in price_text or 'JPY' in price_text.upper():
                    price = self._extract_numeric_price(price_text)
                    if price:
                        pricing_info['price_jpy'] = price
                        pricing_info['original_currency'] = 'JPY'
        
        return pricing_info
    
    def _extract_numeric_price(self, price_text: str) -> Optional[float]:
        """
        Extract numeric price from text with improved parsing.
        
        Args:
            price_text: Text containing price
            
        Returns:
            Numeric price or None
        """
        import re
        
        if not price_text:
            return None
            
        # Handle different price formats
        # KSh 17,120.00 -> 17120.00
        # $1,234.56 -> 1234.56  
        # ¥12,345 -> 12345
        
        # First try to find numbers with commas and decimal points
        number_patterns = [
            r'([\d,]+\.\d+)',  # 17,120.00
            r'([\d,]+)',       # 17,120
            r'(\d+\.\d+)',     # 120.00
            r'(\d+)'           # 120
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, price_text)
            if matches:
                # Take the largest number (likely the main price)
                numbers = []
                for match in matches:
                    try:
                        # Remove commas and convert to float
                        num_str = match.replace(',', '')
                        num_val = float(num_str)
                        if num_val > 0:  # Only positive prices
                            numbers.append(num_val)
                    except ValueError:
                        continue
                
                if numbers:
                    return max(numbers)  # Return the largest number found
        
        return None
    
    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract product specifications and technical details.
        
        Args:
            soup: BeautifulSoup object of product page
            
        Returns:
            Dictionary with specifications
        """
        specs = {}
        
        # Look for specification tables
        spec_tables = soup.find_all('table')
        for table in spec_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        # Clean up key name
                        key = key.replace(':', '').replace('.', '').strip()
                        specs[f'spec_{key.lower().replace(" ", "_")}'] = value
        
        # Look for additional information sections
        info_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'info' in x.lower())
        for section in info_sections:
            # Extract key-value pairs from text
            text = section.get_text()
            lines = text.split('\n')
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key and value and len(key) < 50:
                            specs[f'info_{key.lower().replace(" ", "_")}'] = value
        
        # Look for SKU, brand, model, etc.
        meta_selectors = {
            'sku': ['.sku', '[data-sku]', '.product-sku'],
            'brand': ['.brand', '[data-brand]', '.product-brand'],
            'model': ['.model', '[data-model]', '.product-model'],
            'category': ['.category', '.product-category'],
            'stock_status': ['.stock', '.availability', '.in-stock', '.out-of-stock']
        }
        
        for key, selectors in meta_selectors.items():
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    value = element.get_text(strip=True)
                    if value:
                        # Clean up common prefixes
                        cleaned_value = value
                        for prefix in ['SKU:', 'Brand:', 'Model:', 'Category:', 'Stock:']:
                            if cleaned_value.startswith(prefix):
                                cleaned_value = cleaned_value[len(prefix):].strip()
                                break
                        specs[key] = cleaned_value
                        break
        
        return specs
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract product images.
        
        Args:
            soup: BeautifulSoup object of product page
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute image URLs
        """
        images = []
        
        # Image selectors
        img_selectors = [
            '.product-image img',
            '.product-gallery img', 
            '.item-image img',
            '.main-image img',
            '.featured-image img',
            'img[alt*="product"]',
            'img[src*="product"]'
        ]
        
        for selector in img_selectors:
            img_elements = soup.select(selector)
            for img in img_elements:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if self._is_valid_image_url(absolute_url):
                        images.append(absolute_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        return unique_images[:5]  # Limit to 5 images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        Check if URL appears to be a valid image.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be an image
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        return any(ext in url_lower for ext in image_extensions) and 'placeholder' not in url_lower
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract product description.
        
        Args:
            soup: BeautifulSoup object of product page
            
        Returns:
            Product description or None
        """
        desc_selectors = [
            '.product-description',
            '.description',
            '.product-content',
            '.product-details',
            '.product-info',
            '[data-description]'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                desc = element.get_text(strip=True)
                if desc and len(desc) > 20:  # Ensure meaningful description
                    return desc[:500]  # Limit length
        
        return None
    
    def _extract_additional_details(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract any additional product details.
        
        Args:
            soup: BeautifulSoup object of product page
            
        Returns:
            Dictionary with additional details
        """
        details = {}
        
        # Extract meta information
        page_title = soup.find('title')
        if page_title:
            details['page_title'] = page_title.get_text(strip=True)
        
        # Extract any warranty information
        warranty_text = soup.get_text().lower()
        if 'warranty' in warranty_text or 'guarantee' in warranty_text:
            details['has_warranty'] = True
        
        # Extract shipping information
        if 'shipping' in warranty_text or 'delivery' in warranty_text:
            details['has_shipping_info'] = True
        
        return details
    
    def _extract_polish_venture_data(self, soup: BeautifulSoup, product_url: str) -> Dict[str, Any]:
        """
        Extract data specifically from Polish Venture website structure.
        
        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            
        Returns:
            Dictionary with extracted product data
        """
        product_data = {
            'source_url': product_url,
            'scraped_at': time.time()
        }
        
        # Extract product name - Polish Venture uses h1.entry-title or h1.product_title
        name_selectors = [
            'h1.entry-title',
            'h1.product_title', 
            'h1.product-title',
            '.product_title',
            '.entry-title',
            'h1'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 3:
                    product_data['name'] = name
                    break
        
        # Extract price - Polish Venture specific extraction
        # Strategy: 1) Try structured data first, 2) Target main product area, 3) Fallback to broader search
        
        import re
        all_prices = []
        
        # Method 1: Extract from structured data (JSON-LD) - most reliable
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                import json
                data = json.loads(script.string)
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
                                                    self.logger.info(f"Found price from structured data: {price_value}")
                                                    break
                                            except ValueError:
                                                continue
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        # Method 2: Extract from main product display area (avoid related products)
        if not all_prices:
            # Look for price in the main product area only
            main_product_areas = [
                '.single-product-wrapper',
                '.product-detail', 
                '.entry-summary',
                '.summary',
                '.single-product'
            ]
            
            main_area = None
            for area_selector in main_product_areas:
                main_area = soup.select_one(area_selector)
                if main_area:
                    break
            
            if main_area:
                # Look for prices only within the main product area
                price_selectors = [
                    '.woocommerce-Price-amount bdi',
                    '.woocommerce-Price-amount',
                    '.price .amount',
                    '.price bdi',
                    '.price'
                ]
                
                for selector in price_selectors:
                    elements = main_area.select(selector)
                    for element in elements:
                        # Skip if element is part of related products or sidebars
                        element_text = element.get_text(strip=True)
                        if 'KSh' in element_text or 'KES' in element_text:
                            # Clean and extract price
                            cleaned_text = element_text.replace('KSh', '').replace('KES', '').replace(',', '').strip()
                            numbers = re.findall(r'\d+(?:\.\d+)?', cleaned_text)
                            if numbers:
                                try:
                                    price_value = float(numbers[0])
                                    if price_value > 0:
                                        # Only add if this looks like a main price (not related products)
                                        parent_context = element.get_text() if element.parent else ''
                                        if not any(skip in parent_context.lower() for skip in ['related', 'you may also', 'similar']):
                                            all_prices.append(price_value)
                                except ValueError:
                                    continue
        
        # Method 3: Fallback - broader search but filter out related products
        if not all_prices:
            fallback_selectors = [
                '.woocommerce-Price-amount bdi',
                '.woocommerce-Price-amount', 
                '.price .amount',
                '.price bdi',
                '.price'
            ]
            
            for selector in fallback_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Skip elements that are clearly from related products sections
                    ancestor_text = ''
                    current = element
                    for _ in range(5):  # Check up to 5 levels up
                        if current and current.parent:
                            current = current.parent
                            if current.get('class'):
                                ancestor_classes = ' '.join(current.get('class', []))
                                ancestor_text += ancestor_classes.lower() + ' '
                        else:
                            break
                    
                    # Skip if in related products, cart, or sidebar areas
                    if any(skip in ancestor_text for skip in ['related', 'upsell', 'cross-sell', 'cart', 'sidebar', 'widget']):
                        continue
                        
                    price_text = element.get_text(strip=True)
                    if 'KSh' in price_text or 'KES' in price_text:
                        cleaned_text = price_text.replace('KSh', '').replace('KES', '').replace(',', '').strip()
                        numbers = re.findall(r'\d+(?:\.\d+)?', cleaned_text)
                        if numbers:
                            try:
                                price_value = float(numbers[0])
                                if price_value > 0:
                                    all_prices.append(price_value)
                            except ValueError:
                                continue
        
        # Select the most appropriate price with improved logic
        if all_prices:
            # Remove obvious outliers (prices below 100 KES are likely errors)
            valid_prices = [p for p in all_prices if p > 100]
            
            if valid_prices:
                # Since we now prioritize structured data and main product area,
                # the first valid price found is usually the correct one
                if len(valid_prices) == 1:
                    selected_price = valid_prices[0]
                else:
                    # If multiple prices, prefer the first one found (from structured data or main area)
                    # But remove extreme outliers
                    price_range = max(valid_prices) - min(valid_prices)
                    if price_range > min(valid_prices) * 0.5:  # If range is > 50% of min price
                        # Remove extreme outliers and take first reasonable price
                        median_price = sorted(valid_prices)[len(valid_prices) // 2]
                        filtered_prices = [p for p in valid_prices if abs(p - median_price) < median_price * 0.3]
                        selected_price = filtered_prices[0] if filtered_prices else valid_prices[0]
                    else:
                        # Prices are close, take the first one
                        selected_price = valid_prices[0]
                
                product_data['price_kes'] = selected_price
                product_data['original_currency'] = 'KES'
                self.logger.info(f"Selected price: KES {selected_price} from {len(all_prices)} found prices")
        
        # Extract SKU - Polish Venture shows SKU in product meta
        sku_selectors = [
            '.sku',
            '.product_meta .sku',
            '[data-sku]',
            '.product-sku'
        ]
        
        for selector in sku_selectors:
            element = soup.select_one(selector)
            if element:
                sku = element.get_text(strip=True)
                if sku and sku != 'N/A':
                    # Clean up SKU by removing prefixes like "SKU:"
                    cleaned_sku = sku
                    for prefix in ['SKU:', 'SKU ', 'Product Code:', 'Code:']:
                        if cleaned_sku.startswith(prefix):
                            cleaned_sku = cleaned_sku[len(prefix):].strip()
                            break
                    product_data['sku'] = cleaned_sku
                    break
        
        # Extract brand - Look for "Battery Brand" or similar in Polish Venture
        brand_text = soup.get_text().lower()
        
        # Look for "Battery Brand Power zone" pattern
        import re
        brand_patterns = [
            r'battery brand[:\s]+([^\n\r]+)',
            r'brand[:\s]+([^\n\r]+)',
            r'manufacturer[:\s]+([^\n\r]+)'
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, brand_text, re.IGNORECASE)
            if matches:
                brand = matches[0].strip()
                if len(brand) < 50:  # Reasonable brand name length
                    product_data['brand'] = brand.title()
                    break
        
        # Extract category from breadcrumbs or page structure
        category_selectors = [
            '.breadcrumb a:last-of-type',
            '.category a',
            '.product-category',
            '[rel="tag"]'
        ]
        
        for selector in category_selectors:
            element = soup.select_one(selector)
            if element:
                category = element.get_text(strip=True)
                if category and category.lower() != 'home':
                    product_data['category'] = category
                    break
        
        # Default to 'Car Battery' if we found battery-related content
        if not product_data.get('category') and 'battery' in product_data.get('name', '').lower():
            product_data['category'] = 'Car Battery'
        
        # Extract stock status
        stock_selectors = [
            '.stock',
            '.in-stock',
            '.availability',
            '.stock-status'
        ]
        
        stock_text = soup.get_text().lower()
        if 'in stock' in stock_text:
            product_data['stock_status'] = 'In Stock'
        elif 'out of stock' in stock_text:
            product_data['stock_status'] = 'Out of Stock'
        
        # Extract description from Polish Venture structure
        desc_selectors = [
            '.woocommerce-product-details__short-description',
            '.product-description',
            '.entry-summary p',
            '.product-short-description',
            '.description'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                desc = element.get_text(strip=True)
                if desc and len(desc) > 20:
                    product_data['description'] = desc[:500]
                    break
        
        # Extract additional information from tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'battery brand' in key:
                        product_data['brand'] = value
                    elif 'oem' in key or 'part' in key:
                        product_data['part_number'] = value
                    elif key in ['sku', 'product code']:
                        product_data['sku'] = value
        
        # Extract images - Polish Venture uses WooCommerce gallery
        image_selectors = [
            '.woocommerce-product-gallery__image img',
            '.product-images img',
            '.wp-post-image',
            '.product-gallery img'
        ]
        
        images = []
        for selector in image_selectors:
            img_elements = soup.select(selector)
            for img in img_elements:
                src = img.get('src') or img.get('data-src') or img.get('data-large_image')
                if src and self._is_valid_image_url(src):
                    if not src.startswith('http'):
                        from urllib.parse import urljoin
                        src = urljoin(product_url, src)
                    images.append(src)
        
        if images:
            product_data['images'] = list(dict.fromkeys(images))  # Remove duplicates
            product_data['primary_image'] = images[0]
        
        return product_data


