"""
Iron Condor Strategy
Four-leg neutral strategy combining bull put and bear call spreads
REQ-STRAT-001: Iron Condor implementation
"""

from typing import Dict, List, Optional
from datetime import datetime
from .base_strategy import BaseStrategy, StrategySignal
import logging


class IronCondorStrategy(BaseStrategy):
    """
    Iron Condor Strategy
    Structure: Buy OTM Put + Sell OTM Put + Sell OTM Call + Buy OTM Call
    Risk: Defined (strike width - net credit)
    Best For: Low volatility, range-bound markets
    """

    def __init__(self, config: Dict, strike_selector):
        """
        Initialize Iron Condor strategy

        Args:
            config: Strategy configuration from strategy_params.yaml
            strike_selector: StrikeSelector instance
        """
        super().__init__(config, name="Iron Condor")
        self.strike_selector = strike_selector

        # Strategy-specific parameters
        self.sd_distance = config.get('sd_distance', 1.0)
        self.wing_width = config.get('wing_width', 200)
        self.min_credit = config.get('min_credit', 50)
        self.delta_stop = config.get('delta_stop', 0.50)

        self.logger.info(
            f"Iron Condor initialized: SD={self.sd_distance}, "
            f"Wing={self.wing_width}, Min Credit={self.min_credit}"
        )

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """
        Generate Iron Condor entry signal
        REQ-STRAT-014 to REQ-STRAT-019

        Entry Conditions:
        - Low volatility (VIX < max_vix)
        - Range-bound market
        - DTE: 5-15 days
        - Minimum credit threshold met
        - Time window: 9:20 AM - 2:00 PM
        """
        # Check common conditions
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        # Extract market data
        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        days_to_expiry = market_data.get('days_to_expiry')
        expiry_date = market_data.get('expiry_date')

        # Select strikes using IV-based method (REQ-STRAT-009 to REQ-STRAT-013)
        strikes = self.strike_selector.select_strikes_by_sd(
            symbol=symbol,
            spot_price=spot_price,
            option_chain=option_chain,
            days_to_expiry=days_to_expiry,
            sd_distance=self.sd_distance,
            wing_width=self.wing_width
        )

        # Get option prices from chain
        legs_data = self._get_option_prices(option_chain, strikes, expiry_date)
        if not legs_data:
            self.logger.warning("Could not find all required options in chain")
            return None

        # Calculate expected credit
        net_credit = self._calculate_net_credit(legs_data)

        # Check minimum credit threshold (REQ-STRAT-018)
        if net_credit < self.min_credit:
            self.logger.debug(
                f"Credit {net_credit:.2f} below minimum {self.min_credit}"
            )
            return None

        # Build leg structure
        legs = self._build_legs(legs_data, strikes)

        # Calculate position metrics (REQ-RISK-001)
        metrics = self.calculate_position_metrics(legs, spot_price)

        # Calculate position Greeks
        position_greeks = self._calculate_position_greeks(legs_data)

        # Create signal
        signal = StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            expiry_date=expiry_date,
            signal_type='ENTRY',
            legs=legs,
            entry_conditions_met=True,
            reason=(
                f"Iron Condor setup: Credit=₹{net_credit:.2f}, "
                f"PoP={strikes['prob_profit']:.1%}, "
                f"Max Loss=₹{metrics['max_loss']:.2f}"
            ),
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=metrics['max_profit'],
            margin_required=metrics['margin_required'],
            position_greeks=position_greeks,
            target_profit_pct=self.target_profit * 100,
            stop_loss_pct=self.stop_loss * 100
        )

        self.log_signal(signal)
        return signal

    def check_exit_conditions(
        self,
        position: Dict,
        market_data: Dict,
        current_greeks: Dict
    ) -> tuple[bool, str]:
        """
        Check Iron Condor exit conditions
        REQ-STRAT-020 to REQ-STRAT-024

        Exit Conditions:
        - Target profit: 50% of max profit
        - Stop loss: 100% of credit received
        - Delta stop: Short option Delta >= 0.50
        - Time: Exit by 3:15 PM
        """
        # This will be called by PositionRiskManager
        # Implementation handled by base risk management
        return False, "Exit check delegated to PositionRiskManager"

    def calculate_position_metrics(
        self,
        legs: List[Dict],
        spot_price: float
    ) -> Dict:
        """
        Calculate Iron Condor risk metrics
        REQ-RISK-001: Define maximum loss

        Max Profit = Net credit received
        Max Loss = (Strike width - Net credit) × Lot size
        """
        # Calculate net credit
        net_credit = 0
        for leg in legs:
            price = leg.get('price', 0)
            quantity = leg.get('quantity', 1)
            if leg['action'] == 'SELL':
                net_credit += price * quantity
            else:  # BUY
                net_credit -= price * quantity

        # Get strike width (distance between short and long on same side)
        call_legs = [l for l in legs if l['option_type'] == 'CE']
        put_legs = [l for l in legs if l['option_type'] == 'PE']

        # Call spread width
        call_strikes = sorted([l['strike'] for l in call_legs])
        call_width = call_strikes[-1] - call_strikes[0] if len(call_strikes) == 2 else 0

        # Put spread width
        put_strikes = sorted([l['strike'] for l in put_legs])
        put_width = put_strikes[-1] - put_strikes[0] if len(put_strikes) == 2 else 0

        # Max loss is the larger of the two spreads minus net credit
        max_width = max(call_width, put_width)
        quantity = legs[0].get('quantity', 1) if legs else 1

        max_loss = (max_width - net_credit) * quantity
        max_profit = net_credit * quantity

        # Margin required (approximate)
        margin_required = max_loss * 1.1  # 10% buffer

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_credit': net_credit,
            'call_width': call_width,
            'put_width': put_width
        }

    def _get_option_prices(
        self,
        option_chain: List[Dict],
        strikes: Dict,
        expiry_date: str
    ) -> Optional[Dict]:
        """Get option prices for all legs from option chain"""
        # Find options in chain
        long_call = self._find_option(
            option_chain, strikes['long_call_strike'], 'CE', expiry_date
        )
        short_call = self._find_option(
            option_chain, strikes['short_call_strike'], 'CE', expiry_date
        )
        short_put = self._find_option(
            option_chain, strikes['short_put_strike'], 'PE', expiry_date
        )
        long_put = self._find_option(
            option_chain, strikes['long_put_strike'], 'PE', expiry_date
        )

        if not all([long_call, short_call, short_put, long_put]):
            return None

        return {
            'long_call': long_call,
            'short_call': short_call,
            'short_put': short_put,
            'long_put': long_put
        }

    def _find_option(
        self,
        option_chain: List[Dict],
        strike: float,
        option_type: str,
        expiry_date: str
    ) -> Optional[Dict]:
        """Find specific option in chain"""
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry_date):
                return opt
        return None

    def _calculate_net_credit(self, legs_data: Dict) -> float:
        """Calculate net credit received"""
        credit = 0
        credit += legs_data['short_call'].get('ltp', 0)  # Sell call
        credit += legs_data['short_put'].get('ltp', 0)   # Sell put
        credit -= legs_data['long_call'].get('ltp', 0)   # Buy call
        credit -= legs_data['long_put'].get('ltp', 0)    # Buy put
        return credit

    def _build_legs(self, legs_data: Dict, strikes: Dict) -> List[Dict]:
        """Build leg structure for signal"""
        symbol = legs_data['long_call']['symbol']
        expiry = legs_data['long_call'].get('expiry_date')

        return [
            {
                'symbol': symbol,
                'strike': strikes['long_put_strike'],
                'option_type': 'PE',
                'expiry': expiry,
                'action': 'BUY',
                'quantity': 1,
                'price': legs_data['long_put'].get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': strikes['short_put_strike'],
                'option_type': 'PE',
                'expiry': expiry,
                'action': 'SELL',
                'quantity': 1,
                'price': legs_data['short_put'].get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': strikes['short_call_strike'],
                'option_type': 'CE',
                'expiry': expiry,
                'action': 'SELL',
                'quantity': 1,
                'price': legs_data['short_call'].get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': strikes['long_call_strike'],
                'option_type': 'CE',
                'expiry': expiry,
                'action': 'BUY',
                'quantity': 1,
                'price': legs_data['long_call'].get('ltp', 0)
            }
        ]

    def _calculate_position_greeks(self, legs_data: Dict) -> Dict[str, float]:
        """Calculate aggregate position Greeks"""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0

        for leg_name, leg_data in legs_data.items():
            greeks = leg_data.get('greeks', {})
            multiplier = -1 if 'short' in leg_name else 1

            total_delta += greeks.get('delta', 0) * multiplier
            total_gamma += greeks.get('gamma', 0) * multiplier
            total_theta += greeks.get('theta', 0) * multiplier
            total_vega += greeks.get('vega', 0) * multiplier

        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega
        }
