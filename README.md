# Japanese OEM Car Parts Scraper

A comprehensive Python script that scrapes Japanese OEM car parts websites, converts prices from JPY to USD, and generates professional PDF reports with images and pricing information.

## Features

- **Web Scraping**: Scrapes multiple Japanese car parts websites simultaneously
- **Currency Conversion**: Automatically converts JPY prices to USD using live exchange rates
- **Image Download**: Downloads and processes product images
- **PDF Generation**: Creates professional PDF reports with images, prices, and part details
- **Multiple Output Formats**: Supports PDF, compact PDF, and CSV exports
- **Configurable**: Highly customizable through JSON configuration
- **Rate Limiting**: Respectful scraping with configurable delays
- **Error Handling**: Robust error handling with fallback mechanisms
- **Logging**: Comprehensive logging with different levels

## Project Structure

```
japan-carparts-scraper/
├── src/                          # Source code
│   ├── scraper.py               # Web scraping functionality
│   ├── currency_converter.py    # Currency conversion logic
│   └── pdf_generator.py         # PDF and CSV report generation
├── data/                        # Scraped data storage
├── outputs/                     # Generated reports
├── images/                      # Downloaded product images
├── logs/                        # Log files
├── venv/                        # Virtual environment
├── main.py                      # Main execution script
├── config.json                  # Configuration settings
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd japan-carparts-scraper
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Verify dependencies are installed:**
   ```bash
   pip list
   ```

   If dependencies are missing, install them:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Basic Configuration

Edit `config.json` to customize the scraper behavior:

```json
{
  "target_urls": [
    "https://www.upgarage.com/search?q=部品",
    "https://auctions.yahoo.co.jp/category/list/2084007888/"
  ],
  "scraper_settings": {
    "request_delay": 2,
    "max_parts_per_site": 50
  },
  "output_formats": ["pdf", "compact_pdf", "csv"]
}
```

### Currency API Keys (Optional)

For better exchange rate accuracy, you can add API keys:

```json
{
  "currency_settings": {
    "fixer_api_key": "your_fixer_api_key_here",
    "exchangeratesapi_key": "your_exchangeratesapi_key_here"
  }
}
```

**Getting API Keys:**
- **Fixer.io**: Register at [fixer.io](https://fixer.io/) (free tier available)
- **ExchangeRatesAPI**: Register at [exchangeratesapi.io](https://exchangeratesapi.io/)

## Usage

### Basic Usage

Run the scraper with sample data for demonstration:

```bash
python main.py --sample-only
```

### Full Scraping

Run with actual website scraping:

```bash
python main.py
```

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  -c, --config PATH          Path to configuration file (default: config.json)
  -s, --sample-only          Skip scraping and use sample data only
  -n, --no-convert           Skip currency conversion
  -l, --log-level LEVEL      Set logging level (DEBUG, INFO, WARNING, ERROR)
  -o, --output-dir DIR       Output directory for generated files
  -h, --help                 Show help message
```

### Example Commands

```bash
# Use sample data with debug logging
python main.py --sample-only --log-level DEBUG

# Skip currency conversion (use JPY only)
python main.py --no-convert

# Use custom config file
python main.py --config my_config.json

# Generate reports in custom directory
python main.py --output-dir /path/to/custom/output
```

## Output Files

The scraper generates several types of output files:

### 1. PDF Report (`outputs/japanese_car_parts_report_YYYYMMDD_HHMMSS.pdf`)
- Professional format with cover page
- Individual part details with images
- Price summary statistics
- Exchange rate information

### 2. Compact PDF (`outputs/japanese_car_parts_compact_YYYYMMDD_HHMMSS.pdf`)
- Table format for quick overview
- All parts on fewer pages
- Ideal for reference

### 3. CSV Export (`outputs/japanese_car_parts_data_YYYYMMDD_HHMMSS.csv`)
- Raw data in spreadsheet format
- Easy to import into other tools
- Includes all scraped fields

### 4. Data Files (`data/`)
- `raw_scraped_data.json`: Original scraped data
- `exchange_rate_cache.json`: Cached exchange rates

## Configuration Options

### Scraper Settings

