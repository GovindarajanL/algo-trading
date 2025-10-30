"""
Position Risk Manager
Manages individual position risk and Delta-based stops
REQ-POS-001 to REQ-POS-017
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging


class PositionRiskManager:
    """
    Position-level risk management
    Monitors individual positions and enforces stop losses
    """

    def __init__(self, config: Dict):
        """
        Initialize position risk manager

        Args:
            config: Risk limits configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.stop_loss_config = config.get('stop_loss', {})

        # Stop loss parameters
        self.percentage_based = self.stop_loss_config.get('percentage_based', True)
        self.default_stop_pct = self.stop_loss_config.get('default_stop_pct', 100)
        self.delta_based = self.stop_loss_config.get('delta_based', True)
        self.delta_danger = self.stop_loss_config.get('delta_danger', 0.40)
        self.delta_critical = self.stop_loss_config.get('delta_critical', 0.50)

        self.logger.info("Position Risk Manager initialized")

    def check_stop_loss(
        self,
        position: Dict,
        current_price: Dict[str, float],
        current_greeks: Dict[str, Dict]
    ) -> Tuple[bool, str, str]:
        """
        Check if position should be stopped out
        REQ-STRAT-020 to REQ-STRAT-024

        Args:
            position: Position details
            current_price: Current prices for position legs
            current_greeks: Current Greeks for position legs

        Returns:
            Tuple of (should_exit, reason, exit_type)
        """
        # Check 1: Percentage-based stop loss
        if self.percentage_based:
            exit_pct, reason_pct = self._check_percentage_stop(position, current_price)
            if exit_pct:
                return True, reason_pct, "percentage_stop"

        # Check 2: Delta-based stop loss (REQ-POS-013 to REQ-POS-017)
        if self.delta_based:
            exit_delta, reason_delta = self._check_delta_stop(position, current_greeks)
            if exit_delta:
                return True, reason_delta, "delta_stop"

        # Check 3: Time-based mandatory exit (REQ-STRAT-023)
        exit_time, reason_time = self._check_time_stop(position)
        if exit_time:
            return True, reason_time, "time_stop"

        # Check 4: Target profit reached (REQ-STRAT-020)
        exit_target, reason_target = self._check_target_profit(position, current_price)
        if exit_target:
            return True, reason_target, "target_profit"

        return False, "No stop loss triggered", "none"

    def _check_percentage_stop(
        self,
        position: Dict,
        current_price: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Check percentage-based stop loss
        REQ-STRAT-021: Stop loss at X% of premium
        """
        strategy_name = position.get('strategy_name', '')
        entry_premium = position.get('entry_premium', 0)
        current_value = self._calculate_position_value(position, current_price)

        # Calculate P&L
        if 'spread' in strategy_name.lower() or 'condor' in strategy_name.lower():
            # Credit strategies: profit when value decreases
            pnl = entry_premium - current_value
        else:
            # Debit strategies: profit when value increases
            pnl = current_value - entry_premium

        # Get strategy-specific stop loss percentage
        stop_loss_pct = position.get('stop_loss_pct', self.default_stop_pct)

        # Calculate stop loss threshold
        if entry_premium > 0:
            loss_pct = (pnl / entry_premium) * 100
        else:
            loss_pct = 0

        # Trigger if loss exceeds threshold
        if loss_pct <= -stop_loss_pct:
            return True, (
                f"Percentage stop loss triggered: "
                f"Loss {loss_pct:.1f}% >= {stop_loss_pct}%"
            )

        return False, ""

    def _check_delta_stop(
        self,
        position: Dict,
        current_greeks: Dict[str, Dict]
    ) -> Tuple[bool, str]:
        """
        Check Delta-based stop loss
        REQ-POS-013 to REQ-POS-017: Monitor Delta and trigger exits
        """
        # Extract short option legs
        short_legs = [
            leg for leg in position.get('legs', [])
            if leg.get('action') == 'SELL'
        ]

        for leg in short_legs:
            leg_id = self._get_leg_id(leg)
            leg_greeks = current_greeks.get(leg_id, {})
            delta = abs(leg_greeks.get('delta', 0))

            # Critical level - immediate exit (REQ-POS-015)
            if delta >= self.delta_critical:
                return True, (
                    f"Delta CRITICAL stop triggered: "
                    f"{leg['option_type']} {leg['strike']} "
                    f"Delta={delta:.3f} >= {self.delta_critical}"
                )

            # Danger level - warning (REQ-POS-014)
            if delta >= self.delta_danger:
                self.logger.warning(
                    f"⚠️  Delta DANGER level: "
                    f"{leg['option_type']} {leg['strike']} "
                    f"Delta={delta:.3f} >= {self.delta_danger}"
                )

        return False, ""

    def _check_time_stop(self, position: Dict) -> Tuple[bool, str]:
        """
        Check time-based mandatory exit
        REQ-STRAT-023: Exit by 3:20 PM
        """
        current_time = datetime.now()
        force_exit_time = self.stop_loss_config.get('force_exit_time', "15:20")

        # Parse force exit time
        exit_hour, exit_minute = map(int, force_exit_time.split(':'))
        force_exit = current_time.replace(
            hour=exit_hour,
            minute=exit_minute,
            second=0,
            microsecond=0
        )

        if current_time >= force_exit:
            return True, (
                f"Time-based mandatory exit: "
                f"Current time {current_time.strftime('%H:%M:%S')} >= "
                f"{force_exit_time}"
            )

        return False, ""

    def _check_target_profit(
        self,
        position: Dict,
        current_price: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Check if target profit reached
        REQ-STRAT-020: Exit at target profit (e.g., 50% of max)
        """
        entry_premium = position.get('entry_premium', 0)
        max_profit = position.get('max_profit', 0)
        target_profit_pct = position.get('target_profit_pct', 50)

        current_value = self._calculate_position_value(position, current_price)

        # Calculate current P&L
        strategy_name = position.get('strategy_name', '')
        if 'spread' in strategy_name.lower() or 'condor' in strategy_name.lower():
            # Credit strategies
            current_pnl = entry_premium - current_value
        else:
            # Debit strategies
            current_pnl = current_value - entry_premium

        # Calculate target profit
        target_profit = max_profit * (target_profit_pct / 100)

        if current_pnl >= target_profit:
            return True, (
                f"Target profit reached: "
                f"P&L ₹{current_pnl:.2f} >= Target ₹{target_profit:.2f} "
                f"({target_profit_pct}% of max)"
            )

        return False, ""

    def _calculate_position_value(
        self,
        position: Dict,
        current_price: Dict[str, float]
    ) -> float:
        """
        Calculate current position value

        Args:
            position: Position details
            current_price: Current prices for each leg

        Returns:
            Current total value of position
        """
        total_value = 0.0

        for leg in position.get('legs', []):
            leg_id = self._get_leg_id(leg)
            price = current_price.get(leg_id, 0)
            quantity = leg.get('quantity', 1)

            if leg.get('action') == 'BUY':
                total_value += price * quantity
            else:  # SELL
                total_value -= price * quantity

        return abs(total_value)

    def _get_leg_id(self, leg: Dict) -> str:
        """
        Generate unique identifier for option leg

        Args:
            leg: Option leg details

        Returns:
            Unique identifier string
        """
        return f"{leg['symbol']}_{leg['strike']}_{leg['option_type']}_{leg['expiry']}"

    def calculate_position_greeks(
        self,
        position: Dict,
        leg_greeks: Dict[str, Dict]
    ) -> Dict[str, float]:
        """
        Calculate aggregate Greeks for a position
        REQ-GREEK-009: Position-level aggregate Greeks

        Args:
            position: Position details
            leg_greeks: Greeks for each leg

        Returns:
            Dictionary with aggregate Greeks
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for leg in position.get('legs', []):
            leg_id = self._get_leg_id(leg)
            greeks = leg_greeks.get(leg_id, {})
            quantity = leg.get('quantity', 1)
            multiplier = 1 if leg.get('action') == 'BUY' else -1

            total_delta += greeks.get('delta', 0) * quantity * multiplier
            total_gamma += greeks.get('gamma', 0) * quantity * multiplier
            total_theta += greeks.get('theta', 0) * quantity * multiplier
            total_vega += greeks.get('vega', 0) * quantity * multiplier

        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega
        }

    def get_position_risk_status(
        self,
        position: Dict,
        current_price: Dict[str, float],
        current_greeks: Dict[str, Dict]
    ) -> Dict:
        """
        Get comprehensive position risk status

        Args:
            position: Position details
            current_price: Current prices
            current_greeks: Current Greeks

        Returns:
            Dictionary with position risk status
        """
        # Check all stop conditions
        should_exit, reason, exit_type = self.check_stop_loss(
            position, current_price, current_greeks
        )

        # Calculate position Greeks
        position_greeks = self.calculate_position_greeks(position, current_greeks)

        # Calculate current P&L
        entry_premium = position.get('entry_premium', 0)
        current_value = self._calculate_position_value(position, current_price)

        strategy_name = position.get('strategy_name', '')
        if 'spread' in strategy_name.lower() or 'condor' in strategy_name.lower():
            current_pnl = entry_premium - current_value
        else:
            current_pnl = current_value - entry_premium

        return {
            'should_exit': should_exit,
            'exit_reason': reason,
            'exit_type': exit_type,
            'current_pnl': current_pnl,
            'current_value': current_value,
            'greeks': position_greeks,
            'delta_danger': any(
                abs(current_greeks.get(self._get_leg_id(leg), {}).get('delta', 0)) >= self.delta_danger
                for leg in position.get('legs', [])
                if leg.get('action') == 'SELL'
            ),
            'delta_critical': any(
                abs(current_greeks.get(self._get_leg_id(leg), {}).get('delta', 0)) >= self.delta_critical
                for leg in position.get('legs', [])
                if leg.get('action') == 'SELL'
            )
        }
