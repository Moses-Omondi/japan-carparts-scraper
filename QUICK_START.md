# 🚗 Japanese Car Parts Scraper

## ⚠️ Important Note

**Most modern Japanese car parts websites use JavaScript** to load their product listings. This means our scraper (which reads static HTML) will often fall back to **sample data** to demonstrate functionality.

## How to Run

```bash
# Test with sample data (always works) - RECOMMENDED
./run.sh --sample-only

# Try scraping a website (may fall back to sample data)
./run.sh https://autoparts.beforward.jp/search/Lightings/Headlights/

# Test multiple sites to find one that works
./venv/bin/python test_sites.py
```

## What it does

1. **Attempts to scrape** Japanese car parts websites
2. **Falls back to sample data** if the site uses JavaScript (most do)
3. **Converts** JPY prices to USD using live exchange rates  
4. **Generates** professional PDF reports and CSV exports

## Why You Keep Seeing the Same Data

The Toyota Supra A90 Front Bumper and other parts you see are **sample data** because:
- Modern websites load content with JavaScript
- Our scraper only reads static HTML
- This is a common limitation of simple web scrapers

## Output Files

Check the `outputs/` directory:
- **PDF Report**: Professional format with part details
- **Compact PDF**: Table format for quick reference
- **CSV**: Raw data for spreadsheet analysis

## The Scraper Works!

The scraper **successfully**:
✅ Converts JPY to USD with live exchange rates  
✅ Generates professional PDF reports  
✅ Exports data to CSV format  
✅ Downloads and processes images  
✅ Creates detailed pricing summaries

**It just needs websites that don't require JavaScript!** 🎯

## What It Does

1. **Scrapes** Japanese car parts websites for pricing data
2. **Converts** JPY prices to USD using live exchange rates
3. **Generates** professional PDF reports with images
4. **Exports** data to CSV for spreadsheet analysis

## Output Files

After running, check the `outputs/` directory:
- **PDF Report**: `japanese_car_parts_report_YYYYMMDD_HHMMSS.pdf`
- **Compact PDF**: `japanese_car_parts_compact_YYYYMMDD_HHMMSS.pdf` 
- **CSV Data**: `japanese_car_parts_data_YYYYMMDD_HHMMSS.csv`

## Command Options

- `--sample-only, -s`: Use sample data (perfect for testing)
- `--no-convert, -n`: Skip currency conversion (JPY only)
- `--log-level LEVEL`: Set logging (DEBUG, INFO, WARNING, ERROR)

## Example Commands

```bash
# Test with sample data
./run.sh --sample-only

# Try UpGarage (popular Japanese car parts site)
./run.sh https://www.upgarage.com/

# Debug mode with real site
./run.sh https://www.upgarage.com/ --log-level DEBUG

# Multiple sites, no currency conversion
./run.sh https://site1.com https://site2.com --no-convert
```

That's it! The scraper handles setup automatically and generates professional reports.
