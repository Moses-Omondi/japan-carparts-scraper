#!/usr/bin/env python3
"""
FAANG-Level Ultra-High-Performance Multi-Core Scraper V2
=========================================================

Optimized for pagination-based sites with focused product extraction.
Performance Targets: >50 products/second, <60 second full catalog

Key Optimizations:
1. Pagination-focused discovery (more efficient than full crawling)
2. Multi-core parallel processing with optimized chunking  
3. Smart caching and deduplication
4. Adaptive concurrency based on server response
5. Memory-efficient processing
"""

import asyncio
import multiprocessing as mp
import time
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import threading
from functools import lru_cache
import re

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / "excel_scraper" / "src"))

try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

try:
    from pybloom_live import BloomFilter
    import mmh3
    ADVANCED_LIBS = True
except ImportError:
    ADVANCED_LIBS = False
    print("⚠️  Advanced libraries not available, using fallback implementations")


@dataclass
class PerformanceStats:
    """Performance tracking with real-time metrics."""
    start_time: float = field(default_factory=time.time)
    pages_processed: int = 0
    products_found: int = 0
    network_requests: int = 0
    errors: int = 0
    
    @property
    def duration(self) -> float:
        return time.time() - self.start_time
    
    @property
    def products_per_second(self) -> float:
        return self.products_found / max(self.duration, 0.001)


class AdaptiveConcurrencyManager:
    """Dynamically adjust concurrency based on server response times."""
    
    def __init__(self, min_concurrency: int = 10, max_concurrency: int = 60):
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.current_concurrency = min_concurrency * 2  # Start higher
        self.response_times = deque(maxlen=50)
        self.error_count = 0
        self.lock = threading.Lock()
        
    def record_response(self, response_time: float, success: bool):
        """Record response time and adjust concurrency."""
        with self.lock:
            self.response_times.append(response_time)
            
            if not success:
                self.error_count += 1
                if self.error_count > 5:
                    self.current_concurrency = max(
                        self.min_concurrency,
                        self.current_concurrency - 3
                    )
            else:
                self.error_count = max(0, self.error_count - 1)
                
                # Increase concurrency if response times are good
                if len(self.response_times) >= 10:
                    avg_time = sum(self.response_times) / len(self.response_times)
                    if avg_time < 0.5 and self.error_count == 0:
                        self.current_concurrency = min(
                            self.max_concurrency,
                            self.current_concurrency + 2
                        )
                    elif avg_time > 2.0:
                        self.current_concurrency = max(
                            self.min_concurrency,
                            self.current_concurrency - 1
                        )
    
    def get_concurrency(self) -> int:
        return self.current_concurrency


