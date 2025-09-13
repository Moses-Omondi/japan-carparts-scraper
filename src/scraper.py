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
        This is a generic implementation that would need to be customized
        for specific websites.
        
        Args:
            soup: BeautifulSoup object of the webpage
            base_url: Base URL for resolving relative links
            
        Returns:
            List of dictionaries containing part data
        """
        parts_data = []
        
        # Generic selectors - these would need to be customized for specific sites
        part_containers = soup.find_all(['div', 'article', 'section'], 
                                       class_=lambda x: x and any(keyword in x.lower() 
                                       for keyword in ['product', 'item', 'part', 'listing']))
        
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
            # Extract part name
            name_element = container.find(['h1', 'h2', 'h3', 'h4', 'span', 'p'], 
                                        class_=lambda x: x and any(keyword in x.lower() 
                                        for keyword in ['title', 'name', 'product']))
            name = name_element.get_text(strip=True) if name_element else None
            
            # Extract price in JPY
            price_element = container.find(['span', 'div', 'p'], 
                                         class_=lambda x: x and any(keyword in x.lower() 
                                         for keyword in ['price', 'cost', 'yen', 'jpy']))
            
            price_text = price_element.get_text(strip=True) if price_element else None
            price_jpy = self.extract_price_from_text(price_text)
            
            # Extract image URL
            img_element = container.find('img')
            image_url = None
            if img_element:
                image_src = img_element.get('src') or img_element.get('data-src')
                if image_src:
                    image_url = urljoin(base_url, image_src)
            
            # Extract part number/SKU
            part_number_element = container.find(['span', 'div', 'p'], 
                                                class_=lambda x: x and any(keyword in x.lower() 
                                                for keyword in ['sku', 'part', 'code', 'number']))
            part_number = part_number_element.get_text(strip=True) if part_number_element else None
            
            # Extract description
            desc_element = container.find(['p', 'div'], 
                                        class_=lambda x: x and any(keyword in x.lower() 
                                        for keyword in ['desc', 'detail', 'info']))
            description = desc_element.get_text(strip=True) if desc_element else None
            
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
        
        Args:
            price_text: Text containing price information
            
        Returns:
            Price as float or None if not found
        """
        if not price_text:
            return None
            
        import re
        
        # Remove common currency symbols and text
        cleaned_text = re.sub(r'[¥￥円税込税抜送料別送料込]', '', price_text)
        
        # Find numbers (including with commas)
        price_matches = re.findall(r'[\d,]+\.?\d*', cleaned_text)
        
        if price_matches:
            # Take the first number found and remove commas
            price_str = price_matches[0].replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                pass
                
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


# Example usage and site-specific scrapers would be added here
class YahooAuctionsScraper(CarPartsScraper):
    """Specialized scraper for Yahoo Auctions Japan car parts."""
    
    def extract_parts_data(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Override for Yahoo Auctions specific extraction."""
        # This would contain Yahoo Auctions specific selectors
        # Implementation would be added based on actual site structure
        return super().extract_parts_data(soup, base_url)


class UpgarageeScraper(CarPartsScraper):
    """Specialized scraper for UpGarage car parts."""
    
    def extract_parts_data(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Override for UpGarage specific extraction."""
        # This would contain UpGarage specific selectors
        # Implementation would be added based on actual site structure
        return super().extract_parts_data(soup, base_url)
