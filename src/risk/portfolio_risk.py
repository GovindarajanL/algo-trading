"""
Portfolio Risk Manager
Manages portfolio-level Greeks and risk metrics
REQ-RISK-011 to REQ-RISK-016
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging


@dataclass
class PortfolioGreeks:
    """Portfolio aggregate Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    total_positions: int
    total_capital_allocated: float
    net_premium: float


class PortfolioRiskManager:
    """
    Portfolio-level risk management
    Tracks aggregate Greeks and enforces portfolio limits
    """

    def __init__(self, config: Dict):
        """
        Initialize portfolio risk manager

        Args:
            config: Risk limits configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.greeks_limits = config.get('portfolio_greeks', {})

        # Portfolio Greeks limits
        self.max_delta = self.greeks_limits.get('max_delta', 500)
        self.max_gamma = self.greeks_limits.get('max_gamma', 100)
        self.min_theta = self.greeks_limits.get('min_theta', -1000)
        self.max_vega = self.greeks_limits.get('max_vega', 1000)
        self.delta_neutral_tolerance = self.greeks_limits.get('delta_neutral_tolerance', 50)

        self.logger.info("Portfolio Risk Manager initialized")

    def calculate_portfolio_greeks(
        self,
        positions: List[Dict]
    ) -> PortfolioGreeks:
        """
        Calculate aggregate portfolio Greeks
        REQ-RISK-011 to REQ-RISK-014

        Args:
            positions: List of open positions with their Greeks

        Returns:
            PortfolioGreeks with aggregated values
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_capital = 0.0
        net_premium = 0.0

        for position in positions:
            greeks = position.get('current_greeks', {})
            quantity = position.get('quantity', 1)

            # Aggregate Greeks (weighted by quantity)
            total_delta += greeks.get('delta', 0) * quantity
            total_gamma += greeks.get('gamma', 0) * quantity
            total_theta += greeks.get('theta', 0) * quantity
            total_vega += greeks.get('vega', 0) * quantity

            # Capital and premium
            total_capital += position.get('capital_allocated', 0)
            net_premium += position.get('entry_premium', 0)

        portfolio_greeks = PortfolioGreeks(
            delta=total_delta,
            gamma=total_gamma,
            theta=total_theta,
            vega=total_vega,
            total_positions=len(positions),
            total_capital_allocated=total_capital,
            net_premium=net_premium
        )

        self.logger.debug(
            f"Portfolio Greeks: Δ={total_delta:.2f}, Γ={total_gamma:.2f}, "
            f"Θ={total_theta:.2f}, ν={total_vega:.2f}"
        )

        return portfolio_greeks

    def check_portfolio_limits(
        self,
        portfolio_greeks: PortfolioGreeks
    ) -> Tuple[bool, List[str]]:
        """
        Check if portfolio Greeks are within limits
        REQ-RISK-015, REQ-RISK-016

        Args:
            portfolio_greeks: Current portfolio Greeks

        Returns:
            Tuple of (all_ok: bool, violations: List[str])
        """
        violations = []

        # Check Delta (REQ-RISK-011, REQ-RISK-016)
        if abs(portfolio_greeks.delta) > self.max_delta:
            violations.append(
                f"Delta limit breach: {portfolio_greeks.delta:.2f} "
                f"(limit: ±{self.max_delta})"
            )

        # Delta neutrality warning
        if abs(portfolio_greeks.delta) > self.delta_neutral_tolerance:
            violations.append(
                f"Delta neutrality warning: {portfolio_greeks.delta:.2f} "
                f"(tolerance: ±{self.delta_neutral_tolerance})"
            )

        # Check Gamma (REQ-RISK-012)
        if abs(portfolio_greeks.gamma) > self.max_gamma:
            violations.append(
                f"Gamma limit breach: {portfolio_greeks.gamma:.2f} "
                f"(limit: ±{self.max_gamma})"
            )

        # Check Theta (REQ-RISK-013)
        if portfolio_greeks.theta < self.min_theta:
            violations.append(
                f"Theta limit breach: {portfolio_greeks.theta:.2f} "
                f"(limit: >={self.min_theta})"
            )

        # Check Vega (REQ-RISK-014)
        if abs(portfolio_greeks.vega) > self.max_vega:
            violations.append(
                f"Vega limit breach: {portfolio_greeks.vega:.2f} "
                f"(limit: ±{self.max_vega})"
            )

        all_ok = len(violations) == 0

        if not all_ok:
            self.logger.warning(
                f"⚠️  Portfolio limits violated:\n   " +
                "\n   ".join(violations)
            )

        return all_ok, violations

    def suggest_hedge(
        self,
        portfolio_greeks: PortfolioGreeks
    ) -> Dict:
        """
        Suggest hedging action if Greeks are out of balance

        Args:
            portfolio_greeks: Current portfolio Greeks

        Returns:
            Dictionary with hedge suggestions
        """
        suggestions = []

        # Delta hedge suggestion
        if abs(portfolio_greeks.delta) > self.delta_neutral_tolerance:
            direction = "SELL" if portfolio_greeks.delta > 0 else "BUY"
            hedge_amount = abs(portfolio_greeks.delta)
            suggestions.append({
                'greek': 'delta',
                'action': f"{direction} futures/options to reduce Delta",
                'amount': hedge_amount,
                'reason': f"Portfolio Delta {portfolio_greeks.delta:.2f} outside tolerance"
            })

        # Gamma hedge suggestion
        if abs(portfolio_greeks.gamma) > self.max_gamma * 0.8:  # 80% threshold
            suggestions.append({
                'greek': 'gamma',
                'action': "Consider reducing position sizes or adjusting strikes",
                'amount': abs(portfolio_greeks.gamma),
                'reason': f"Portfolio Gamma {portfolio_greeks.gamma:.2f} near limit"
            })

        # Theta warning
        if portfolio_greeks.theta < self.min_theta * 0.8:  # 80% threshold
            suggestions.append({
                'greek': 'theta',
                'action': "High negative theta - monitor time decay exposure",
                'amount': abs(portfolio_greeks.theta),
                'reason': f"Portfolio Theta {portfolio_greeks.theta:.2f} near limit"
            })

        # Vega hedge suggestion
        if abs(portfolio_greeks.vega) > self.max_vega * 0.8:  # 80% threshold
            suggestions.append({
                'greek': 'vega',
                'action': "Reduce volatility exposure by closing positions",
                'amount': abs(portfolio_greeks.vega),
                'reason': f"Portfolio Vega {portfolio_greeks.vega:.2f} near limit"
            })

        return {
            'hedge_required': len(suggestions) > 0,
            'suggestions': suggestions
        }

    def calculate_portfolio_risk_metrics(
        self,
        positions: List[Dict],
        portfolio_greeks: PortfolioGreeks
    ) -> Dict:
        """
        Calculate additional portfolio risk metrics

        Args:
            positions: List of open positions
            portfolio_greeks: Current portfolio Greeks

        Returns:
            Dictionary with risk metrics
        """
        if not positions:
            return {
                'total_max_loss': 0,
                'total_max_profit': 0,
                'risk_reward_ratio': 0,
                'capital_utilization_pct': 0,
                'concentration_risk': 0
            }

        total_max_loss = sum(pos.get('max_loss', 0) for pos in positions)
        total_max_profit = sum(pos.get('max_profit', 0) for pos in positions)
        total_capital = self.config.get('total_capital', 50000)

        # Risk-Reward Ratio
        risk_reward = (
            total_max_profit / total_max_loss
            if total_max_loss > 0 else 0
        )

        # Capital Utilization
        capital_utilization_pct = (
            portfolio_greeks.total_capital_allocated / total_capital * 100
            if total_capital > 0 else 0
        )

        # Concentration Risk (Herfindahl Index)
        # Measures how concentrated the portfolio is
        capital_shares = [
            (pos.get('capital_allocated', 0) / portfolio_greeks.total_capital_allocated) ** 2
            for pos in positions
            if portfolio_greeks.total_capital_allocated > 0
        ]
        concentration_risk = sum(capital_shares) if capital_shares else 0

        return {
            'total_max_loss': total_max_loss,
            'total_max_profit': total_max_profit,
            'risk_reward_ratio': risk_reward,
            'capital_utilization_pct': capital_utilization_pct,
            'concentration_risk': concentration_risk,  # 0=diversified, 1=concentrated
            'net_premium': portfolio_greeks.net_premium
        }

    def get_portfolio_status(
        self,
        positions: List[Dict]
    ) -> Dict:
        """
        Get comprehensive portfolio status

        Args:
            positions: List of open positions

        Returns:
            Dictionary with complete portfolio status
        """
        portfolio_greeks = self.calculate_portfolio_greeks(positions)
        limits_ok, violations = self.check_portfolio_limits(portfolio_greeks)
        hedge_suggestions = self.suggest_hedge(portfolio_greeks)
        risk_metrics = self.calculate_portfolio_risk_metrics(positions, portfolio_greeks)

        return {
            'greeks': {
                'delta': portfolio_greeks.delta,
                'gamma': portfolio_greeks.gamma,
                'theta': portfolio_greeks.theta,
                'vega': portfolio_greeks.vega
            },
            'limits': {
                'within_limits': limits_ok,
                'violations': violations
            },
            'hedge': hedge_suggestions,
            'metrics': risk_metrics,
            'positions_count': portfolio_greeks.total_positions,
            'capital_allocated': portfolio_greeks.total_capital_allocated
        }