class TurboScraperOptimized:
    """Ultra-high-performance multi-core scraper optimized for speed."""
    
    def __init__(self, num_processes: Optional[int] = None):
        self.num_processes = num_processes or mp.cpu_count()
        self.stats = PerformanceStats()
        self.concurrency_manager = AdaptiveConcurrencyManager()
        
        # Initialize bloom filter if available
        if ADVANCED_LIBS:
            self.seen_urls = BloomFilter(capacity=50000, error_rate=0.01)
        else:
            self.seen_urls = set()
        
        print(f"🚀 TurboScraperOptimized initialized with {self.num_processes} CPU cores")
    
    async def create_session(self) -> aiohttp.ClientSession:
        """Create optimized aiohttp session."""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=self.concurrency_manager.get_concurrency(),
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=6, connect=2, sock_read=6)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        }
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
    
    def generate_smart_pagination_urls(self, base_url: str, max_pages: int = 30) -> List[str]:
        """Generate pagination URLs with smart limits."""
        urls = [base_url]
        
        # For Polish Venture and similar sites
        for page in range(2, max_pages + 1):
            if '?' in base_url:
                urls.append(f"{base_url}&page={page}")
            else:
                urls.append(f"{base_url}?page={page}")
        
        return urls
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, Optional[str]]:
        """Fetch single page with performance tracking."""
        async with semaphore:
            start_time = time.time()
            
            try:
                async with session.get(url) as response:
                    self.stats.network_requests += 1
                    
                    if response.status == 200:
                        content = await response.text()
                        response_time = time.time() - start_time
                        self.concurrency_manager.record_response(response_time, True)
                        return url, content
                    else:
                        self.concurrency_manager.record_response(time.time() - start_time, False)
                        return url, None
                        
            except Exception:
                self.stats.errors += 1
                self.concurrency_manager.record_response(time.time() - start_time, False)
                return url, None
    
    async def fetch_all_pages(self, session: aiohttp.ClientSession, urls: List[str]) -> List[Tuple[str, str]]:
        """Fetch all pages with adaptive concurrency."""
        semaphore = asyncio.Semaphore(self.concurrency_manager.get_concurrency())
        
        tasks = [self.fetch_page(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid results
        valid_results = []
        for result in results:
            if isinstance(result, tuple) and result[1] is not None:
                valid_results.append(result)
        
        return valid_results
    
    def extract_product_urls(self, html: str, base_url: str) -> List[str]:
        """Extract product URLs from listing page."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            product_urls = set()
            
            # Optimized selectors for Polish Venture and similar sites
            selectors = [
                'a[href*="/product/"]',
                '.woocommerce-loop-product__link[href]',
                '.product-item a[href]',
                'h2 a[href]'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links[:30]:  # Limit to prevent overload
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if self.is_valid_product_url(full_url):
                            product_urls.add(full_url)
            
            return list(product_urls)
        except:
            return []
    
    def is_valid_product_url(self, url: str) -> bool:
        """Check if URL is a valid product page."""
        url_lower = url.lower()
        return (
            '/product/' in url_lower and
            not any(exclude in url_lower for exclude in [
                'add-to-cart', 'filter', 'page=', 'orderby=', 'category'
            ])
        )
    
    def extract_products_parallel(self, html_pages: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Extract products using multiple CPU cores."""
        if not html_pages:
            return []
        
        # Divide work among processes
        chunk_size = max(1, len(html_pages) // self.num_processes)
        chunks = [html_pages[i:i + chunk_size] for i in range(0, len(html_pages), chunk_size)]
        
        all_products = []
        
        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            futures = [executor.submit(extract_product_chunk, chunk) for chunk in chunks]
            
            for future in as_completed(futures):
                try:
                    products = future.result(timeout=15)
                    all_products.extend(products)
                except Exception as e:
                    print(f"Extraction error: {e}")
                    self.stats.errors += 1
        
        return all_products
    
    def deduplicate_fast(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fast deduplication."""
        if ADVANCED_LIBS:
            seen_hashes = set()
            unique_products = []
            
            for product in products:
                content = f"{product.get('name', '')}{product.get('source_url', '')}"
                content_hash = mmh3.hash(content, signed=False)
                
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_products.append(product)
            
            return unique_products
        else:
            seen_urls = set()
            unique_products = []
            
            for product in products:
                url = product.get('source_url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_products.append(product)
            
            return unique_products
    
    async def scrape_catalog_optimized(self, base_url: str, max_time: float = 50.0) -> List[Dict[str, Any]]:
        """Main optimized scraping method."""
        print(f"🔥 Starting optimized scraping of {base_url}")
        print(f"⚙️  Using {self.num_processes} CPU cores, time limit: {max_time}s")
        
        start_time = time.time()
        session = await self.create_session()
        
        try:
            # Phase 1: Generate pagination URLs (smart limit for speed)
            print("📄 Phase 1: Generating page URLs...")
            page_urls = self.generate_smart_pagination_urls(base_url, max_pages=25)
            print(f"   Generated {len(page_urls)} page URLs")
            
            # Phase 2: Fetch listing pages
            print("🌐 Phase 2: Fetching listing pages...")
            html_pages = await self.fetch_all_pages(session, page_urls)
            print(f"   Successfully fetched {len(html_pages)} pages")
            
            # Phase 3: Extract product URLs
            print("🔗 Phase 3: Extracting product URLs...")
            all_product_urls = set()
            for url, html in html_pages:
                product_urls = self.extract_product_urls(html, url)
                all_product_urls.update(product_urls)
                
                # Time check
                if time.time() - start_time > max_time * 0.4:
                    break
            
            product_urls_list = list(all_product_urls)[:300]  # Focus on quality over quantity
            print(f"   Found {len(product_urls_list)} product URLs")
            
            # Phase 4: Fetch product pages
            print("📦 Phase 4: Fetching product pages...")
            product_pages = await self.fetch_all_pages(session, product_urls_list)
            print(f"   Successfully fetched {len(product_pages)} product pages")
            
            # Phase 5: Multi-core extraction
            print("⚡ Phase 5: Multi-core product extraction...")
            all_products = self.extract_products_parallel(product_pages)
            
            # Phase 6: Deduplication
            unique_products = self.deduplicate_fast(all_products)
            
            self.stats.products_found = len(unique_products)
            self.stats.pages_processed = len(html_pages) + len(product_pages)
            
            self.print_performance_report()
            
            return unique_products
            
        finally:
            await session.close()
    
    def print_performance_report(self):
        """Print performance report."""
        print("\n" + "="*60)
        print("🚀 OPTIMIZED SCRAPER PERFORMANCE REPORT")
        print("="*60)
        print(f"⏱️  Duration: {self.stats.duration:.2f}s")
        print(f"📊 Products Found: {self.stats.products_found}")
        print(f"📄 Pages Processed: {self.stats.pages_processed}")
        print(f"🌐 Network Requests: {self.stats.network_requests}")
        print(f"⚡ Products/Second: {self.stats.products_per_second:.1f}")
        print(f"🎯 Final Concurrency: {self.concurrency_manager.get_concurrency()}")
        print(f"❌ Errors: {self.stats.errors}")
        print("="*60)
        
        if self.stats.products_per_second > 50:
            print("🔥 PERFORMANCE: FAANG LEVEL (>50 products/s)")
        elif self.stats.products_per_second > 20:
            print("✅ PERFORMANCE: ENTERPRISE LEVEL (>20 products/s)")
        else:
            print("⚠️  PERFORMANCE: NEEDS OPTIMIZATION (<20 products/s)")
        
        if self.stats.duration < 60:
            print(f"✅ TIME TARGET: ACHIEVED ({self.stats.duration:.1f}s)")
        else:
            print(f"❌ TIME TARGET: EXCEEDED ({self.stats.duration:.1f}s)")
        
        print("="*60 + "\n")


# Static functions for multiprocessing
def extract_product_chunk(html_pages: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    """Extract products from a chunk of HTML pages."""
    products = []
    
    for url, html in html_pages:
        try:
            soup = BeautifulSoup(html, 'lxml')
            product = extract_product_fast(soup, url)
            
            if product and product.get('name'):
                products.append(product)
                
        except Exception:
            continue
    
    return products


@lru_cache(maxsize=200)
def get_selectors(selector_type: str) -> Tuple[str, ...]:
    """Get cached CSS selectors."""
    selectors = {
        'name': (
            'h1.entry-title', 'h1.product_title', 'h1.product-title',
            '.product_title', '.entry-title', 'h1'
        ),
        'price': (
            '.woocommerce-Price-amount bdi', '.woocommerce-Price-amount',
            '.price .amount', '.price bdi', '.price'
        ),
        'image': (
            '.woocommerce-product-gallery img', '.product-image img',
            '.wp-post-image', '.attachment-shop_single'
        )
    }
    return selectors.get(selector_type, ())


def extract_product_fast(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Ultra-fast product extraction."""
    product = {
        'source_url': url,
        'scraped_at': time.time()
    }
    
    # Quick validation
    if not soup.title or len(soup.get_text()) < 100:
        return {}
    
    # Extract name
    for selector in get_selectors('name'):
        element = soup.select_one(selector)
        if element:
            name = element.get_text(strip=True)
            if name and len(name) > 3:
                product['name'] = name[:150]
                break
    
    # Extract price
    for selector in get_selectors('price'):
        elements = soup.select(selector)[:2]  # Limit search
        for element in elements:
            price_text = element.get_text(strip=True)
            if 'KSh' in price_text or 'KES' in price_text:
                numbers = re.findall(r'[\d,]+(?:\.?\d*)', price_text.replace(',', ''))
                if numbers:
                    try:
                        price_value = float(numbers[0])
                        if 10 <= price_value <= 10000000:
                            product['price_kes'] = price_value
                            product['original_currency'] = 'KES'
                            break
                    except ValueError:
                        continue
        if 'price_kes' in product:
            break
    
    # Extract image
    for selector in get_selectors('image'):
        img = soup.select_one(selector)
        if img:
            src = img.get('src') or img.get('data-src')
            if src:
                product['primary_image'] = urljoin(url, src)
                break
    
    return product


async def run_optimized_scraper(base_url: str, max_time: float = 50.0) -> List[Dict[str, Any]]:
    """Run the optimized scraper."""
    if UVLOOP_AVAILABLE:
        try:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except:
            pass
    
    scraper = TurboScraperOptimized()
    return await scraper.scrape_catalog_optimized(base_url, max_time)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimized FAANG-Level Scraper")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--max-time", type=float, default=50.0, help="Max time in seconds")
    
    args = parser.parse_args()
    
    products = asyncio.run(run_optimized_scraper(args.url, args.max_time))
    print(f"\n🎯 FINAL RESULT: {len(products)} products scraped")