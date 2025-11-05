"""
Market Data Feed
Unified interface for fetching market data from broker or other sources
REQ-DATA-001 to REQ-DATA-010
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import time
from threading import Lock


class MarketDataFeed:
    """
    Unified market data feed interface
    Supports multiple data sources with caching
    """

    def __init__(self, broker, config: Dict):
        """
        Initialize market data feed

        Args:
            broker: Broker instance (Angel One, Paper Trading, etc.)
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.config = config

        # Cache settings
        self.cache_enabled = config.get('data', {}).get('enable_cache', True)
        self.cache_ttl = config.get('data', {}).get('cache_ttl_seconds', 5)

        # Data caches with timestamps
        self._spot_cache = {}
        self._vix_cache = {}
        self._option_chain_cache = {}
        self._ltp_cache = {}

        # Thread safety
        self._cache_lock = Lock()

        # Rate limiting
        self.rate_limit_delay = config.get('data', {}).get('rate_limit_ms', 100) / 1000
        self._last_request_time = 0

        self.logger.info("Market Data Feed initialized")

    def get_spot_price(self, symbol: str) -> Optional[float]:
        """
        Get current spot price for a symbol
        REQ-DATA-001: Fetch spot price

        Args:
            symbol: Symbol name (e.g., 'BANKNIFTY', 'NIFTY')

        Returns:
            Current spot price or None if unavailable
        """
        # Check cache first
        if self.cache_enabled:
            cached = self._get_from_cache(self._spot_cache, symbol)
            if cached is not None:
                return cached

        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Fetch from broker
            market_data = self.broker.get_market_data(symbol)

            if market_data and 'ltp' in market_data:
                spot_price = float(market_data['ltp'])

                # Update cache
                if self.cache_enabled:
                    self._update_cache(self._spot_cache, symbol, spot_price)

                self.logger.debug(f"Spot price for {symbol}: ₹{spot_price:.2f}")
                return spot_price

        except Exception as e:
            self.logger.error(f"Error fetching spot price for {symbol}: {e}")

        return None

    def get_vix(self) -> Optional[float]:
        """
        Get current VIX (India VIX)
        REQ-DATA-002: Fetch VIX for volatility assessment

        Returns:
            Current VIX value or None
        """
        # Check cache
        if self.cache_enabled:
            cached = self._get_from_cache(self._vix_cache, 'INDIAVIX')
            if cached is not None:
                return cached

        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Try to fetch from broker
            vix_data = self.broker.get_market_data('INDIAVIX')

            if vix_data and 'ltp' in vix_data:
                vix = float(vix_data['ltp'])

                # Update cache
                if self.cache_enabled:
                    self._update_cache(self._vix_cache, 'INDIAVIX', vix)

                self.logger.debug(f"India VIX: {vix:.2f}")
                return vix

        except Exception as e:
            self.logger.warning(f"Error fetching VIX: {e}")

        # Return default if unavailable
        default_vix = self.config.get('data', {}).get('default_vix', 20.0)
        self.logger.warning(f"Using default VIX: {default_vix}")
        return default_vix

    def get_option_chain(
        self,
        symbol: str,
        expiry_date: str,
        strikes_range: Optional[int] = None
    ) -> List[Dict]:
        """
        Get option chain for a symbol and expiry
        REQ-DATA-003: Fetch complete option chain

        Args:
            symbol: Underlying symbol (e.g., 'BANKNIFTY')
            expiry_date: Expiry date in format 'DDMMMYY' (e.g., '26DEC24')
            strikes_range: Optional number of strikes around ATM to fetch

        Returns:
            List of option contracts with strike, type, LTP, Greeks, etc.
        """
        cache_key = f"{symbol}_{expiry_date}"

        # Check cache
        if self.cache_enabled:
            cached = self._get_from_cache(self._option_chain_cache, cache_key)
            if cached is not None:
                return cached

        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Fetch from broker
            option_chain = self.broker.get_option_chain(symbol, expiry_date)

            if option_chain:
                # Filter by strikes range if specified
                if strikes_range:
                    spot_price = self.get_spot_price(symbol)
                    if spot_price:
                        option_chain = self._filter_option_chain_by_range(
                            option_chain, spot_price, strikes_range
                        )

                # Enrich with additional data if needed
                option_chain = self._enrich_option_chain(option_chain)

                # Update cache
                if self.cache_enabled:
                    self._update_cache(self._option_chain_cache, cache_key, option_chain)

                self.logger.debug(
                    f"Fetched option chain for {symbol} {expiry_date}: "
                    f"{len(option_chain)} contracts"
                )
                return option_chain

        except Exception as e:
            self.logger.error(f"Error fetching option chain: {e}")

        return []

    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get LTP (Last Traded Price) for multiple symbols in batch
        REQ-DATA-004: Batch fetch for efficiency

        Args:
            symbols: List of symbol identifiers

        Returns:
            Dictionary mapping symbol to LTP
        """
        result = {}

        # Check cache for all symbols first
        uncached_symbols = []

        if self.cache_enabled:
            for symbol in symbols:
                cached = self._get_from_cache(self._ltp_cache, symbol)
                if cached is not None:
                    result[symbol] = cached
                else:
                    uncached_symbols.append(symbol)
        else:
            uncached_symbols = symbols

        if not uncached_symbols:
            return result

        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Fetch uncached symbols
            # Note: Most brokers support batch fetch
            ltp_data = self.broker.get_ltp_batch(uncached_symbols)

            if ltp_data:
                result.update(ltp_data)

                # Update cache
                if self.cache_enabled:
                    for symbol, ltp in ltp_data.items():
                        self._update_cache(self._ltp_cache, symbol, ltp)

                self.logger.debug(f"Fetched LTP for {len(result)} symbols")

        except AttributeError:
            # Broker doesn't support batch fetch, fetch individually
            self.logger.debug("Broker doesn't support batch LTP, fetching individually")

            for symbol in uncached_symbols:
                try:
                    self._apply_rate_limit()
                    market_data = self.broker.get_market_data(symbol)

                    if market_data and 'ltp' in market_data:
                        ltp = float(market_data['ltp'])
                        result[symbol] = ltp

                        if self.cache_enabled:
                            self._update_cache(self._ltp_cache, symbol, ltp)

                except Exception as e:
                    self.logger.warning(f"Error fetching LTP for {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"Error in batch LTP fetch: {e}")

        return result

    def get_greeks_for_option_chain(
        self,
        option_chain: List[Dict],
        spot_price: float,
        time_to_expiry: float
    ) -> List[Dict]:
        """
        Calculate Greeks for entire option chain
        REQ-DATA-005: Enrich option chain with Greeks

        Args:
            option_chain: Option chain data
            spot_price: Current spot price
            time_to_expiry: Time to expiry in years

        Returns:
            Option chain enriched with Greeks
        """
        from greeks.black_scholes import BlackScholesCalculator

        bs_calc = BlackScholesCalculator()
        enriched_chain = []

        for option in option_chain:
            try:
                strike = option['strike']
                option_type = option['option_type']
                ltp = option.get('ltp', option.get('last_price', 0))

                if ltp > 0 and time_to_expiry > 0:
                    # Estimate IV (you may want to use IV calculator here)
                    # For now, use a simple estimation
                    volatility = 0.25  # Default 25% IV

                    # Calculate Greeks
                    greeks = bs_calc.calculate_greeks(
                        spot_price=spot_price,
                        strike_price=strike,
                        time_to_expiry=time_to_expiry,
                        volatility=volatility,
                        option_type=option_type
                    )

                    # Add Greeks to option
                    option['greeks'] = greeks

                enriched_chain.append(option)

            except Exception as e:
                self.logger.warning(f"Error calculating Greeks for {option}: {e}")
                enriched_chain.append(option)

        return enriched_chain

    def invalidate_cache(self, cache_type: Optional[str] = None):
        """
        Invalidate cache
        REQ-DATA-006: Cache management

        Args:
            cache_type: Specific cache to invalidate ('spot', 'vix', 'option_chain', 'ltp')
                       If None, invalidates all caches
        """
        with self._cache_lock:
            if cache_type is None or cache_type == 'all':
                self._spot_cache.clear()
                self._vix_cache.clear()
                self._option_chain_cache.clear()
                self._ltp_cache.clear()
                self.logger.info("All caches invalidated")

            elif cache_type == 'spot':
                self._spot_cache.clear()
            elif cache_type == 'vix':
                self._vix_cache.clear()
            elif cache_type == 'option_chain':
                self._option_chain_cache.clear()
            elif cache_type == 'ltp':
                self._ltp_cache.clear()

    def _get_from_cache(self, cache: Dict, key: str) -> Optional[any]:
        """Get value from cache if not expired"""
        with self._cache_lock:
            if key in cache:
                value, timestamp = cache[key]
                age = (datetime.now() - timestamp).total_seconds()

                if age < self.cache_ttl:
                    return value

                # Expired, remove from cache
                del cache[key]

        return None

    def _update_cache(self, cache: Dict, key: str, value: any):
        """Update cache with timestamp"""
        with self._cache_lock:
            cache[key] = (value, datetime.now())

    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        if self.rate_limit_delay > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _filter_option_chain_by_range(
        self,
        option_chain: List[Dict],
        spot_price: float,
        strikes_range: int
    ) -> List[Dict]:
        """Filter option chain to strikes near ATM"""
        # Get all unique strikes
        strikes = sorted(set(opt['strike'] for opt in option_chain))

        # Find ATM strike index
        atm_index = min(range(len(strikes)),
                       key=lambda i: abs(strikes[i] - spot_price))

        # Calculate range indices
        start_idx = max(0, atm_index - strikes_range)
        end_idx = min(len(strikes), atm_index + strikes_range + 1)

        # Get strikes in range
        strikes_in_range = strikes[start_idx:end_idx]

        # Filter option chain
        filtered = [opt for opt in option_chain
                   if opt['strike'] in strikes_in_range]

        return filtered

    def _enrich_option_chain(self, option_chain: List[Dict]) -> List[Dict]:
        """Enrich option chain with additional computed fields"""
        enriched = []

        for option in option_chain:
            # Add computed fields
            option['symbol_full'] = self._construct_symbol(option)

            # Add moneyness indicator
            # This would require spot price, so skip for now
            # option['moneyness'] = 'ITM' if ... else 'OTM'

            enriched.append(option)

        return enriched

    def _construct_symbol(self, option: Dict) -> str:
        """
        Construct full option symbol from components
        Format: SYMBOL EXPIRY STRIKE TYPE
        Example: BANKNIFTY26DEC2445000CE
        """
        try:
            symbol = option.get('underlying', option.get('symbol', ''))
            expiry = option.get('expiry_date', '')
            strike = option.get('strike', 0)
            option_type = option.get('option_type', 'CE')

            # Remove common formatting
            expiry_clean = expiry.replace('-', '').replace('/', '')

            return f"{symbol}{expiry_clean}{int(strike)}{option_type}"

        except Exception:
            return option.get('tradingsymbol', 'UNKNOWN')
