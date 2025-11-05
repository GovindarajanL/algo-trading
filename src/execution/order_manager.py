"""
Order Execution Manager
Handles order placement with retry logic and progressive price modification
REQ-EXEC-001 to REQ-EXEC-020
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import logging
from enum import Enum


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class OrderManager:
    """
    Advanced order execution manager
    Implements progressive price modification and retry logic
    """

    def __init__(self, broker, config: Dict):
        """
        Initialize order manager

        Args:
            broker: Broker instance
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.config = config

        # Order management settings
        self.max_order_retry = config.get('execution', {}).get('max_retry', 3)
        self.order_timeout = config.get('execution', {}).get('timeout_seconds', 60)
        self.price_improvement_ticks = config.get('execution', {}).get('price_improvement_ticks', 1)
        self.tick_size = config.get('execution', {}).get('tick_size', 0.05)

        # Active orders tracking
        self.active_orders = {}  # order_id -> order details
        self.order_history = []

        self.logger.info("Order Manager initialized")

    def place_order_with_retry(
        self,
        order: Dict,
        retry_with_improvement: bool = True
    ) -> Optional[str]:
        """
        Place order with automatic retry and price improvement
        REQ-EXEC-009: Progressive price modification

        Args:
            order: Order details
            retry_with_improvement: Enable progressive price modification

        Returns:
            Order ID if successful, None otherwise
        """
        attempt = 0
        current_price = order.get('price', 0)
        transaction_type = order.get('transaction_type')

        while attempt < self.max_order_retry:
            attempt += 1

            self.logger.info(
                f"Placing order (Attempt {attempt}/{self.max_order_retry}): "
                f"{transaction_type} {order.get('quantity')} x {order.get('symbol')} "
                f"@ ₹{current_price}"
            )

            # Update order price for this attempt
            order['price'] = current_price

            # Place order
            order_id = self.broker.place_order(order)

            if order_id:
                # Order placed successfully
                self.active_orders[order_id] = {
                    'order_id': order_id,
                    'order': order.copy(),
                    'placed_time': datetime.now(),
                    'attempts': attempt,
                    'status': OrderStatus.OPEN
                }

                # Monitor order for fill
                filled = self._monitor_order_fill(order_id)

                if filled:
                    self.logger.info(f"✅ Order {order_id} filled successfully")
                    return order_id

                # Order not filled, try price improvement
                if retry_with_improvement and attempt < self.max_order_retry:
                    # Improve price for next attempt
                    current_price = self._improve_price(
                        current_price,
                        transaction_type,
                        self.price_improvement_ticks
                    )

                    self.logger.info(
                        f"Order not filled, improving price to ₹{current_price}"
                    )

                    # Cancel unfilled order
                    self.broker.cancel_order(order_id)
                else:
                    # No more retries
                    self.broker.cancel_order(order_id)
                    break

            else:
                # Order placement failed
                self.logger.error(f"Order placement failed on attempt {attempt}")

                if attempt < self.max_order_retry:
                    time.sleep(1)  # Wait before retry

        self.logger.error(f"❌ Order failed after {attempt} attempts")
        return None

    def place_multi_leg_order(
        self,
        legs: List[Dict],
        atomic: bool = False
    ) -> Dict[str, Optional[str]]:
        """
        Place multi-leg strategy order
        REQ-EXEC-012: Execute multi-leg strategies

        Args:
            legs: List of individual leg orders
            atomic: If True, cancel all if any leg fails

        Returns:
            Dictionary mapping leg index to order_id
        """
        self.logger.info(f"Placing multi-leg order with {len(legs)} legs (atomic={atomic})")

        results = {}
        placed_orders = []

        for i, leg in enumerate(legs):
            self.logger.info(f"Placing leg {i+1}/{len(legs)}")

            order_id = self.place_order_with_retry(leg)

            results[f"leg_{i}"] = order_id
            if order_id:
                placed_orders.append(order_id)

            if not order_id and atomic:
                # Atomic order - cancel all legs if one fails
                self.logger.error(
                    f"Leg {i+1} failed in atomic order, cancelling all legs"
                )

                for cancel_id in placed_orders:
                    self.broker.cancel_order(cancel_id)

                return {f"leg_{j}": None for j in range(len(legs))}

        success_count = sum(1 for v in results.values() if v is not None)
        self.logger.info(
            f"Multi-leg order complete: {success_count}/{len(legs)} legs filled"
        )

        return results

    def modify_order_progressive(
        self,
        order_id: str,
        target_price: float,
        max_modifications: int = 3
    ) -> bool:
        """
        Progressively modify order price towards target
        REQ-EXEC-009: Progressive price modification

        Args:
            order_id: Order to modify
            target_price: Target price to reach
            max_modifications: Maximum number of modifications

        Returns:
            True if order eventually fills, False otherwise
        """
        if order_id not in self.active_orders:
            self.logger.error(f"Order {order_id} not found in active orders")
            return False

        order_info = self.active_orders[order_id]
        original_price = order_info['order'].get('price', 0)
        transaction_type = order_info['order'].get('transaction_type')

        modification_count = 0

        while modification_count < max_modifications:
            # Check if order filled
            status = self.broker.get_order_status(order_id)

            if status and status.get('status') in ['COMPLETE', 'FILLED']:
                self.logger.info(f"✅ Order {order_id} filled")
                return True

            # Calculate next price
            current_price = order_info['order'].get('price', original_price)

            # Move price towards target
            if transaction_type == 'BUY':
                new_price = min(current_price + self.tick_size, target_price)
            else:  # SELL
                new_price = max(current_price - self.tick_size, target_price)

            # Modify order
            self.logger.info(
                f"Modifying order {order_id} from ₹{current_price} to ₹{new_price}"
            )

            if self.broker.modify_order(order_id, new_price):
                order_info['order']['price'] = new_price
                modification_count += 1

                # Wait to see if it fills
                time.sleep(5)
            else:
                self.logger.error("Order modification failed")
                break

        return False

    def _monitor_order_fill(
        self,
        order_id: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Monitor order for fill within timeout
        REQ-EXEC-018: Track order status in real-time

        Args:
            order_id: Order to monitor
            timeout: Timeout in seconds (default: from config)

        Returns:
            True if filled, False if timeout or rejected
        """
        if timeout is None:
            timeout = self.order_timeout

        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                status = self.broker.get_order_status(order_id)

                if status:
                    order_status = status.get('status', '').upper()

                    if order_status in ['COMPLETE', 'FILLED']:
                        # Order filled
                        self._update_order_status(order_id, OrderStatus.COMPLETE)
                        return True

                    elif order_status in ['REJECTED', 'CANCELLED']:
                        # Order rejected or cancelled
                        self._update_order_status(order_id, OrderStatus.REJECTED)
                        return False

                    elif order_status in ['OPEN', 'PENDING']:
                        # Still pending
                        self._update_order_status(order_id, OrderStatus.OPEN)

                # Wait before next check
                time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error checking order status: {e}")
                time.sleep(2)

        # Timeout
        self.logger.warning(f"Order {order_id} monitoring timeout")
        return False

    def _improve_price(
        self,
        current_price: float,
        transaction_type: str,
        ticks: int
    ) -> float:
        """
        Improve price by given number of ticks
        REQ-EXEC-009: Price improvement logic

        Args:
            current_price: Current order price
            transaction_type: 'BUY' or 'SELL'
            ticks: Number of ticks to improve

        Returns:
            Improved price
        """
        improvement = ticks * self.tick_size

        if transaction_type == 'BUY':
            # For buy orders, increase price to get filled faster
            new_price = current_price + improvement
        else:  # SELL
            # For sell orders, decrease price to get filled faster
            new_price = current_price - improvement

        # Round to tick size
        new_price = round(new_price / self.tick_size) * self.tick_size

        return new_price

    def _update_order_status(self, order_id: str, status: OrderStatus):
        """Update order status in tracking"""
        if order_id in self.active_orders:
            self.active_orders[order_id]['status'] = status
            self.active_orders[order_id]['last_update'] = datetime.now()

    def get_active_orders(self) -> List[Dict]:
        """Get list of active orders"""
        return [
            order for order in self.active_orders.values()
            if order['status'] in [OrderStatus.OPEN, OrderStatus.PENDING]
        ]

    def cancel_all_pending_orders(self) -> int:
        """
        Cancel all pending orders
        REQ-EXEC-020: Emergency order cancellation

        Returns:
            Number of orders cancelled
        """
        pending_orders = self.get_active_orders()
        cancelled_count = 0

        for order in pending_orders:
            order_id = order['order_id']

            if self.broker.cancel_order(order_id):
                self._update_order_status(order_id, OrderStatus.CANCELLED)
                cancelled_count += 1
                self.logger.info(f"Cancelled order {order_id}")

        self.logger.info(f"Cancelled {cancelled_count}/{len(pending_orders)} pending orders")
        return cancelled_count

    def get_order_fill_rate(self) -> float:
        """
        Calculate order fill rate
        Useful for monitoring execution quality

        Returns:
            Fill rate as percentage
        """
        if not self.active_orders:
            return 0.0

        completed = sum(
            1 for order in self.active_orders.values()
            if order['status'] == OrderStatus.COMPLETE
        )

        return (completed / len(self.active_orders)) * 100

    def get_average_fill_time(self) -> float:
        """
        Calculate average time to fill orders

        Returns:
            Average fill time in seconds
        """
        fill_times = []

        for order in self.active_orders.values():
            if order['status'] == OrderStatus.COMPLETE:
                placed_time = order['placed_time']
                last_update = order.get('last_update', placed_time)
                fill_time = (last_update - placed_time).total_seconds()
                fill_times.append(fill_time)

        if fill_times:
            return sum(fill_times) / len(fill_times)

        return 0.0
