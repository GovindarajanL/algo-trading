"""
Paper Trading Simulator
Simulates trading without real money
REQ-COMP-010 to REQ-COMP-014
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import random


class PaperTradingBroker:
    """
    Paper trading simulator for safe testing
    REQ-COMP-010 to REQ-COMP-014
    """

    def __init__(self, initial_capital: float = 50000):
        """
        Initialize paper trading broker

        Args:
            initial_capital: Starting capital for simulation
        """
        self.logger = logging.getLogger(__name__)
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.positions = {}
        self.orders = {}
        self.order_id_counter = 1000
        self.is_connected = True

        self.logger.info(
            f"✅ Paper Trading initialized with capital: ₹{initial_capital:,.2f}"
        )

    def connect(self) -> bool:
        """Simulate connection"""
        self.is_connected = True
        self.logger.info("✅ Paper Trading connected (simulated)")
        return True

    def reconnect(self) -> bool:
        """Simulate reconnection"""
        return self.connect()

    def place_order(self, order: Dict) -> Optional[str]:
        """
        Simulate order placement
        REQ-COMP-013: Simulate order fills realistically

        Args:
            order: Order details

        Returns:
            Simulated order ID
        """
        if not self.is_connected:
            self.logger.error("Not connected")
            return None

        # Generate order ID
        order_id = f"PAPER_{self.order_id_counter}"
        self.order_id_counter += 1

        # Simulate order
        simulated_order = {
            'order_id': order_id,
            'symbol': order['symbol'],
            'transaction_type': order['transaction_type'],
            'quantity': order['quantity'],
            'order_type': order.get('order_type', 'LIMIT'),
            'price': order.get('price', 0),
            'status': 'PENDING',
            'filled_qty': 0,
            'pending_qty': order['quantity'],
            'avg_price': 0,
            'order_time': datetime.now(),
            'fill_time': None
        }

        self.orders[order_id] = simulated_order

        # Simulate instant fill for limit orders (90% probability)
        # Simulate realistic market behavior
        if order.get('order_type') == 'LIMIT':
            if random.random() < 0.90:  # 90% fill rate
                self._simulate_fill(order_id, order.get('price', 0))
            else:
                self.logger.debug(f"Order {order_id} waiting for fill")
        elif order.get('order_type') == 'MARKET':
            # Market orders fill instantly with slippage
            slippage = random.uniform(-0.5, 0.5)  # ±0.5% slippage
            fill_price = order.get('price', 0) * (1 + slippage / 100)
            self._simulate_fill(order_id, fill_price)

        self.logger.info(
            f"📝 Paper Order placed: {order_id} - "
            f"{order['transaction_type']} {order['quantity']} {order['symbol']}"
        )

        return order_id

    def _simulate_fill(self, order_id: str, fill_price: float):
        """Simulate order fill"""
        order = self.orders.get(order_id)
        if not order:
            return

        order['status'] = 'COMPLETE'
        order['filled_qty'] = order['quantity']
        order['pending_qty'] = 0
        order['avg_price'] = fill_price
        order['fill_time'] = datetime.now()

        self.logger.debug(f"✅ Paper Order filled: {order_id} @ ₹{fill_price:.2f}")

    def modify_order(self, order_id: str, new_price: float) -> bool:
        """Simulate order modification"""
        order = self.orders.get(order_id)
        if not order:
            self.logger.error(f"Order {order_id} not found")
            return False

        if order['status'] == 'COMPLETE':
            self.logger.error(f"Cannot modify completed order {order_id}")
            return False

        order['price'] = new_price
        self.logger.info(f"✅ Paper Order modified: {order_id} to ₹{new_price:.2f}")

        # Simulate fill with modified price
        if random.random() < 0.80:  # 80% fill rate after modification
            self._simulate_fill(order_id, new_price)

        return True

    def cancel_order(self, order_id: str) -> bool:
        """Simulate order cancellation"""
        order = self.orders.get(order_id)
        if not order:
            return False

        if order['status'] == 'COMPLETE':
            self.logger.error(f"Cannot cancel completed order {order_id}")
            return False

        order['status'] = 'CANCELLED'
        self.logger.info(f"✅ Paper Order cancelled: {order_id}")
        return True

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get simulated order status"""
        order = self.orders.get(order_id)
        if not order:
            return None

        return {
            'order_id': order_id,
            'status': order['status'],
            'filled_qty': order['filled_qty'],
            'pending_qty': order['pending_qty'],
            'price': order['price'],
            'avg_price': order['avg_price']
        }

    def get_positions(self) -> List[Dict]:
        """Get simulated positions"""
        return list(self.positions.values())

    def update_position(self, symbol: str, quantity: int, avg_price: float):
        """Update simulated position"""
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'quantity': 0,
                'avg_price': 0,
                'ltp': avg_price,
                'pnl': 0
            }

        pos = self.positions[symbol]
        pos['quantity'] += quantity
        pos['avg_price'] = avg_price
        pos['ltp'] = avg_price  # Simplified

        if pos['quantity'] == 0:
            del self.positions[symbol]

    def get_option_chain(self, symbol: str, expiry: str) -> List[Dict]:
        """
        Simulate option chain
        Note: Would need market data feed for realistic simulation
        """
        self.logger.warning("Paper trading: Option chain simulation not fully implemented")
        return []

    def get_ltp(self, symbol: str, token: str) -> Optional[float]:
        """Simulate LTP (would need data feed)"""
        self.logger.debug(f"Paper trading: LTP requested for {symbol}")
        # Would integrate with market data feed
        return None

    def get_margins(self) -> Dict:
        """Get simulated margins"""
        used_margin = self.initial_capital - self.available_capital

        return {
            'available_cash': self.available_capital,
            'used_margin': used_margin,
            'available_margin': self.available_capital
        }

    def logout(self) -> bool:
        """Simulate logout"""
        self.is_connected = False
        self.logger.info("✅ Paper Trading logged out")
        return True

    def get_account_summary(self) -> Dict:
        """Get paper trading account summary"""
        total_pnl = sum(pos['pnl'] for pos in self.positions.values())

        return {
            'initial_capital': self.initial_capital,
            'available_capital': self.available_capital,
            'used_capital': self.initial_capital - self.available_capital,
            'total_positions': len(self.positions),
            'total_orders': len(self.orders),
            'unrealized_pnl': total_pnl,
            'account_value': self.initial_capital + total_pnl
        }
