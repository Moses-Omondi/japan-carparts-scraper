#!/usr/bin/env python3
"""
Scrape Polish Venture products and export to Excel file.
This script uses the improved price extraction to ensure accurate data.
"""

import sys
import os
import pandas as pd
from datetime import datetime
import logging

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from scraper import CarPartsScraper
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def setup_logging():
    """Set up logging for the scraping process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/excel_export.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def scrape_polish_venture_to_excel(max_products=50):
    """
    Scrape Polish Venture products and export to Excel.
    
    Args:
        max_products: Maximum number of products to scrape
    """
    
    logger = setup_logging()
    logger.info("Starting Polish Venture scraping for Excel export")
    
    # Configure scraper
    config = {
        'max_pages_per_site': 10,  # Scrape up to 10 pages
        'max_products_per_page': max_products,  # Limit total products
        'request_delay': 2,  # Be respectful with delays
        'enable_image_download': False  # Skip image download for faster scraping
    }
    
    scraper = CarPartsScraper(config)
    
    # Polish Venture shop URL
    shop_url = "https://polishventure.com/shop/"
    
    print("🚀 Starting Polish Venture scraping...")
    print("=" * 60)
    print(f"Target URL: {shop_url}")
    print(f"Max products: {max_products}")
    print(f"Request delay: {config['request_delay']}s")
    print("=" * 60)
    
    try:
        # Scrape the website
        logger.info(f"Scraping {shop_url}")
        products = scraper.scrape_website(shop_url)
        
        if not products:
            print("❌ No products found!")
            logger.error("No products scraped")
            return
        
        print(f"✅ Successfully scraped {len(products)} products!")
        logger.info(f"Scraped {len(products)} products successfully")
        
        # Process data for Excel
        processed_data = []
        
        for i, product in enumerate(products, 1):
            print(f"Processing product {i}/{len(products)}: {product.get('name', 'Unknown')[:50]}...")
            
            # Create clean record for Excel
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
                'Scraped Date': datetime.fromtimestamp(product.get('scraped_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if product.get('scraped_at') else '',
                'Has Warranty': product.get('has_warranty', False),
                'Has Shipping Info': product.get('has_shipping_info', False)
            }
            
            # Add pricing breakdown if available
            if product.get('price_jpy'):
                record['Price (JPY)'] = product.get('price_jpy', 0)
                record['Exchange Rate Used'] = product.get('exchange_rate', 0)
            
            # Add specifications if available
            if product.get('specifications'):
                specs = product.get('specifications', {})
                record['Specifications'] = '; '.join([f"{k}: {v}" for k, v in specs.items() if k and v])
            
            processed_data.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(processed_data)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f"polish_venture_products_{timestamp}.xlsx"
        excel_path = os.path.join(os.getcwd(), excel_filename)
        
        print(f"\n📊 Creating Excel file: {excel_filename}")
        logger.info(f"Creating Excel file: {excel_path}")
        
        # Create Excel file with formatting
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Write main data sheet
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # Get workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Products']
            
            # Import openpyxl styles
            from openpyxl.styles import Font, PatternFill
            
            # Format headers
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            
            for cell in worksheet[1]:  # First row (headers)
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
                    len(df[df['Price (KES)'] > 0]),
                    len(df[df['SKU'].str.len() > 0]),
                    len(df[df['Brand'].str.len() > 0]),
                    len(df[df['Total Images'] > 0]),
                    f"{df[df['Price (KES)'] > 0]['Price (KES)'].mean():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 else "0",
                    f"{df['Price (KES)'].max():.2f}" if df['Price (KES)'].max() > 0 else "0",
                    f"{df[df['Price (KES)'] > 0]['Price (KES)'].min():.2f}" if len(df[df['Price (KES)'] > 0]) > 0 else "0",
                    timestamp,
                    shop_url
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
        
        print(f"✅ Excel file created successfully!")
        print(f"📁 Location: {excel_path}")
        print(f"📊 Total products: {len(df)}")
        print(f"💰 Products with prices: {len(df[df['Price (KES)'] > 0])}")
        
        # Display sample data
        print(f"\n📋 Sample of scraped data:")
        print("-" * 80)
        sample_columns = ['Product Name', 'Price (KES)', 'SKU', 'Brand', 'Stock Status']
        print(df[sample_columns].head().to_string(index=False))
        
        logger.info(f"Successfully created Excel file with {len(df)} products")
        
        return excel_path
        
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        logger.error(f"Scraping failed: {e}")
        return None

def main():
    """Main function to run the scraping process."""
    
    print("POLISH VENTURE EXCEL EXPORTER")
    print("=" * 50)
    print("This script will scrape Polish Venture products and create an Excel file.")
    print("Using improved price extraction for accurate data.")
    print()
    
    # Get user input for number of products
    try:
        max_products = input("Enter maximum number of products to scrape (default: 25): ").strip()
        max_products = int(max_products) if max_products else 25
    except ValueError:
        max_products = 25
    
    print(f"Will scrape up to {max_products} products...")
    print()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run the scraping
    result = scrape_polish_venture_to_excel(max_products)
    
    if result:
        print(f"\n🎉 SUCCESS! Excel file created: {os.path.basename(result)}")
        print("You can now open this file in Excel, Google Sheets, or any spreadsheet application.")
    else:
        print("\n❌ FAILED! Check the logs for details.")

if __name__ == "__main__":
    main()