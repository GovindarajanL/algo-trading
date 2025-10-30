"""
Circuit Breakers
Automatic trading halts on risk limit breaches
REQ-RISK-017 to REQ-RISK-021
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging


class BreakerType(Enum):
    """Circuit breaker types"""
    DAILY_LOSS = "daily_loss_limit"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    MARGIN_ALERT = "margin_alert"
    SYSTEM_HEALTH = "system_health"
    MARKET_VOLATILITY = "market_volatility"
    TIME_BASED = "time_based"


class BreakerStatus(Enum):
    """Circuit breaker status"""
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    RECOVERING = "RECOVERING"
    RESET = "RESET"


@dataclass
class BreakerEvent:
    """Circuit breaker event"""
    breaker_type: BreakerType
    trigger_time: datetime
    trigger_value: float
    threshold_value: float
    message: str
    recovery_action: str


class CircuitBreakers:
    """
    Circuit Breakers Manager
    Monitors conditions and triggers automatic trading halts
    """

    def __init__(self, config: Dict):
        """
        Initialize circuit breakers

        Args:
            config: Risk limits configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.breakers_config = config.get('circuit_breakers', {})

        # Breaker states
        self.breakers_status = {
            BreakerType.DAILY_LOSS: BreakerStatus.ACTIVE,
            BreakerType.CONSECUTIVE_LOSSES: BreakerStatus.ACTIVE,
            BreakerType.MARGIN_ALERT: BreakerStatus.ACTIVE,
            BreakerType.SYSTEM_HEALTH: BreakerStatus.ACTIVE,
            BreakerType.MARKET_VOLATILITY: BreakerStatus.ACTIVE,
            BreakerType.TIME_BASED: BreakerStatus.ACTIVE
        }

        self.breaker_events = []
        self.trading_halted = False
        self.halt_reason = None

        self.logger.info("Circuit Breakers initialized")

    def check_all_breakers(
        self,
        daily_stats: Dict,
        system_stats: Dict,
        market_data: Dict,
        current_time: datetime
    ) -> bool:
        """
        Check all circuit breaker conditions

        Args:
            daily_stats: Daily trading statistics
            system_stats: System health statistics
            market_data: Current market data (VIX, etc.)
            current_time: Current time

        Returns:
            True if any breaker triggered (trading should halt)
        """
        # Reset halt status for fresh check
        any_triggered = False

        # Breaker 1: Daily Loss Limit (REQ-RISK-017)
        if self._check_daily_loss_limit(daily_stats):
            any_triggered = True

        # Breaker 2: Consecutive Losses (REQ-RISK-018)
        if self._check_consecutive_losses(daily_stats):
            any_triggered = True

        # Breaker 3: Margin Alert (REQ-RISK-019)
        if self._check_margin_utilization(system_stats):
            any_triggered = True

        # Breaker 4: System Health (REQ-RISK-020)
        if self._check_system_health(system_stats):
            any_triggered = True

        # Breaker 5: Market Volatility (REQ-RISK-019)
        if self._check_market_volatility(market_data):
            any_triggered = True

        # Breaker 6: Time-Based (REQ-RISK-019)
        if self._check_time_based(current_time):
            any_triggered = True

        self.trading_halted = any_triggered

        return any_triggered

    def _check_daily_loss_limit(self, daily_stats: Dict) -> bool:
        """
        Breaker 1: Daily Loss Limit
        Trigger: Daily P&L <= -₹5,000 (configurable)
        Action: Halt all new trades, monitor existing positions
        """
        max_daily_loss = self.breakers_config.get('daily_loss_limit', 5000)
        current_pnl = daily_stats.get('daily_pnl', 0)

        if current_pnl <= -max_daily_loss:
            if self.breakers_status[BreakerType.DAILY_LOSS] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.DAILY_LOSS,
                    trigger_time=datetime.now(),
                    trigger_value=current_pnl,
                    threshold_value=-max_daily_loss,
                    message=(
                        f"Daily loss limit breached! "
                        f"P&L: ₹{current_pnl:.2f} <= Limit: ₹{-max_daily_loss:.2f}"
                    ),
                    recovery_action=(
                        "Manual review required. Reset at market open next day."
                    )
                )
                self._trigger_breaker(BreakerType.DAILY_LOSS, event)
            return True

        return False

    def _check_consecutive_losses(self, daily_stats: Dict) -> bool:
        """
        Breaker 2: Consecutive Losses
        Trigger: 5 consecutive losing trades
        Action: Halt trading, perform system review
        Rationale: Indicates market conditions or strategy mismatch
        """
        max_consecutive = self.breakers_config.get('consecutive_losses', 5)
        consecutive_losses = daily_stats.get('consecutive_losses', 0)

        if consecutive_losses >= max_consecutive:
            if self.breakers_status[BreakerType.CONSECUTIVE_LOSSES] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.CONSECUTIVE_LOSSES,
                    trigger_time=datetime.now(),
                    trigger_value=consecutive_losses,
                    threshold_value=max_consecutive,
                    message=(
                        f"Consecutive losses breaker triggered! "
                        f"{consecutive_losses} consecutive losses"
                    ),
                    recovery_action=(
                        "Manual confirmation required after system review."
                    )
                )
                self._trigger_breaker(BreakerType.CONSECUTIVE_LOSSES, event)
            return True

        return False

    def _check_margin_utilization(self, system_stats: Dict) -> bool:
        """
        Breaker 3: Margin Alert
        Trigger: Margin utilization > 80%
        Action: Prevent new positions, consider closing positions
        """
        margin_critical = self.config.get('margin_utilization_critical', 80)
        margin_used_pct = system_stats.get('margin_utilization_pct', 0)

        if margin_used_pct > margin_critical:
            if self.breakers_status[BreakerType.MARGIN_ALERT] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.MARGIN_ALERT,
                    trigger_time=datetime.now(),
                    trigger_value=margin_used_pct,
                    threshold_value=margin_critical,
                    message=(
                        f"Margin utilization critical! "
                        f"{margin_used_pct:.1f}% > {margin_critical}%"
                    ),
                    recovery_action=(
                        f"Reduce positions to <70% margin usage. "
                        f"Current: {margin_used_pct:.1f}%"
                    )
                )
                self._trigger_breaker(BreakerType.MARGIN_ALERT, event)
            return True

        return False

    def _check_system_health(self, system_stats: Dict) -> bool:
        """
        Breaker 4: System Health
        Trigger: API latency > 2 seconds consistently
        Action: Pause trading, alert operator
        """
        max_latency_ms = self.breakers_config.get('api_latency_ms', 2000)
        current_latency_ms = system_stats.get('api_latency_ms', 0)

        if current_latency_ms > max_latency_ms:
            if self.breakers_status[BreakerType.SYSTEM_HEALTH] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.SYSTEM_HEALTH,
                    trigger_time=datetime.now(),
                    trigger_value=current_latency_ms,
                    threshold_value=max_latency_ms,
                    message=(
                        f"System health critical! "
                        f"API latency {current_latency_ms}ms > {max_latency_ms}ms"
                    ),
                    recovery_action=(
                        "Verify connection quality, restart if needed."
                    )
                )
                self._trigger_breaker(BreakerType.SYSTEM_HEALTH, event)
            return True

        return False

    def _check_market_volatility(self, market_data: Dict) -> bool:
        """
        Breaker 5: Market Volatility
        Trigger: VIX > 40 (extreme volatility)
        Action: Halt new entries, tighten stops on existing
        Rationale: Extreme volatility invalidates strategy assumptions
        """
        max_vix = self.breakers_config.get('max_vix', 40)
        current_vix = market_data.get('vix', 0)

        if current_vix > max_vix:
            if self.breakers_status[BreakerType.MARKET_VOLATILITY] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.MARKET_VOLATILITY,
                    trigger_time=datetime.now(),
                    trigger_value=current_vix,
                    threshold_value=max_vix,
                    message=(
                        f"Extreme market volatility! "
                        f"VIX {current_vix:.2f} > {max_vix}"
                    ),
                    recovery_action=(
                        f"Resume when VIX < 35. Current: {current_vix:.2f}"
                    )
                )
                self._trigger_breaker(BreakerType.MARKET_VOLATILITY, event)
            return True

        # Auto-recovery when VIX drops below 35
        if current_vix < 35 and self.breakers_status[BreakerType.MARKET_VOLATILITY] == BreakerStatus.TRIGGERED:
            self.logger.info(f"VIX recovered to {current_vix:.2f}. Resetting volatility breaker.")
            self.breakers_status[BreakerType.MARKET_VOLATILITY] = BreakerStatus.RESET

        return False

    def _check_time_based(self, current_time: datetime) -> bool:
        """
        Breaker 6: Time-Based
        Trigger: Time >= 3:00 PM
        Action: No new position entries
        Rationale: Insufficient time to manage position properly
        """
        # Extract hour and minute
        current_hour = current_time.hour
        current_minute = current_time.minute

        # 3:00 PM = 15:00
        if current_hour >= 15:
            if self.breakers_status[BreakerType.TIME_BASED] != BreakerStatus.TRIGGERED:
                event = BreakerEvent(
                    breaker_type=BreakerType.TIME_BASED,
                    trigger_time=current_time,
                    trigger_value=current_hour + current_minute / 60,
                    threshold_value=15.0,
                    message=(
                        f"Time-based breaker triggered at "
                        f"{current_time.strftime('%H:%M:%S')}"
                    ),
                    recovery_action=(
                        "No new entries. Monitor existing positions for exit."
                    )
                )
                self._trigger_breaker(BreakerType.TIME_BASED, event)
            return True

        return False

    def _trigger_breaker(self, breaker_type: BreakerType, event: BreakerEvent):
        """
        Trigger a circuit breaker

        Args:
            breaker_type: Type of breaker
            event: Breaker event details
        """
        self.breakers_status[breaker_type] = BreakerStatus.TRIGGERED
        self.breaker_events.append(event)
        self.halt_reason = event.message

        self.logger.critical(
            f"🚨 CIRCUIT BREAKER TRIGGERED: {breaker_type.value}\n"
            f"   Message: {event.message}\n"
            f"   Recovery: {event.recovery_action}"
        )

    def reset_breaker(self, breaker_type: BreakerType, manual: bool = False):
        """
        Reset a circuit breaker

        Args:
            breaker_type: Type of breaker to reset
            manual: True if manual reset (requires confirmation)
        """
        if manual:
            self.logger.warning(
                f"⚠️  MANUAL RESET: {breaker_type.value} circuit breaker"
            )
        else:
            self.logger.info(
                f"✅ AUTO RESET: {breaker_type.value} circuit breaker"
            )

        self.breakers_status[breaker_type] = BreakerStatus.RESET

        # Check if all breakers are reset/active
        all_clear = all(
            status in [BreakerStatus.ACTIVE, BreakerStatus.RESET]
            for status in self.breakers_status.values()
        )

        if all_clear:
            self.trading_halted = False
            self.halt_reason = None
            self.logger.info("✅ All circuit breakers cleared. Trading resumed.")

    def reset_daily_breakers(self):
        """
        Reset breakers at start of new trading day
        """
        self.breakers_status[BreakerType.DAILY_LOSS] = BreakerStatus.ACTIVE
        self.breakers_status[BreakerType.CONSECUTIVE_LOSSES] = BreakerStatus.ACTIVE
        self.breakers_status[BreakerType.TIME_BASED] = BreakerStatus.ACTIVE
        self.trading_halted = False
        self.halt_reason = None
        self.breaker_events = []

        self.logger.info("🔄 Daily circuit breakers reset for new trading day")

    def is_trading_allowed(self) -> bool:
        """
        Check if trading is currently allowed

        Returns:
            True if trading allowed, False if halted
        """
        return not self.trading_halted

    def get_breaker_status(self) -> Dict:
        """
        Get status of all circuit breakers

        Returns:
            Dictionary with breaker statuses
        """
        return {
            'trading_halted': self.trading_halted,
            'halt_reason': self.halt_reason,
            'breakers': {
                breaker.value: status.value
                for breaker, status in self.breakers_status.items()
            },
            'recent_events': [
                {
                    'type': event.breaker_type.value,
                    'time': event.trigger_time.isoformat(),
                    'message': event.message,
                    'recovery': event.recovery_action
                }
                for event in self.breaker_events[-5:]  # Last 5 events
            ]
        }
