"""
Currency conversion module for converting JPY prices to USD.
Supports both API-based and manual exchange rate conversion.
"""

import requests
import logging
import time
import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta


class CurrencyConverter:
    """Currency converter class for JPY to USD conversion."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the currency converter."""
        self.config = config
        self.exchange_rate_cache = {}
        self.cache_expiry = {}
        self.logger = logging.getLogger(__name__)
        
        # Default fallback exchange rate (should be updated regularly)
        self.fallback_rate = 0.0067  # Approximate JPY to USD rate
        
        # Cache duration in hours
        self.cache_duration = config.get('cache_duration_hours', 1)
    
    def get_exchange_rate(self, from_currency: str = 'JPY', to_currency: str = 'USD') -> Optional[float]:
        """
        Get current exchange rate from JPY to USD.
        
        Args:
            from_currency: Source currency (default: JPY)
            to_currency: Target currency (default: USD)
            
        Returns:
            Exchange rate as float or None if failed
        """
        cache_key = f"{from_currency}_{to_currency}"
        
        # Check if we have cached rate that's still valid
        if self._is_cache_valid(cache_key):
            self.logger.info(f"Using cached exchange rate: {self.exchange_rate_cache[cache_key]}")
            return self.exchange_rate_cache[cache_key]
        
        # Try different API sources
        rate = self._get_rate_from_api(from_currency, to_currency)
        
        if rate:
            self._cache_rate(cache_key, rate)
            return rate
        
        # Fallback to default rate
        self.logger.warning(f"Using fallback exchange rate: {self.fallback_rate}")
        return self.fallback_rate
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached exchange rate is still valid."""
        if cache_key not in self.exchange_rate_cache:
            return False
            
        if cache_key not in self.cache_expiry:
            return False
            
        return datetime.now() < self.cache_expiry[cache_key]
    
    def _cache_rate(self, cache_key: str, rate: float):
        """Cache exchange rate with expiry time."""
        self.exchange_rate_cache[cache_key] = rate
        self.cache_expiry[cache_key] = datetime.now() + timedelta(hours=self.cache_duration)
        
        # Save to file cache
        self._save_cache_to_file()
    
    def _save_cache_to_file(self):
        """Save exchange rate cache to file."""
        try:
            os.makedirs('data', exist_ok=True)
            cache_data = {
                'rates': self.exchange_rate_cache,
                'expiry': {k: v.isoformat() for k, v in self.cache_expiry.items()}
            }
            
            with open('data/exchange_rate_cache.json', 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving cache to file: {e}")
    
    def _load_cache_from_file(self):
        """Load exchange rate cache from file."""
        try:
            if os.path.exists('data/exchange_rate_cache.json'):
                with open('data/exchange_rate_cache.json', 'r') as f:
                    cache_data = json.load(f)
                
                self.exchange_rate_cache = cache_data.get('rates', {})
                
                # Convert expiry strings back to datetime objects
                expiry_data = cache_data.get('expiry', {})
                self.cache_expiry = {
                    k: datetime.fromisoformat(v) for k, v in expiry_data.items()
                }
                
                self.logger.info("Loaded exchange rate cache from file")
                
        except Exception as e:
            self.logger.error(f"Error loading cache from file: {e}")
            self.exchange_rate_cache = {}
            self.cache_expiry = {}
    
    def _get_rate_from_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get exchange rate from various free APIs.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Exchange rate as float or None if all APIs fail
        """
        # Try exchangerate-api.com (free tier available)
        rate = self._get_rate_from_exchangerate_api(from_currency, to_currency)
        if rate:
            return rate
        
        # Try fixer.io as backup (requires API key)
        rate = self._get_rate_from_fixer(from_currency, to_currency)
        if rate:
            return rate
        
        # Try exchangeratesapi.io as another backup
        rate = self._get_rate_from_exchangeratesapi(from_currency, to_currency)
        if rate:
            return rate
        
        return None
    
    def _get_rate_from_exchangerate_api(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get rate from exchangerate-api.com (free tier)."""
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rate = data.get('rates', {}).get(to_currency)
            
            if rate:
                self.logger.info(f"Got exchange rate from exchangerate-api.com: 1 {from_currency} = {rate} {to_currency}")
                return float(rate)
                
        except Exception as e:
            self.logger.warning(f"Error getting rate from exchangerate-api.com: {e}")
        
        return None
    
    def _get_rate_from_fixer(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get rate from fixer.io (requires API key)."""
        api_key = self.config.get('fixer_api_key')
        if not api_key:
            return None
        
        try:
            url = f"http://data.fixer.io/api/latest"
            params = {
                'access_key': api_key,
                'base': from_currency,
                'symbols': to_currency
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                rate = data.get('rates', {}).get(to_currency)
                if rate:
                    self.logger.info(f"Got exchange rate from fixer.io: 1 {from_currency} = {rate} {to_currency}")
                    return float(rate)
                    
        except Exception as e:
            self.logger.warning(f"Error getting rate from fixer.io: {e}")
        
        return None
    
    def _get_rate_from_exchangeratesapi(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get rate from exchangeratesapi.io."""
        try:
            url = f"https://api.exchangeratesapi.io/v1/latest"
            params = {
                'base': from_currency,
                'symbols': to_currency
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                rate = data.get('rates', {}).get(to_currency)
                if rate:
                    self.logger.info(f"Got exchange rate from exchangeratesapi.io: 1 {from_currency} = {rate} {to_currency}")
                    return float(rate)
                    
        except Exception as e:
            self.logger.warning(f"Error getting rate from exchangeratesapi.io: {e}")
        
        return None
    
    def convert_jpy_to_usd(self, jpy_amount: float) -> Dict[str, Any]:
        """
        Convert JPY amount to USD.
        
        Args:
            jpy_amount: Amount in Japanese Yen
            
        Returns:
            Dictionary with conversion details
        """
        exchange_rate = self.get_exchange_rate()
        
        if exchange_rate:
            usd_amount = jpy_amount * exchange_rate
            
            return {
                'original_jpy': jpy_amount,
                'converted_usd': round(usd_amount, 2),
                'exchange_rate': exchange_rate,
                'conversion_date': datetime.now().isoformat(),
                'rate_source': 'api' if exchange_rate != self.fallback_rate else 'fallback'
            }
        
        return {
            'original_jpy': jpy_amount,
            'converted_usd': None,
            'exchange_rate': None,
            'conversion_date': datetime.now().isoformat(),
            'rate_source': 'failed'
        }
    
    def convert_parts_list(self, parts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert JPY prices to USD for a list of car parts.
        
        Args:
            parts_data: List of dictionaries containing part data with JPY prices
            
        Returns:
            List of dictionaries with added USD price information
        """
        exchange_rate = self.get_exchange_rate()
        
        converted_parts = []
        
        for part in parts_data:
            part_copy = part.copy()
            
            jpy_price = part.get('price_jpy')
            if jpy_price and exchange_rate:
                usd_price = jpy_price * exchange_rate
                part_copy['price_usd'] = round(usd_price, 2)
                part_copy['exchange_rate'] = exchange_rate
                part_copy['conversion_date'] = datetime.now().isoformat()
                part_copy['rate_source'] = 'api' if exchange_rate != self.fallback_rate else 'fallback'
            else:
                part_copy['price_usd'] = None
                part_copy['exchange_rate'] = None
                part_copy['conversion_date'] = datetime.now().isoformat()
                part_copy['rate_source'] = 'failed'
            
            converted_parts.append(part_copy)
        
        self.logger.info(f"Converted {len(converted_parts)} parts from JPY to USD")
        return converted_parts
    
    def get_rate_info(self) -> Dict[str, Any]:
        """
        Get current exchange rate information.
        
        Returns:
            Dictionary with rate information
        """
        rate = self.get_exchange_rate()
        
        return {
            'current_rate': rate,
            'rate_date': datetime.now().isoformat(),
            'cached_rates': self.exchange_rate_cache.copy(),
            'cache_expiry': {k: v.isoformat() for k, v in self.cache_expiry.items()},
            'fallback_rate': self.fallback_rate
        }
    
    def set_manual_rate(self, rate: float):
        """
        Set manual exchange rate (useful for testing or when APIs are down).
        
        Args:
            rate: Exchange rate from JPY to USD
        """
        cache_key = 'JPY_USD'
        self._cache_rate(cache_key, rate)
        self.logger.info(f"Set manual exchange rate: 1 JPY = {rate} USD")
    
    def clear_cache(self):
        """Clear exchange rate cache."""
        self.exchange_rate_cache.clear()
        self.cache_expiry.clear()
        
        try:
            if os.path.exists('data/exchange_rate_cache.json'):
                os.remove('data/exchange_rate_cache.json')
        except Exception as e:
            self.logger.error(f"Error clearing cache file: {e}")
        
        self.logger.info("Cleared exchange rate cache")


# Utility functions for easy usage
def convert_jpy_to_usd_simple(jpy_amount: float, config: Dict[str, Any] = None) -> float:
    """
    Simple function to convert JPY to USD.
    
    Args:
        jpy_amount: Amount in JPY
        config: Configuration dictionary
        
    Returns:
        Amount in USD
    """
    if config is None:
        config = {}
    
    converter = CurrencyConverter(config)
    result = converter.convert_jpy_to_usd(jpy_amount)
    
    return result.get('converted_usd', 0.0)


def get_current_jpy_usd_rate(config: Dict[str, Any] = None) -> float:
    """
    Get current JPY to USD exchange rate.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Current exchange rate
    """
    if config is None:
        config = {}
    
    converter = CurrencyConverter(config)
    return converter.get_exchange_rate() or 0.0
