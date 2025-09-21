import json
from typing import Any, Optional


class Config:
    """High-performance configuration for sub-50 second scraping."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = {
            # High-performance settings
            'max_concurrent_requests': 30,  # Increased from 8 to 30
            'max_concurrent_products': 25,   # New: concurrent product detail requests
            'request_delay': 0.1,           # Reduced from 0.3 to 0.1 seconds
            'product_request_delay': 0.05,  # Very short delay for product details
            'timeout': 15,                  # Reduced timeout for faster failures
            'max_products_per_page': 50,
            'max_pages': 999,  # For full catalog scraping
            'output_dir': 'output',
            'file_prefix': 'scraped_products',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Connection optimization
            'connection_limit': 100,        # Total connection pool size
            'connection_limit_per_host': 30, # Per-host connection limit
            'keepalive_timeout': 30,        # Keep connections alive longer
            
            # Parsing optimization
            'use_lxml': True,              # Use fast lxml parser
            'extract_images': True,        # Set to False to skip image extraction for speed
            'extract_descriptions': True,  # Set to False to skip descriptions for speed
            
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
