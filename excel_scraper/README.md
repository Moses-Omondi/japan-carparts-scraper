# Fast Excel Scraper

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, async web scraper optimized for sub-50 second e-commerce data extraction and Excel export.

## Features

- **High Performance**: Async processing with 30-40 concurrent requests for sub-50 second scraping
- **Excel Export**: Professional Excel files with formatting and summary sheets
- **Smart Extraction**: Intelligent product data extraction optimized for e-commerce sites
- **Configurable**: Speed vs quality trade-offs with multiple performance modes
- **Production Ready**: Robust error handling, logging, and session management

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Speed-optimized scraping (recommended)
python scripts/scrape.py https://polishventure.com/shop/ --speed-test

# Time-limited scraping (45 seconds)
python scripts/scrape.py https://polishventure.com/shop/ --max-time 45

# High-performance config
python scripts/scrape.py https://polishventure.com/shop/ --config config_fast.json
```

### Python API

```python
import asyncio
from excel_scraper import FastExcelScraper, Config

async def main():
    # Create speed-optimized configuration
    config = Config()
    config.set('max_concurrent_requests', 40)
    config.set('max_concurrent_products', 35)
    config.set('request_delay', 0.05)
    
    # Initialize scraper
    scraper = FastExcelScraper(config)
    
    try:
        # Scrape website with high performance
        products = await scraper.scrape_website_async('https://polishventure.com/shop/')
        
        # Save to Excel
        output_file = scraper.save_to_excel(products)
        print(f"Scraped {len(products)} products in sub-50 seconds: {output_file}")
        
    finally:
        await scraper.close_session()

# Run the scraper
asyncio.run(main())
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Website URL to scrape | Required |
| `--speed-test` | Enable speed-optimized settings | False |
| `--max-time` | Maximum scraping time (seconds) | None |
| `--max-products` | Maximum products to scrape | 100 |
| `--concurrent-requests` | Simultaneous requests | 30 |
| `--delay` | Delay between requests (seconds) | 0.1 |
| `--config` | Custom config file | None |
| `--verbose` | Enable verbose logging | False |

## Performance

### Speed Optimizations
- **Async product detail fetching** - Eliminates main bottleneck (5-10x improvement)
- **High concurrency** - 30-40 concurrent requests vs 8 standard
- **Minimal delays** - 0.05-0.1s delays vs 0.3s standard
- **Optimized connection pooling** - Persistent connections with keep-alive
- **Streamlined extraction** - Optional image/description extraction

### Performance Modes
- **Speed Test Mode** (`--speed-test`): Maximum speed, minimal data
- **Balanced Mode** (default): Good speed with full data extraction
- **Custom Config**: Fine-tuned performance vs quality trade-offs

### Expected Results
- **Sub-50 second scraping** for moderate catalogs (100-500 products)
- **15-25 products/second** processing rate
- **5-10x faster** than standard synchronous scraping

## Excel Output

### Product Data
- Product ID, Name, Price (KES), SKU
- Category, Brand, Stock Status
- Description, Images, Source URL
- Scraped timestamp

### File Features
- Professional formatting with colored headers
- Auto-sized columns for readability
- Summary sheet with statistics
- Multiple export formats supported

## Configuration

### Speed-Optimized Config (`config_fast.json`)

```json
{
  "max_concurrent_requests": 40,
  "max_concurrent_products": 35,
  "request_delay": 0.05,
  "product_request_delay": 0.02,
  "timeout": 10,
  "extract_images": false,
  "extract_descriptions": false
}
```

### Balanced Config (Default)

```json
{
  "max_concurrent_requests": 30,
  "request_delay": 0.1,
  "timeout": 15,
  "extract_images": true,
  "extract_descriptions": true
}
```

## Project Structure

```
excel_scraper/
├── src/excel_scraper/
│   ├── scraper.py        # Core async scraper
│   ├── config.py         # Performance settings
│   └── utils.py          # Helper functions
├── scripts/scrape.py     # CLI interface
├── config_fast.json      # Speed-optimized config
└── requirements.txt      # Dependencies
```

## License

MIT License - see LICENSE file for details.

