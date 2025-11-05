"""
Symbol Master Manager for Angel One
Downloads and maintains instrument token mapping
REQ-DATA-007: Symbol master file management
"""

from typing import Dict, List, Optional
import pandas as pd
import logging
import os
from datetime import datetime, timedelta
import json


class SymbolMasterManager:
    """
    Manages symbol master file for Angel One
    Downloads, caches, and provides instrument token lookup
    """

    def __init__(self, broker, cache_dir: str = "data/symbol_master"):
        """
        Initialize Symbol Master Manager

        Args:
            broker: Angel One broker instance
            cache_dir: Directory to cache symbol master files
        """
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.cache_dir = cache_dir

        # Create cache directory if not exists
        os.makedirs(cache_dir, exist_ok=True)

        # Symbol master data
        self.symbol_df = None
        self.symbol_lookup = {}  # symbol -> token mapping
        self.token_lookup = {}   # token -> symbol data mapping

        # Cache settings
        self.cache_validity_days = 7  # Refresh weekly

        self.logger.info("Symbol Master Manager initialized")

    def download_symbol_master(self, force_refresh: bool = False) -> bool:
        """
        Download symbol master from Angel One
        REQ-DATA-007: Download and cache symbol master

        Args:
            force_refresh: Force download even if cache is valid

        Returns:
            True if successful, False otherwise
        """
        cache_file = os.path.join(self.cache_dir, 'angel_one_symbols.csv')

        # Check if cache exists and is recent
        if not force_refresh and os.path.exists(cache_file):
            file_age_days = (datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(cache_file)
            )).days

            if file_age_days < self.cache_validity_days:
                self.logger.info(
                    f"Using cached symbol master (age: {file_age_days} days)"
                )
                return self._load_from_cache(cache_file)

        # Download fresh symbol master
        self.logger.info("Downloading symbol master from Angel One...")

        try:
            # Angel One provides symbol master via API or downloadable file
            # URL: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json

            import requests

            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Convert to DataFrame
                df = pd.DataFrame(data)

                # Save to cache
                df.to_csv(cache_file, index=False)

                self.logger.info(
                    f"✅ Downloaded symbol master: {len(df)} instruments"
                )

                # Load into memory
                return self._load_from_cache(cache_file)

            else:
                self.logger.error(
                    f"Failed to download symbol master: HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error downloading symbol master: {e}")

            # Try to use cached file even if old
            if os.path.exists(cache_file):
                self.logger.warning("Using old cached symbol master")
                return self._load_from_cache(cache_file)

            return False

    def _load_from_cache(self, cache_file: str) -> bool:
        """Load symbol master from cache file"""
        try:
            self.symbol_df = pd.read_csv(cache_file)

            # Build lookup dictionaries for fast access
            self._build_lookups()

            self.logger.info(
                f"Loaded {len(self.symbol_df)} symbols from cache"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error loading symbol master from cache: {e}")
            return False

    def _build_lookups(self):
        """Build fast lookup dictionaries"""
        if self.symbol_df is None:
            return

        self.symbol_lookup = {}
        self.token_lookup = {}

        for _, row in self.symbol_df.iterrows():
            symbol = row.get('symbol', row.get('tradingsymbol', ''))
            token = str(row.get('token', ''))

            if symbol and token:
                self.symbol_lookup[symbol] = row.to_dict()
                self.token_lookup[token] = row.to_dict()

        self.logger.debug(f"Built lookups for {len(self.symbol_lookup)} symbols")

    def get_token(self, symbol: str, exchange: str = 'NFO') -> Optional[str]:
        """
        Get instrument token for a symbol
        REQ-DATA-008: Token lookup

        Args:
            symbol: Trading symbol (e.g., 'BANKNIFTY26DEC2445000CE')
            exchange: Exchange (NFO, NSE, BSE, etc.)

        Returns:
            Instrument token or None
        """
        if self.symbol_df is None:
            self.download_symbol_master()

        # Try exact match first
        if symbol in self.symbol_lookup:
            return self.symbol_lookup[symbol].get('token')

        # Try case-insensitive match
        symbol_upper = symbol.upper()
        if symbol_upper in self.symbol_lookup:
            return self.symbol_lookup[symbol_upper].get('token')

        # Search in DataFrame
        try:
            result = self.symbol_df[
                (self.symbol_df['symbol'] == symbol) |
                (self.symbol_df['tradingsymbol'] == symbol)
            ]

            if exchange:
                result = result[result['exch_seg'] == exchange]

            if not result.empty:
                return str(result.iloc[0]['token'])

        except Exception as e:
            self.logger.warning(f"Error searching for symbol {symbol}: {e}")

        return None

    def get_symbol_data(self, symbol: str) -> Optional[Dict]:
        """
        Get complete symbol data

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with symbol data or None
        """
        if symbol in self.symbol_lookup:
            return self.symbol_lookup[symbol]

        # Search in DataFrame
        if self.symbol_df is not None:
            try:
                result = self.symbol_df[
                    (self.symbol_df['symbol'] == symbol) |
                    (self.symbol_df['tradingsymbol'] == symbol)
                ]

                if not result.empty:
                    return result.iloc[0].to_dict()

            except Exception:
                pass

        return None

    def search_symbols(
        self,
        query: str,
        exchange: Optional[str] = None,
        instrument_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for symbols matching query
        REQ-DATA-009: Symbol search

        Args:
            query: Search query (partial symbol name)
            exchange: Filter by exchange
            instrument_type: Filter by type (OPTIDX, FUTSTK, etc.)
            limit: Maximum results to return

        Returns:
            List of matching symbol data
        """
        if self.symbol_df is None:
            self.download_symbol_master()
            if self.symbol_df is None:
                return []

        try:
            # Search in symbol and tradingsymbol columns
            mask = (
                self.symbol_df['symbol'].str.contains(query, case=False, na=False) |
                self.symbol_df['tradingsymbol'].str.contains(query, case=False, na=False)
            )

            # Apply filters
            if exchange:
                mask &= (self.symbol_df['exch_seg'] == exchange)

            if instrument_type:
                mask &= (self.symbol_df['instrumenttype'] == instrument_type)

            results = self.symbol_df[mask].head(limit)

            return results.to_dict('records')

        except Exception as e:
            self.logger.error(f"Error searching symbols: {e}")
            return []

    def get_option_symbols(
        self,
        underlying: str,
        expiry: str,
        strike_range: Optional[tuple] = None
    ) -> List[Dict]:
        """
        Get option symbols for an underlying and expiry
        REQ-DATA-010: Option chain symbol lookup

        Args:
            underlying: Underlying symbol (e.g., 'BANKNIFTY')
            expiry: Expiry date string (e.g., '26DEC24')
            strike_range: Optional (min_strike, max_strike) tuple

        Returns:
            List of option symbols
        """
        if self.symbol_df is None:
            self.download_symbol_master()
            if self.symbol_df is None:
                return []

        try:
            # Filter for options of this underlying
            mask = (
                self.symbol_df['name'].str.contains(underlying, case=False, na=False) &
                (self.symbol_df['instrumenttype'] == 'OPTIDX')
            )

            # Filter by expiry if available
            if 'expiry' in self.symbol_df.columns:
                mask &= self.symbol_df['expiry'].str.contains(expiry, case=False, na=False)

            # Filter by strike range if provided
            if strike_range and 'strike' in self.symbol_df.columns:
                min_strike, max_strike = strike_range
                mask &= (
                    (self.symbol_df['strike'] >= min_strike) &
                    (self.symbol_df['strike'] <= max_strike)
                )

            results = self.symbol_df[mask]

            return results.to_dict('records')

        except Exception as e:
            self.logger.error(f"Error getting option symbols: {e}")
            return []

    def construct_option_symbol(
        self,
        underlying: str,
        expiry: str,
        strike: int,
        option_type: str
    ) -> str:
        """
        Construct option symbol in Angel One format
        Format: BANKNIFTY26DEC2445000CE

        Args:
            underlying: Underlying (BANKNIFTY, NIFTY, etc.)
            expiry: Expiry in DDMMMYY format
            strike: Strike price
            option_type: CE or PE

        Returns:
            Constructed symbol string
        """
        return f"{underlying}{expiry}{int(strike)}{option_type.upper()}"

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol exists in master

        Args:
            symbol: Symbol to validate

        Returns:
            True if exists, False otherwise
        """
        return self.get_token(symbol) is not None

    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Lot size or default 25 for BANKNIFTY/NIFTY
        """
        symbol_data = self.get_symbol_data(symbol)

        if symbol_data:
            return int(symbol_data.get('lotsize', 25))

        # Default lot sizes for major indices
        if 'BANKNIFTY' in symbol.upper():
            return 25
        elif 'NIFTY' in symbol.upper():
            return 50
        elif 'FINNIFTY' in symbol.upper():
            return 40

        return 1

    def get_tick_size(self, symbol: str) -> float:
        """
        Get tick size for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Tick size (usually 0.05 for options)
        """
        symbol_data = self.get_symbol_data(symbol)

        if symbol_data:
            return float(symbol_data.get('tick_size', 0.05))

        # Default tick size for options
        return 0.05


# Global instance for easy access
_symbol_master_instance = None


def get_symbol_master(broker=None, cache_dir="data/symbol_master") -> SymbolMasterManager:
    """Get or create global symbol master instance"""
    global _symbol_master_instance

    if _symbol_master_instance is None and broker:
        _symbol_master_instance = SymbolMasterManager(broker, cache_dir)

    return _symbol_master_instance


if __name__ == "__main__":
    # Test symbol master
    print("Symbol Master Test")
    print("=" * 50)

    # Create manager (without broker for testing)
    manager = SymbolMasterManager(None)

    # Try to download
    if manager.download_symbol_master():
        print(f"✅ Symbol master loaded: {len(manager.symbol_df)} instruments")

        # Test lookup
        test_symbols = ['BANKNIFTY', 'NIFTY', 'FINNIFTY']

        for symbol in test_symbols:
            token = manager.get_token(symbol, 'NSE')
            print(f"{symbol}: Token={token}")

        # Test search
        print("\nSearch 'BANKNIFTY':")
        results = manager.search_symbols('BANKNIFTY', exchange='NFO', limit=5)
        for result in results:
            print(f"  {result.get('symbol')} - {result.get('token')}")

    else:
        print("❌ Failed to load symbol master")
