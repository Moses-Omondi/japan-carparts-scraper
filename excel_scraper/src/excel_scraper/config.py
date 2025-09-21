"""
Configuration management for the Excel Scraper.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration management for the scraper."""
    
    DEFAULT_CONFIG = {
        # Performance settings
        'max_concurrent_requests': 8,
        'request_delay': 0.3,
        'timeout': 20,
        'retry_attempts': 2,
        
        # Scraping limits
        'max_products_per_page': 50,
        'max_pages': 20,
        
        # Output settings
        'output_dir': 'output',
        'file_prefix': 'scraped_products',
        'timestamp_format': '%Y%m%d_%H%M%S',
        
        # Request settings
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        
        # Site-specific settings
        'polish_venture': {
            'base_url': 'https://polishventure.com/shop/',
            'product_selectors': [
                '.product-item', '.product', '.woocommerce-loop-product__link',
                '.product-small', '.box-image', '.col-inner'
            ]
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'polish_venture.base_url')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config.copy()
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config_path: Path to save configuration
        """
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)