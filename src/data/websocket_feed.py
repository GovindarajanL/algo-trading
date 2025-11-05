"""
WebSocket Feed for Real-Time Market Data
Connects to Angel One SmartAPI WebSocket for live quotes
REQ-DATA-011: Real-time market data via WebSocket
"""

from typing import Dict, List, Callable, Optional
import logging
import threading
import time
from datetime import datetime
import json


class WebSocketFeed:
    """
    Real-time market data feed via WebSocket
    Subscribes to live quotes from Angel One SmartAPI
    """

    def __init__(self, broker, feed_token: str, config: Dict):
        """
        Initialize WebSocket feed

        Args:
            broker: Broker instance (for authentication)
            feed_token: Feed token from Angel One
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.feed_token = feed_token
        self.config = config

        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.is_running = False

        # Subscription management
        self.subscribed_tokens = set()
        self.token_callbacks = {}  # token -> list of callbacks

        # Latest data cache
        self.latest_data = {}  # token -> latest tick data

        # Connection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds

        # Threading
        self.ws_thread = None
        self.heartbeat_thread = None

        self.logger.info("WebSocket Feed initialized")

    def connect(self) -> bool:
        """
        Connect to WebSocket
        REQ-DATA-011: Establish WebSocket connection

        Returns:
            True if connected, False otherwise
        """
        try:
            # Import SmartWebSocket
            from SmartApi import SmartWebSocket

            # Create correlation ID
            correlation_id = f"algo_trader_{int(time.time())}"

            # WebSocket configuration
            self.ws = SmartWebSocket(
                AUTH_TOKEN=self.feed_token,
                API_KEY=self.broker.credentials.get('api_key'),
                CLIENT_CODE=self.broker.credentials.get('client_id'),
                FEED_TOKEN=self.feed_token
            )

            # Set callbacks
            self.ws.on_open = self._on_open
            self.ws.on_data = self._on_data
            self.ws.on_error = self._on_error
            self.ws.on_close = self._on_close

            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True
            )
            self.ws_thread.start()

            # Wait for connection
            timeout = 10
            start_time = time.time()

            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.is_connected:
                self.logger.info("✅ WebSocket connected")

                # Start heartbeat
                self._start_heartbeat()

                return True
            else:
                self.logger.error("❌ WebSocket connection timeout")
                return False

        except ImportError:
            self.logger.error(
                "SmartAPI WebSocket library not available. "
                "Install with: pip install smartapi-python"
            )
            return False

        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            return False

    def _run_websocket(self):
        """Run WebSocket connection"""
        try:
            self.is_running = True
            self.ws.connect()

        except Exception as e:
            self.logger.error(f"WebSocket run error: {e}")
            self.is_running = False

    def _on_open(self, ws):
        """WebSocket opened callback"""
        self.is_connected = True
        self.reconnect_attempts = 0
        self.logger.info("🔌 WebSocket opened")

        # Re-subscribe to all tokens
        if self.subscribed_tokens:
            self._resubscribe_all()

    def _on_data(self, ws, message):
        """
        WebSocket data callback
        Processes incoming tick data

        Args:
            ws: WebSocket instance
            message: Tick data message
        """
        try:
            # Parse message
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message

            # Extract token and update cache
            token = data.get('token')

            if token:
                # Update latest data
                self.latest_data[token] = {
                    'token': token,
                    'ltp': data.get('last_traded_price', data.get('ltp', 0)),
                    'volume': data.get('volume_trade_for_the_day', data.get('volume', 0)),
                    'open': data.get('open_price_of_the_day', data.get('open', 0)),
                    'high': data.get('high_price_of_the_day', data.get('high', 0)),
                    'low': data.get('low_price_of_the_day', data.get('low', 0)),
                    'close': data.get('closed_price', data.get('close', 0)),
                    'timestamp': datetime.now(),
                    'exchange_timestamp': data.get('exchange_timestamp'),
                }

                # Call registered callbacks
                if token in self.token_callbacks:
                    for callback in self.token_callbacks[token]:
                        try:
                            callback(self.latest_data[token])
                        except Exception as e:
                            self.logger.error(f"Callback error: {e}")

        except Exception as e:
            self.logger.error(f"Error processing WebSocket data: {e}")

    def _on_error(self, ws, error):
        """WebSocket error callback"""
        self.logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws):
        """WebSocket closed callback"""
        self.is_connected = False
        self.logger.warning("🔌 WebSocket closed")

        # Attempt reconnection
        if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.logger.info(
                f"Reconnecting... (Attempt {self.reconnect_attempts}/"
                f"{self.max_reconnect_attempts})"
            )

            time.sleep(self.reconnect_delay)
            self.connect()

    def subscribe(self, tokens: List[str], mode: str = "LTP", callback: Optional[Callable] = None):
        """
        Subscribe to tokens for live updates
        REQ-DATA-012: Subscribe to instruments

        Args:
            tokens: List of instrument tokens
            mode: Subscription mode (LTP, QUOTE, SNAP_QUOTE)
            callback: Optional callback function for updates
        """
        if not self.is_connected:
            self.logger.error("WebSocket not connected")
            return

        try:
            # Prepare subscription request
            subscription_request = {
                "correlationID": f"sub_{int(time.time())}",
                "action": 1,  # Subscribe
                "params": {
                    "mode": self._get_mode_code(mode),
                    "tokenList": [
                        {
                            "exchangeType": 2,  # NFO (1=NSE, 2=NFO, 3=BSE, etc.)
                            "tokens": tokens
                        }
                    ]
                }
            }

            # Send subscription
            self.ws.send(json.dumps(subscription_request))

            # Track subscriptions
            for token in tokens:
                self.subscribed_tokens.add(token)

                # Register callback if provided
                if callback:
                    if token not in self.token_callbacks:
                        self.token_callbacks[token] = []
                    self.token_callbacks[token].append(callback)

            self.logger.info(f"Subscribed to {len(tokens)} tokens in {mode} mode")

        except Exception as e:
            self.logger.error(f"Subscription error: {e}")

    def unsubscribe(self, tokens: List[str]):
        """
        Unsubscribe from tokens
        REQ-DATA-013: Unsubscribe from instruments

        Args:
            tokens: List of instrument tokens to unsubscribe
        """
        if not self.is_connected:
            return

        try:
            # Prepare unsubscription request
            unsubscription_request = {
                "correlationID": f"unsub_{int(time.time())}",
                "action": 0,  # Unsubscribe
                "params": {
                    "mode": 1,  # LTP mode
                    "tokenList": [
                        {
                            "exchangeType": 2,
                            "tokens": tokens
                        }
                    ]
                }
            }

            # Send unsubscription
            self.ws.send(json.dumps(unsubscription_request))

            # Remove from tracking
            for token in tokens:
                self.subscribed_tokens.discard(token)
                if token in self.token_callbacks:
                    del self.token_callbacks[token]

            self.logger.info(f"Unsubscribed from {len(tokens)} tokens")

        except Exception as e:
            self.logger.error(f"Unsubscription error: {e}")

    def get_latest(self, token: str) -> Optional[Dict]:
        """
        Get latest data for a token
        REQ-DATA-014: Retrieve latest tick data

        Args:
            token: Instrument token

        Returns:
            Latest tick data or None
        """
        return self.latest_data.get(token)

    def get_ltp(self, token: str) -> Optional[float]:
        """
        Get Last Traded Price for a token

        Args:
            token: Instrument token

        Returns:
            LTP or None
        """
        data = self.latest_data.get(token)
        return data.get('ltp') if data else None

    def _get_mode_code(self, mode: str) -> int:
        """Convert mode string to code"""
        mode_map = {
            'LTP': 1,
            'QUOTE': 2,
            'SNAP_QUOTE': 3
        }
        return mode_map.get(mode.upper(), 1)

    def _resubscribe_all(self):
        """Resubscribe to all tokens after reconnection"""
        if self.subscribed_tokens:
            tokens_list = list(self.subscribed_tokens)
            self.logger.info(f"Resubscribing to {len(tokens_list)} tokens")
            self.subscribe(tokens_list)

    def _start_heartbeat(self):
        """Start heartbeat thread to keep connection alive"""
        def heartbeat():
            while self.is_running and self.is_connected:
                try:
                    # Send ping
                    ping_request = {
                        "correlationID": f"ping_{int(time.time())}",
                        "action": "heartbeat"
                    }
                    self.ws.send(json.dumps(ping_request))

                except Exception as e:
                    self.logger.warning(f"Heartbeat error: {e}")

                # Sleep for heartbeat interval (every 30 seconds)
                time.sleep(30)

        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self.heartbeat_thread.start()
        self.logger.debug("Heartbeat started")

    def disconnect(self):
        """
        Disconnect WebSocket
        REQ-DATA-015: Clean disconnect
        """
        self.logger.info("Disconnecting WebSocket...")

        self.is_running = False
        self.is_connected = False

        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")

        # Clear subscriptions
        self.subscribed_tokens.clear()
        self.token_callbacks.clear()
        self.latest_data.clear()

        self.logger.info("✅ WebSocket disconnected")

    def get_subscription_count(self) -> int:
        """Get number of subscribed tokens"""
        return len(self.subscribed_tokens)

    def is_subscribed(self, token: str) -> bool:
        """Check if token is subscribed"""
        return token in self.subscribed_tokens


if __name__ == "__main__":
    # Test WebSocket feed
    print("WebSocket Feed Test")
    print("=" * 50)

    # Note: This requires valid credentials and feed token
    # For testing, use paper trading mode

    def on_tick(data):
        """Callback for tick data"""
        print(f"Tick: {data.get('token')} - LTP: ₹{data.get('ltp')}")

    # Create feed (broker and feed_token needed)
    # feed = WebSocketFeed(broker, feed_token, {})

    # if feed.connect():
    #     # Subscribe to tokens
    #     tokens = ['99926000', '99926009']  # Example tokens
    #     feed.subscribe(tokens, mode='LTP', callback=on_tick)
    #
    #     # Run for 60 seconds
    #     time.sleep(60)
    #
    #     # Disconnect
    #     feed.disconnect()

    print("WebSocket test complete")
