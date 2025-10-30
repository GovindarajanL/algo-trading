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
        """
        if not self.is_connected:
            return []

        try:
            # Note: Angel One doesn't have direct option chain API
            # Implementation would use search + quotes for multiple strikes
            # Simplified placeholder

            self.logger.warning("Option chain fetching needs full implementation")
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
