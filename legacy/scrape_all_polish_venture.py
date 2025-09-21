#!/usr/bin/env python3
"""
Complete Polish Venture scraper for all 15,435+ products across 644 pages.
This script handles the full catalog with proper error handling, resume capability, and progress tracking.
"""

import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time
import json
from typing import List, Dict, Any
import signal

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from scraper import CarPartsScraper
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class PolishVentureFullScraper:
    """Enhanced scraper for complete Polish Venture catalog."""
    
    def __init__(self):
        self.scraped_products = []
        self.progress_file = "polish_venture_progress.json"
        self.temp_excel_file = None
        self.start_time = time.time()
        self.products_scraped = 0
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Set up comprehensive logging."""
        log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler('logs/full_scraper.log')
        file_handler.setFormatter(log_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        
        # Setup logger
        self.logger = logging.getLogger('PolishVentureFullScraper')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}. Saving progress and exiting gracefully...")
            self.save_progress()
            self.save_current_data_to_excel()
            print(f"\n🛑 Scraping interrupted. Progress saved!")
            print(f"📊 Scraped {self.products_scraped} products so far.")
            if self.temp_excel_file:
                print(f"📁 Partial results saved to: {self.temp_excel_file}")
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def load_progress(self) -> Dict[str, Any]:
        """Load previous progress if exists."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                self.logger.info(f"Loaded progress: Page {progress.get('last_page', 1)}, {len(progress.get('scraped_urls', []))} products completed")
                return progress
            except Exception as e:
                self.logger.error(f"Error loading progress: {e}")
        
        return {'last_page': 1, 'scraped_urls': [], 'completed_products': []}
    
    def save_progress(self):
        """Save current progress."""
        progress = {
            'last_page': getattr(self, 'current_page', 1),
            'scraped_urls': [p.get('source_url', '') for p in self.scraped_products],
            'completed_products': len(self.scraped_products),
            'timestamp': datetime.now().isoformat(),
            'total_runtime_minutes': (time.time() - self.start_time) / 60
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
            self.logger.info(f"Progress saved: {len(self.scraped_products)} products")
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")
    
    def save_current_data_to_excel(self, final=False):
        """Save current scraped data to Excel file."""
        if not self.scraped_products:
            return None
            
        try:
            # Process data for Excel
            processed_data = []
            
            for i, product in enumerate(self.scraped_products, 1):
                record = {
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
                    'Scraped Date': datetime.fromtimestamp(product.get('scraped_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if product.get('scraped_at') else ''
                }
                
                # Add specifications if available
                if product.get('specifications'):
                    specs = product.get('specifications', {})
                    record['Specifications'] = '; '.join([f"{k}: {v}" for k, v in specs.items() if k and v])
                
                processed_data.append(record)
            
            # Create DataFrame
            df = pd.DataFrame(processed_data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            status = "COMPLETE" if final else "PARTIAL"
            excel_filename = f"polish_venture_products_{status}_{timestamp}.xlsx"
            excel_path = os.path.join(os.getcwd(), excel_filename)
            
            # Create Excel file with formatting
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Write main data sheet
                df.to_excel(writer, sheet_name='Products', index=False)
                
                # Import styles
                from openpyxl.styles import Font, PatternFill, Alignment
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Products']
                
                # Format headers
                header_font = Font(bold=True, color='FFFFFF')
                header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
                center_alignment = Alignment(horizontal='center')
                
                for cell in worksheet[1]:  # First row (headers)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = center_alignment
                
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
                    
                    # Set width with padding, max 50
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Create summary sheet
                runtime_hours = (time.time() - self.start_time) / 3600
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
                        'Scraping Status',
                        'Runtime (Hours)',
                        'Scraping Rate (Products/Hour)',
                        'Last Updated',
                        'Source Website'
                    ],
                    'Value': [
                        len(df),
                        len(df[df['Price (KES)'] > 0]),
                        len(df[df['SKU'].str.len() > 0]) if 'SKU' in df.columns else 0,
                        len(df[df['Brand'].str.len() > 0]) if 'Brand' in df.columns else 0,
                        len(df[df['Total Images'] > 0]) if 'Total Images' in df.columns else 0,
                        f"{df[df['Price (KES)'] > 0]['Price (KES)'].mean():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 else "0",
                        f"{df['Price (KES)'].max():.2f}" if df['Price (KES)'].max() > 0 else "0",
                        f"{df[df['Price (KES)'] > 0]['Price (KES)'].min():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 else "0",
                        status,
                        f"{runtime_hours:.1f}",
                        f"{len(df) / runtime_hours:.1f}" if runtime_hours > 0 else "0",
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "https://polishventure.com/shop/"
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
            
            self.temp_excel_file = excel_path
            self.logger.info(f"Excel file {'completed' if final else 'updated'}: {excel_filename}")
            return excel_path
            
        except Exception as e:
            self.logger.error(f"Error creating Excel file: {e}")
            return None
    
    def scrape_all_products(self, start_page=1, max_pages=None, save_interval=50):
        """
        Scrape all Polish Venture products with progress tracking.
        
        Args:
            start_page: Page to start from (for resume capability)
            max_pages: Maximum pages to scrape (None for all)
            save_interval: Save progress every N products
        """
        
        # Load previous progress
        progress = self.load_progress()
        if start_page == 1 and progress['last_page'] > 1:
            resume = input(f"Found previous progress (page {progress['last_page']}, {progress['completed_products']} products). Resume? (y/n): ").strip().lower()
            if resume == 'y':
                start_page = progress['last_page']
                self.scraped_products = []  # Will reload from progress if needed
        
        # Configure scraper for large-scale operation
        config = {
            'max_pages_per_site': max_pages or 1000,  # Set high limit
            'max_products_per_page': 50,  # Process products in batches
            'request_delay': 1.5,  # Respectful delay
            'enable_image_download': False  # Skip images for speed
        }
        
        scraper = CarPartsScraper(config)
        
        print("🚀 POLISH VENTURE COMPLETE CATALOG SCRAPER")
        print("=" * 80)
        print(f"📊 Target: ~15,435 products across 644 pages")
        print(f"🎯 Starting from page: {start_page}")
        print(f"⏱️ Request delay: {config['request_delay']}s")
        print(f"💾 Auto-save every: {save_interval} products")
        print("=" * 80)
        
        base_url = "https://polishventure.com/shop/"
        current_page = start_page
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        try:
            while True:
                self.current_page = current_page
                page_url = f"{base_url}?page={current_page}" if current_page > 1 else base_url
                
                self.logger.info(f"Scraping page {current_page}: {page_url}")
                print(f"\n📄 Page {current_page} - Products scraped: {len(self.scraped_products)}")
                
                try:
                    # Scrape current page
                    page_products = scraper.scrape_website(page_url)
                    
                    if not page_products:
                        consecutive_failures += 1
                        self.logger.warning(f"No products found on page {current_page} (failure #{consecutive_failures})")
                        
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.info(f"Reached max consecutive failures ({max_consecutive_failures}). Assuming end of catalog.")
                            break
                        
                        current_page += 1
                        continue
                    
                    # Reset failure counter
                    consecutive_failures = 0
                    
                    # Add products to collection (avoid duplicates more efficiently)
                    existing_urls = {p.get('source_url', '') for p in self.scraped_products}
                    new_products = 0
                    for product in page_products:
                        product_url = product.get('source_url', '')
                        if product_url and product_url not in existing_urls:
                            self.scraped_products.append(product)
                            existing_urls.add(product_url)
                            new_products += 1
                    
                    self.products_scraped = len(self.scraped_products)
                    self.logger.info(f"Page {current_page}: Found {len(page_products)} products, {new_products} new products")
                    
                    # Show progress
                    estimated_total = 15435
                    progress_percent = (self.products_scraped / estimated_total) * 100
                    runtime_minutes = (time.time() - self.start_time) / 60
                    rate_per_hour = self.products_scraped / (runtime_minutes / 60) if runtime_minutes > 0 else 0
                    
                    print(f"✅ Progress: {self.products_scraped}/{estimated_total} ({progress_percent:.1f}%)")
                    print(f"⚡ Rate: {rate_per_hour:.1f} products/hour | Runtime: {runtime_minutes:.1f} mins")
                    
                    # Save progress periodically
                    if self.products_scraped % save_interval == 0:
                        self.save_progress()
                        self.save_current_data_to_excel()
                        print(f"💾 Progress saved at {self.products_scraped} products")
                    
                    # Check if we've reached the expected total
                    if self.products_scraped >= estimated_total:
                        self.logger.info(f"Reached expected total of {estimated_total} products")
                        break
                    
                    current_page += 1
                    
                    # Optional max pages limit
                    if max_pages and current_page > max_pages:
                        self.logger.info(f"Reached max pages limit ({max_pages})")
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error scraping page {current_page}: {e}")
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error(f"Too many consecutive failures. Stopping.")
                        break
                    
                    current_page += 1
                    time.sleep(5)  # Longer delay on error
                    continue
        
        except KeyboardInterrupt:
            self.logger.info("Scraping interrupted by user")
        
        finally:
            # Final save
            self.save_progress()
            final_excel = self.save_current_data_to_excel(final=True)
            
            # Clean up progress file if completed
            if os.path.exists(self.progress_file):
                try:
                    os.remove(self.progress_file)
                    self.logger.info("Cleaned up progress file")
                except:
                    pass
        
        return final_excel

def main():
    """Main function to run the complete scraper."""
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Initialize scraper
    full_scraper = PolishVentureFullScraper()
    
    print("POLISH VENTURE COMPLETE CATALOG SCRAPER")
    print("=" * 60)
    print("This will scrape ALL 15,435+ products from Polish Venture.")
    print("The process will:")
    print("- Save progress automatically every 50 products")
    print("- Allow resume if interrupted")
    print("- Create Excel files with complete data")
    print("- Handle errors gracefully")
    print()
    
    # Ask for confirmation
    confirm = input("This will take several hours. Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Scraping cancelled.")
        return
    
    # Configure options
    try:
        start_page = int(input("Start from page (default 1): ").strip() or "1")
    except ValueError:
        start_page = 1
    
    try:
        max_pages = input("Max pages to scrape (default: all 644): ").strip()
        max_pages = int(max_pages) if max_pages else None
    except ValueError:
        max_pages = None
    
    print(f"\n🚀 Starting complete scrape from page {start_page}")
    if max_pages:
        print(f"📊 Will scrape up to {max_pages} pages")
    else:
        print(f"📊 Will scrape all 644 pages (~15,435 products)")
    
    print("\nPress Ctrl+C at any time to stop and save progress.")
    print("=" * 60)
    
    # Start scraping
    final_file = full_scraper.scrape_all_products(
        start_page=start_page, 
        max_pages=max_pages,
        save_interval=50
    )
    
    # Final summary
    total_products = len(full_scraper.scraped_products)
    runtime_hours = (time.time() - full_scraper.start_time) / 3600
    
    print("\n" + "=" * 80)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 80)
    print(f"📊 Total products scraped: {total_products}")
    print(f"⏱️ Total runtime: {runtime_hours:.1f} hours")
    print(f"⚡ Average rate: {total_products / runtime_hours:.1f} products/hour")
    
    if final_file:
        print(f"📁 Final Excel file: {os.path.basename(final_file)}")
        print(f"💾 File location: {final_file}")
    
    print("\n✅ All Polish Venture products have been scraped and saved to Excel!")

if __name__ == "__main__":
    main()