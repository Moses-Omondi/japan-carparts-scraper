import json
from typing import Any, Optional


class Config:
    """Minimal configuration for the scraper."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = {
            'max_concurrent_requests': 8,
            'request_delay': 0.3, 
            'timeout': 20,
            'max_products_per_page': 50,
            'max_pages': 999,  # For full catalog scraping
            'output_dir': 'output',
            'file_prefix': 'scraped_products',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'polish_venture': {
                'product_selectors': ['.product-item', '.product', '.woocommerce-loop-product__link']
            }
        }
        
        if config_path:
            try:
                with open(config_path) as f:
                    self.config.update(json.load(f))
            except:
                pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value with dot notation support."""
        value = self.config
        for k in key.split('.'):
            try:
                value = value[k]
            except (KeyError, TypeError):
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set config value."""
        self.config[key] = value
