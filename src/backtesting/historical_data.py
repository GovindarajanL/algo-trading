"""
Historical Data Fetcher
Fetches historical options data from Angel One and other sources
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import pandas as pd
import time


class HistoricalDataFetcher:
    """
    Fetch historical data for backtesting
    Supports Angel One API and CSV files
    """

    def __init__(self, broker_api=None):
        """
        Initialize historical data fetcher

        Args:
            broker_api: Angel One broker API instance (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.broker_api = broker_api
        self.cache = {}

    def fetch_historical_candles(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = '5MINUTE'
    ) -> pd.DataFrame:
        """
        Fetch historical candle data from Angel One

        Args:
            symbol: Symbol name (e.g., 'NIFTY', 'BANKNIFTY')
            from_date: Start date
            to_date: End date
            interval: Timeframe ('1MINUTE', '5MINUTE', '15MINUTE', '1HOUR', '1DAY')

        Returns:
            DataFrame with OHLCV data
        """
        if not self.broker_api:
            self.logger.warning("No broker API provided, returning sample data")
            return self._generate_sample_data(symbol, from_date, to_date)

        try:
            # Angel One historical data format
            params = {
                'exchange': 'NSE',
                'symboltoken': self._get_symbol_token(symbol),
                'interval': interval,
                'fromdate': from_date.strftime('%Y-%m-%d %H:%M'),
                'todate': to_date.strftime('%Y-%m-%d %H:%M')
            }

            response = self.broker_api.getCandleData(params)

            if response['status']:
                data = response['data']
                df = pd.DataFrame(
                    data,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            else:
                self.logger.error(f"Failed to fetch data: {response}")
                return pd.DataFrame()

        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()

    def fetch_option_chain_historical(
        self,
        symbol: str,
        expiry_date: str,
        date: datetime
    ) -> List[Dict]:
        """
        Fetch historical option chain for a specific date
        Note: Angel One doesn't provide historical option chain directly
        Need to use alternative data sources or store real-time data

        Args:
            symbol: Underlying symbol
            expiry_date: Option expiry date
            date: Historical date

        Returns:
            List of option data dictionaries
        """
        self.logger.warning(
            "Historical option chain not available via Angel One API. "
            "Use stored data or alternative providers (NSE historical, paid data)"
        )

        # Return sample option chain for demonstration
        return self._generate_sample_option_chain(symbol, expiry_date, date)

    def fetch_from_csv(
        self,
        filepath: str,
        date_column: str = 'timestamp'
    ) -> pd.DataFrame:
        """
        Load historical data from CSV file

        Args:
            filepath: Path to CSV file
            date_column: Name of date column

        Returns:
            DataFrame with historical data
        """
        try:
            df = pd.read_csv(filepath)
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values(date_column)

            self.logger.info(f"Loaded {len(df)} rows from {filepath}")
            return df

        except Exception as e:
            self.logger.error(f"Error loading CSV: {e}")
            return pd.DataFrame()

    def save_realtime_data_for_backtest(
        self,
        data: List[Dict],
        filepath: str
    ):
        """
        Save real-time data for future backtesting

        Args:
            data: List of data dictionaries
            filepath: Path to save CSV
        """
        try:
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Saved {len(df)} rows to {filepath}")

        except Exception as e:
            self.logger.error(f"Error saving data: {e}")

    def fetch_nse_option_chain(
        self,
        symbol: str,
        expiry_date: str
    ) -> List[Dict]:
        """
        Fetch option chain from NSE website
        Alternative when Angel One data not available

        Args:
            symbol: Symbol name
            expiry_date: Expiry date

        Returns:
            List of option data
        """
        try:
            import requests

            # NSE option chain URL (example)
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Parse NSE data format
                # (Implementation depends on NSE API structure)

                self.logger.info(f"Fetched NSE option chain for {symbol}")
                return []  # Return parsed data

            else:
                self.logger.error(f"NSE API error: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching NSE data: {e}")
            return []

    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for Angel One API"""
        # Token mapping (would need to be populated from Angel One API)
        tokens = {
            'NIFTY': '99926000',
            'BANKNIFTY': '99926009',
            'FINNIFTY': '99926037'
        }
        return tokens.get(symbol, '')

    def _generate_sample_data(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> pd.DataFrame:
        """
        Generate sample price data for testing
        Uses random walk simulation
        """
        import numpy as np

        # Initial price based on symbol
        initial_prices = {
            'NIFTY': 22000,
            'BANKNIFTY': 45000,
            'FINNIFTY': 20000
        }
        initial_price = initial_prices.get(symbol, 45000)

        # Generate minute-by-minute data
        dates = pd.date_range(start=from_date, end=to_date, freq='5T')

        # Market hours filter (9:15 AM - 3:30 PM)
        dates = dates[
            (dates.hour >= 9) & (dates.hour <= 15) &
            ~((dates.hour == 9) & (dates.minute < 15)) &
            ~((dates.hour == 15) & (dates.minute > 30))
        ]

        # Random walk
        np.random.seed(42)
        returns = np.random.normal(0, 0.002, len(dates))  # 0.2% std dev
        prices = initial_price * (1 + returns).cumprod()

        # Generate OHLCV
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + abs(np.random.normal(0, 0.001, len(dates)))),
            'low': prices * (1 - abs(np.random.normal(0, 0.001, len(dates)))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(dates))
        })

        self.logger.info(f"Generated {len(df)} sample candles for {symbol}")
        return df

    def _generate_sample_option_chain(
        self,
        symbol: str,
        expiry_date: str,
        date: datetime
    ) -> List[Dict]:
        """Generate sample option chain for testing"""
        import numpy as np

        spot_price = 45000 if symbol == 'BANKNIFTY' else 22000
        strike_interval = 100 if symbol == 'BANKNIFTY' else 50

        # Generate strikes around spot
        strikes = range(
            int(spot_price - 1000),
            int(spot_price + 1000),
            strike_interval
        )

        option_chain = []

        for strike in strikes:
            # Simplified pricing (normally would use Black-Scholes)
            moneyness = (spot_price - strike) / spot_price

            # Call option
            call_price = max(spot_price - strike, 0) + abs(moneyness) * 100
            option_chain.append({
                'symbol': f"{symbol}25N06{strike}CE",
                'strike': strike,
                'option_type': 'CE',
                'expiry_date': expiry_date,
                'ltp': round(call_price, 2),
                'bid': round(call_price * 0.98, 2),
                'ask': round(call_price * 1.02, 2),
                'volume': np.random.randint(1000, 100000),
                'oi': np.random.randint(10000, 500000),
                'iv': 0.15 + abs(moneyness) * 0.5,
                'greeks': {
                    'delta': 0.5 + moneyness,
                    'gamma': 0.01,
                    'theta': -5,
                    'vega': 10
                }
            })

            # Put option
            put_price = max(strike - spot_price, 0) + abs(moneyness) * 100
            option_chain.append({
                'symbol': f"{symbol}25N06{strike}PE",
                'strike': strike,
                'option_type': 'PE',
                'expiry_date': expiry_date,
                'ltp': round(put_price, 2),
                'bid': round(put_price * 0.98, 2),
                'ask': round(put_price * 1.02, 2),
                'volume': np.random.randint(1000, 100000),
                'oi': np.random.randint(10000, 500000),
                'iv': 0.15 + abs(moneyness) * 0.5,
                'greeks': {
                    'delta': -0.5 + moneyness,
                    'gamma': 0.01,
                    'theta': -5,
                    'vega': 10
                }
            })

        return option_chain