```json
{
  "scraper_settings": {
    "request_delay": 2,           // Seconds between requests
    "timeout": 30,                // Request timeout
    "max_retries": 3,             // Retry failed requests
    "max_parts_per_site": 50,     // Limit parts per website
    "user_agent": "...",          // Custom user agent
    "respect_robots_txt": true    // Follow robots.txt
  }
}
```

### Currency Settings

```json
{
  "currency_settings": {
    "cache_duration_hours": 1,      // Cache exchange rates
    "fallback_exchange_rate": 0.0067, // Backup rate if APIs fail
    "fixer_api_key": null,          // Fixer.io API key
    "exchangeratesapi_key": null    // ExchangeRatesAPI key
  }
}
```

### PDF Settings

```json
{
  "pdf_settings": {
    "include_images": true,       // Include product images
    "parts_per_page": 3,         // Parts per page in detailed PDF
    "page_size": "letter",       // Page size (letter/A4)
    "font_family": "Helvetica",  // Font family
    "title_color": "#1f4e79",   // Title color (hex)
    "price_color": "#d32f2f"    // Price color (hex)
  }
}
```

### Filtering Options

```json
{
  "filters": {
    "min_price_jpy": 1000,       // Minimum price filter
    "max_price_jpy": 1000000,    // Maximum price filter
    "exclude_keywords": ["replica", "copy"], // Skip parts with these words
    "include_only_oem": false    // Only include OEM parts
  }
}
```

## Website-Specific Configurations

The scraper supports site-specific selectors for better extraction:

```json
{
  "site_specific": {
    "upgarage": {
      "enabled": true,
      "selectors": {
        "product_container": ".product-item",
        "name": ".product-name",
        "price": ".price",
        "part_number": ".part-code",
        "image": ".product-image img"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Network/Scraping Issues**
   ```bash
   # Run with debug logging
   python main.py --log-level DEBUG
   
   # Use sample data to test other components
   python main.py --sample-only
   ```

3. **Currency Conversion Failures**
   ```bash
   # Skip currency conversion temporarily
   python main.py --no-convert
   
   # Check exchange rate APIs in logs
   python main.py --log-level DEBUG
   ```

4. **PDF Generation Issues**
   ```bash
   # Check if reportlab is properly installed
   pip show reportlab
   
   # Try generating with sample data
   python main.py --sample-only
   ```

### Log Files

Check log files in the `logs/` directory for detailed error information:

```bash
# View latest log file
tail -f logs/main_*.log

# Search for errors
grep ERROR logs/main_*.log
```

## Extending the Project

### Adding New Websites

1. Create a new scraper class in `src/scraper.py`:

```python
class NewSiteScraper(CarPartsScraper):
    def extract_parts_data(self, soup, base_url):
        # Custom extraction logic
        pass
```

2. Add site-specific configuration to `config.json`

3. Register the scraper in `main.py`

### Custom Output Formats

1. Add new methods to `PDFGenerator` class
2. Update configuration options
3. Modify `main.py` to handle new formats

## Legal and Ethical Considerations

- **Respect robots.txt**: The scraper respects robots.txt by default
- **Rate Limiting**: Built-in delays prevent server overload
- **Terms of Service**: Always check website terms before scraping
- **Data Usage**: Use scraped data responsibly and in compliance with laws

## Dependencies

Key Python packages used:

- **requests**: HTTP requests
- **beautifulsoup4**: HTML parsing
- **lxml**: Fast XML/HTML parser
- **selenium**: JavaScript-enabled scraping (optional)
- **reportlab**: PDF generation
- **Pillow**: Image processing
- **pandas**: Data manipulation

## Performance Tips

1. **Adjust request delays** based on website responsiveness
2. **Limit parts per site** for faster testing
3. **Disable image downloads** for faster scraping
4. **Use sample data** during development

## Version History

- **v1.0.0**: Initial release with basic scraping, currency conversion, and PDF generation

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review log files for error details
3. Verify configuration settings
4. Test with sample data first

## License

This project is for educational and research purposes. Please ensure compliance with website terms of service and applicable laws when using this scraper.

---

**Note**: This scraper is designed to work with Japanese car parts websites. The included URLs are examples and may need to be updated with actual working websites. Always verify that you have permission to scrape any website before use.
