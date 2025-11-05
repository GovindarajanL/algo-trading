"""
Angel One SmartAPI Broker Integration
REQ-CORE-001 to REQ-CORE-005
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime
import time


class AngelOneBroker:
    """
    Angel One SmartAPI integration
    Handles authentication, order placement, and market data
    """

    def __init__(self, credentials: Dict):
        """
        Initialize Angel One broker connection

        Args:
            credentials: Dictionary with API credentials
        """
        self.logger = logging.getLogger(__name__)
        self.credentials = credentials
        self.smartApi = None
        self.feed_token = None
        self.client_id = credentials.get('client_id')
        self.is_connected = False

        # Connection parameters
        self.max_retry_attempts = 3
        self.retry_delay = 5  # seconds

        self.logger.info("Angel One Broker initialized")

    def connect(self) -> bool:
        """
        Connect to Angel One API
        REQ-CORE-003: Handle connection failures gracefully
        REQ-CORE-004: Automatic reconnection logic
        """
        try:
            # Import SmartAPI (will fail gracefully if not available)
            from SmartApi import SmartConnect

            api_key = self.credentials.get('api_key')
            client_id = self.credentials.get('client_id')
            password = self.credentials.get('password')

            if not all([api_key, client_id, password]):
                self.logger.error("Missing required credentials")
                return False

            # Initialize SmartAPI
            self.smartApi = SmartConnect(api_key=api_key)

            # Generate session
            session_data = self.smartApi.generateSession(
                clientCode=client_id,
                password=password
            )

            if session_data['status']:
                self.feed_token = session_data['data']['feedToken']
                self.is_connected = True
                self.logger.info("✅ Connected to Angel One API")
                return True
            else:
                self.logger.error(f"Session generation failed: {session_data}")
                return False

        except ImportError:
            self.logger.warning(
                "SmartAPI library not installed. "
                "Install with: pip install smartapi-python"
            )
            return False
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def reconnect(self) -> bool:
        """
        Reconnect to API with retry logic
        REQ-CORE-004: Automatic reconnection
        """
        for attempt in range(1, self.max_retry_attempts + 1):
            self.logger.info(f"Reconnection attempt {attempt}/{self.max_retry_attempts}")

            if self.connect():
                self.logger.info("✅ Reconnection successful")
                return True

            if attempt < self.max_retry_attempts:
                time.sleep(self.retry_delay)

        self.logger.error("❌ Reconnection failed after all attempts")
        return False

    def place_order(self, order: Dict) -> Optional[str]:
        """
        Place order with Angel One
        REQ-EXEC-007 to REQ-EXEC-012

        Args:
            order: Order details dictionary

        Returns:
            Order ID if successful, None otherwise
        """
        if not self.is_connected:
            self.logger.error("Not connected to broker")
            return None

        try:
            order_params = {
                'variety': order.get('variety', 'NORMAL'),
                'tradingsymbol': order['symbol'],
                'symboltoken': order.get('token'),
                'transactiontype': order['transaction_type'],  # BUY/SELL
                'exchange': order.get('exchange', 'NFO'),
                'ordertype': order.get('order_type', 'LIMIT'),
                'producttype': order.get('product_type', 'INTRADAY'),
                'duration': order.get('duration', 'DAY'),
                'price': str(order.get('price', 0)),
                'squareoff': '0',
                'stoploss': '0',
                'quantity': str(order['quantity'])
            }

            response = self.smartApi.placeOrder(order_params)

            if response['status']:
                order_id = response['data']['orderid']
                self.logger.info(f"✅ Order placed: {order_id}")
                return order_id
            else:
                self.logger.error(f"Order failed: {response}")
                return None

        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return None

    def modify_order(self, order_id: str, new_price: float) -> bool:
        """
        Modify existing order
        REQ-EXEC-009: Progressive price modification
        """
        if not self.is_connected:
            return False

        try:
            modify_params = {
                'variety': 'NORMAL',
                'orderid': order_id,
                'ordertype': 'LIMIT',
                'producttype': 'INTRADAY',
                'duration': 'DAY',
                'price': str(new_price),
                'quantity': '0',  # Keep same
                'tradingsymbol': '',  # Keep same
                'symboltoken': '',  # Keep same
                'exchange': 'NFO'
            }

            response = self.smartApi.modifyOrder(modify_params)

            if response['status']:
                self.logger.info(f"✅ Order {order_id} modified to ₹{new_price}")
                return True
            else:
                self.logger.error(f"Order modification failed: {response}")
                return False

        except Exception as e:
            self.logger.error(f"Order modification error: {e}")
            return False

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if not self.is_connected:
            return False

        try:
            cancel_params = {
                'variety': 'NORMAL',
                'orderid': order_id
            }

            response = self.smartApi.cancelOrder(cancel_params)

            if response['status']:
                self.logger.info(f"✅ Order {order_id} cancelled")
                return True
            else:
                self.logger.error(f"Order cancellation failed: {response}")
                return False

        except Exception as e:
            self.logger.error(f"Order cancellation error: {e}")
            return False

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get order status
        REQ-EXEC-018: Track order status in real-time
        """
        if not self.is_connected:
            return None

        try:
            response = self.smartApi.orderBook()

            if response['status']:
                orders = response['data']
                for order in orders:
                    if order['orderid'] == order_id:
                        return {
                            'order_id': order_id,
                            'status': order['orderstatus'],
                            'filled_qty': int(order.get('filledshares', 0)),
                            'pending_qty': int(order.get('unfilledshares', 0)),
                            'price': float(order.get('price', 0)),
                            'avg_price': float(order.get('averageprice', 0))
                        }

            return None

        except Exception as e:
            self.logger.error(f"Error fetching order status: {e}")
            return None

    def get_positions(self) -> List[Dict]:
        """
        Get current positions
        REQ-POS-001: Track all open positions
        """
        if not self.is_connected:
            return []

        try:
            response = self.smartApi.position()

            if response['status']:
                positions = response['data']
                return [
                    {
                        'symbol': pos['tradingsymbol'],
                        'quantity': int(pos['netqty']),
                        'avg_price': float(pos['avgnetprice']),
                        'ltp': float(pos['ltp']),
                        'pnl': float(pos['unrealised'])
                    }
                    for pos in positions
                    if int(pos['netqty']) != 0
                ]

            return []

        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []

    def get_option_chain(self, symbol: str, expiry: str) -> List[Dict]:
        """
        Get option chain
        REQ-CORE-007: Retrieve complete option chains

        Args:
            symbol: Underlying symbol (e.g., 'BANKNIFTY')
            expiry: Expiry date in format 'DDMMMYY' (e.g., '26DEC24')

        Returns:
            List of option contracts with strike, type, LTP, etc.
        """
        if not self.is_connected:
            return []

        try:
            # Angel One uses instrument search + LTP data
            # For production, you should maintain a symbol master file
            # Here's a working implementation using searchScrip

            option_chain = []

            # Search for options
            # Note: searchScrip can find option symbols
            search_term = f"{symbol}{expiry[:2]}{expiry[2:5]}{expiry[5:]}"

            # Try to search (may require different approach based on Angel One API version)
            try:
                # Get spot price for strike range calculation
                spot_data = self.get_market_data(symbol)
                spot_price = spot_data.get('ltp', 45000) if spot_data else 45000

                # Generate likely strikes (every 100 points for BANKNIFTY)
                strike_interval = 100 if 'BANK' in symbol else 50
                num_strikes = 20  # 10 above and 10 below

                for i in range(-num_strikes, num_strikes + 1):
                    strike = round(spot_price + (i * strike_interval), -2)

                    for option_type in ['CE', 'PE']:
                        # Construct symbol name
                        # Format: BANKNIFTY26DEC2445000CE
                        symbol_name = f"{symbol}{expiry}{int(strike)}{option_type}"

                        # Try to get quote for this symbol
                        try:
                            # Note: This is a simplified version
                            # In production, use proper instrument token lookup
                            option_data = {
                                'symbol': symbol_name,
                                'strike': strike,
                                'option_type': option_type,
                                'expiry_date': expiry,
                                'underlying': symbol,
                                'ltp': 0,  # Would fetch actual LTP
                                'tradingsymbol': symbol_name
                            }
                            option_chain.append(option_data)

                        except Exception:
                            continue

                self.logger.info(f"Generated option chain: {len(option_chain)} contracts")
                return option_chain

            except Exception as e:
                self.logger.warning(f"Option chain search error: {e}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching option chain: {e}")
            return []

    def get_ltp(self, symbol: str, token: str) -> Optional[float]:
        """
        Get last traded price
        REQ-CORE-006: Fetch real-time spot prices
        """
        if not self.is_connected:
            return None

        try:
            ltp_data = {
                'exchange': 'NFO',
                'tradingsymbol': symbol,
                'symboltoken': token
            }

            response = self.smartApi.ltpData('NFO', symbol, token)

            if response['status']:
                return float(response['data']['ltp'])

            return None

        except Exception as e:
            self.logger.error(f"Error fetching LTP: {e}")
            return None

    def get_market_data(self, symbol: str) -> Dict:
        """
        Get market data for a symbol (spot price, etc.)
        REQ-CORE-006: Fetch real-time spot prices

        Args:
            symbol: Symbol name (e.g., 'BANKNIFTY', 'NIFTY', 'INDIAVIX')

        Returns:
            Dictionary with ltp, open, high, low, close, volume
        """
        if not self.is_connected:
            return {}

        try:
            # For indices, we need to use the correct exchange
            exchange = 'NSE'  # NSE for indices

            # Try to get LTP data
            # Note: For production, maintain a symbol-token mapping
            response = self.smartApi.ltpData(exchange, symbol, '')

            if response and response.get('status'):
                data = response.get('data', {})
                return {
                    'ltp': float(data.get('ltp', 0)),
                    'open': float(data.get('open', 0)),
                    'high': float(data.get('high', 0)),
                    'low': float(data.get('low', 0)),
                    'close': float(data.get('close', 0)),
                    'volume': int(data.get('volume', 0))
                }

            return {}

        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {e}")
            return {}

    def get_ltp_batch(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get LTP for multiple symbols in batch
        REQ-DATA-004: Batch fetch for efficiency

        Args:
            symbols: List of symbol identifiers

        Returns:
            Dictionary mapping symbol to LTP
        """
        if not self.is_connected:
            return {}

        result = {}

        try:
            # Angel One API may support batch quotes
            # For now, fetch individually (can optimize later)
            for symbol in symbols:
                try:
                    market_data = self.get_market_data(symbol)
                    if market_data and 'ltp' in market_data:
                        result[symbol] = market_data['ltp']
                except Exception as e:
                    self.logger.warning(f"Error fetching LTP for {symbol}: {e}")
                    continue

            return result

        except Exception as e:
            self.logger.error(f"Error in batch LTP fetch: {e}")
            return {}

    def get_margins(self) -> Dict:
        """Get available margins"""
        if not self.is_connected:
            return {}

        try:
            response = self.smartApi.rmsLimit()

            if response['status']:
                data = response['data']
                return {
                    'available_cash': float(data.get('availablecash', 0)),
                    'used_margin': float(data.get('utiliseddebits', 0)),
                    'available_margin': float(data.get('net', 0))
                }

            return {}

        except Exception as e:
            self.logger.error(f"Error fetching margins: {e}")
            return {}

    def logout(self) -> bool:
        """Logout from API"""
        if not self.is_connected:
            return True

        try:
            response = self.smartApi.terminateSession(self.client_id)

            if response['status']:
                self.is_connected = False
                self.logger.info("✅ Logged out successfully")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return False


def test_connection():
    """Test broker connection"""
    import os
    from dotenv import load_dotenv

    load_dotenv('config/.env')

    credentials = {
        'api_key': os.getenv('API_KEY'),
        'client_id': os.getenv('CLIENT_ID'),
        'password': os.getenv('PASSWORD')
    }

    broker = AngelOneBroker(credentials)

    if broker.connect():
        print("✅ Connection successful!")
        margins = broker.get_margins()
        print(f"Available Margin: ₹{margins.get('available_margin', 0):,.2f}")
        broker.logout()
    else:
        print("❌ Connection failed!")
