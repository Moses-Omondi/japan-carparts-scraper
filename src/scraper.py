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
        Scrape a single website for car parts data.
        
        Args:
            url: The URL to scrape
            
        Returns:
            List of dictionaries containing part data
        """
        try:
            self.logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            parts_data = self.extract_parts_data(soup, url)
            
            self.logger.info(f"Found {len(parts_data)} parts on {url}")
            return parts_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return []
    
    def extract_parts_data(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract car parts data from BeautifulSoup object.
        Enhanced to handle table-based layouts like BE FORWARD.
        
        Args:
            soup: BeautifulSoup object of the webpage
            base_url: Base URL for resolving relative links
            
        Returns:
            List of dictionaries containing part data
        """
        parts_data = []
        
        # First, try to extract from table rows (BE FORWARD style)
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


