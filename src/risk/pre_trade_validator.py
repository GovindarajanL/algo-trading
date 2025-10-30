"""
Pre-Trade Validator
Implements 6-layer validation before trade execution
REQ-RISK-001 to REQ-RISK-026
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging


class ValidationResult(Enum):
    """Validation result status"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class TradeSignal:
    """Trade signal structure"""
    strategy_name: str
    symbol: str
    expiry_date: str
    legs: List[Dict]  # List of option legs
    max_loss: float
    max_profit: float
    margin_required: float
    position_greeks: Dict[str, float]
    timestamp: str


@dataclass
class ValidationResponse:
    """Validation response structure"""
    status: ValidationResult
    approved: bool
    reason: str
    failed_checks: List[str]
    checks_passed: Dict[str, bool]


class PreTradeValidator:
    """
    Pre-trade validation engine
    Implements comprehensive 6-layer validation
    """

    def __init__(self, config: Dict):
        """
        Initialize pre-trade validator

        Args:
            config: Risk limits configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.risk_limits = config.get('risk_limits', {})

        # Prohibited strategies
        self.prohibited_strategies = self.risk_limits.get('prohibited_strategies', [
            'naked_call',
            'naked_put',
            'short_straddle_unhedged',
            'short_strangle_unhedged',
            'ratio_spread_unhedged'
        ])

        self.logger.info("Pre-Trade Validator initialized")

    def validate_trade(
        self,
        signal: TradeSignal,
        current_positions: List[Dict],
        daily_stats: Dict
    ) -> ValidationResponse:
        """
        Validate trade signal through all checks

        Args:
            signal: Trade signal to validate
            current_positions: List of current open positions
            daily_stats: Daily statistics (P&L, trades count, etc.)

        Returns:
            ValidationResponse with approval status and reasons
        """
        checks_passed = {}
        failed_checks = []

        # Check 1: Defined Risk Verification (REQ-RISK-001, REQ-RISK-004)
        check1_pass, check1_msg = self._check_defined_risk(signal)
        checks_passed['defined_risk'] = check1_pass
        if not check1_pass:
            failed_checks.append(f"Defined Risk: {check1_msg}")

        # Check 2: Maximum Loss Acceptability (REQ-RISK-002)
        check2_pass, check2_msg = self._check_max_loss_acceptable(signal)
        checks_passed['max_loss_acceptable'] = check2_pass
        if not check2_pass:
            failed_checks.append(f"Max Loss: {check2_msg}")

        # Check 3: Capital Availability (REQ-RISK-003)
        check3_pass, check3_msg = self._check_capital_available(
            signal, current_positions
        )
        checks_passed['capital_available'] = check3_pass
        if not check3_pass:
            failed_checks.append(f"Capital: {check3_msg}")

        # Check 4: Position Limits (REQ-RISK-009)
        check4_pass, check4_msg = self._check_position_limits(current_positions)
        checks_passed['position_limits'] = check4_pass
        if not check4_pass:
            failed_checks.append(f"Position Limits: {check4_msg}")

        # Check 5: Daily Loss Limit (REQ-RISK-006, REQ-RISK-007)
        check5_pass, check5_msg = self._check_daily_loss_limit(signal, daily_stats)
        checks_passed['daily_loss_limit'] = check5_pass
        if not check5_pass:
            failed_checks.append(f"Daily Loss: {check5_msg}")

        # Check 6: Strategy Whitelist (REQ-RISK-022 to REQ-RISK-026)
        check6_pass, check6_msg = self._check_strategy_whitelist(signal)
        checks_passed['strategy_whitelist'] = check6_pass
        if not check6_pass:
            failed_checks.append(f"Strategy: {check6_msg}")

        # Determine overall approval
        all_passed = all(checks_passed.values())

        if all_passed:
            self.logger.info(
                f"✅ Trade APPROVED: {signal.strategy_name} {signal.symbol} "
                f"Max Loss: ₹{signal.max_loss:.2f}"
            )
            return ValidationResponse(
                status=ValidationResult.APPROVED,
                approved=True,
                reason="All validation checks passed",
                failed_checks=[],
                checks_passed=checks_passed
            )
        else:
            rejection_reason = " | ".join(failed_checks)
            self.logger.warning(
                f"❌ Trade REJECTED: {signal.strategy_name} {signal.symbol} "
                f"Reason: {rejection_reason}"
            )
            return ValidationResponse(
                status=ValidationResult.REJECTED,
                approved=False,
                reason=rejection_reason,
                failed_checks=failed_checks,
                checks_passed=checks_passed
            )

    def _check_defined_risk(self, signal: TradeSignal) -> Tuple[bool, str]:
        """
        Check 1: Defined Risk Verification
        REQ-RISK-001: Every trade must have defined maximum loss
        REQ-RISK-004: Reject any trade with infinite/undefined risk
        """
        # Check if max_loss is defined and finite
        if signal.max_loss is None:
            return False, "Maximum loss is not defined"

        if signal.max_loss == float('inf'):
            return False, "Maximum loss is infinite (PROHIBITED)"

        if signal.max_loss <= 0:
            return False, f"Invalid max loss: ₹{signal.max_loss}"

        # Verify hedging for short options
        has_short_options = any(leg.get('action') == 'SELL' for leg in signal.legs)

        if has_short_options:
            # Ensure there are corresponding long options (hedges)
            short_calls = [leg for leg in signal.legs
                          if leg.get('action') == 'SELL' and leg.get('option_type') == 'CE']
            short_puts = [leg for leg in signal.legs
                         if leg.get('action') == 'SELL' and leg.get('option_type') == 'PE']

            long_calls = [leg for leg in signal.legs
                         if leg.get('action') == 'BUY' and leg.get('option_type') == 'CE']
            long_puts = [leg for leg in signal.legs
                        if leg.get('action') == 'BUY' and leg.get('option_type') == 'PE']

            # Verify each short option has protection
            if short_calls and not long_calls:
                return False, "Short calls without protective long calls (naked call PROHIBITED)"

            if short_puts and not long_puts:
                return False, "Short puts without protective long puts (naked put PROHIBITED)"

        return True, f"Defined risk: ₹{signal.max_loss:.2f}"

    def _check_max_loss_acceptable(self, signal: TradeSignal) -> Tuple[bool, str]:
        """
        Check 2: Maximum Loss Acceptability
        REQ-RISK-002: Max loss per trade must not exceed limit
        """
        max_loss_per_trade = self.risk_limits.get('max_loss_per_trade', 1000)

        if signal.max_loss > max_loss_per_trade:
            return False, (
                f"Max loss ₹{signal.max_loss:.2f} exceeds limit "
                f"₹{max_loss_per_trade:.2f}"
            )

        return True, f"Max loss ₹{signal.max_loss:.2f} within limit"

    def _check_capital_available(
        self,
        signal: TradeSignal,
        current_positions: List[Dict]
    ) -> Tuple[bool, str]:
        """
        Check 3: Capital Availability
        REQ-RISK-003: Position size based on available capital
        """
        total_capital = self.risk_limits.get('total_capital', 50000)
        reserved_capital_pct = self.risk_limits.get('reserved_capital_pct', 20)

        # Calculate allocated capital
        allocated_capital = sum(
            pos.get('capital_allocated', 0) for pos in current_positions
        )

        # Calculate available capital (excluding reserved)
        available_capital = total_capital * (1 - reserved_capital_pct / 100) - allocated_capital

        # Required capital is max loss + margin
        required_capital = signal.max_loss + signal.margin_required

        if required_capital > available_capital:
            return False, (
                f"Required capital ₹{required_capital:.2f} exceeds "
                f"available ₹{available_capital:.2f}"
            )

        return True, f"Capital available: ₹{available_capital:.2f}"

    def _check_position_limits(self, current_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Check 4: Position Limits
        REQ-RISK-009: Limit maximum concurrent positions
        """
        max_positions = self.risk_limits.get('max_positions', 5)
        current_count = len(current_positions)

        if current_count >= max_positions:
            return False, (
                f"Position limit reached: {current_count}/{max_positions}"
            )

        return True, f"Positions: {current_count}/{max_positions}"

    def _check_daily_loss_limit(
        self,
        signal: TradeSignal,
        daily_stats: Dict
    ) -> Tuple[bool, str]:
        """
        Check 5: Daily Loss Limit
        REQ-RISK-006: Track cumulative daily P&L
        REQ-RISK-007: Halt if daily loss exceeds limit
        """
        max_daily_loss = self.risk_limits.get('max_daily_loss', 5000)
        current_daily_pnl = daily_stats.get('daily_pnl', 0)

        # Check if already breached
        if current_daily_pnl <= -max_daily_loss:
            return False, (
                f"Daily loss limit breached: ₹{current_daily_pnl:.2f}"
            )

        # Check if potential loss would breach limit
        potential_pnl = current_daily_pnl - signal.max_loss
        if potential_pnl <= -max_daily_loss:
            return False, (
                f"Potential loss would breach daily limit: "
                f"₹{potential_pnl:.2f}"
            )

        return True, f"Daily P&L: ₹{current_daily_pnl:.2f}"

    def _check_strategy_whitelist(self, signal: TradeSignal) -> Tuple[bool, str]:
        """
        Check 6: Strategy Whitelist
        REQ-RISK-022 to REQ-RISK-026: Prohibited strategies
        """
        strategy_lower = signal.strategy_name.lower().replace(' ', '_')

        if strategy_lower in self.prohibited_strategies:
            return False, (
                f"Strategy '{signal.strategy_name}' is PROHIBITED"
            )

        return True, f"Strategy '{signal.strategy_name}' approved"

    def calculate_position_size(
        self,
        signal: TradeSignal,
        risk_capital: float
    ) -> int:
        """
        Calculate appropriate position size
        REQ-RISK-003: Position sizing formula

        Position Size = (Risk Capital × Risk%) / Max Loss Per Lot

        Args:
            signal: Trade signal
            risk_capital: Total allocated capital

        Returns:
            Number of lots to trade
        """
        risk_pct = self.risk_limits.get('risk_per_trade_pct', 2) / 100
        max_lot_size = self.risk_limits.get('max_lot_size', 5)

        # Calculate optimal size
        risk_amount = risk_capital * risk_pct
        optimal_lots = int(risk_amount / signal.max_loss)

        # Apply maximum limit
        position_size = min(optimal_lots, max_lot_size)

        # Ensure at least 1 lot if affordable
        if position_size == 0 and signal.max_loss <= risk_amount:
            position_size = 1

        self.logger.info(
            f"Position sizing: Risk ₹{risk_amount:.2f} / "
            f"Max Loss ₹{signal.max_loss:.2f} = {optimal_lots} lots "
            f"(capped at {position_size})"
        )

        return position_size
