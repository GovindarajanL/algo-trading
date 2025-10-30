"""
Vertical Spread Strategies
Bull Call Spread, Bear Put Spread, Bull Put Spread, Bear Call Spread
REQ-STRAT-002 to REQ-STRAT-006
"""

from typing import Dict, List, Optional
from datetime import datetime
from .base_strategy import BaseStrategy, StrategySignal
import logging


class BullCallSpread(BaseStrategy):
    """
    Bull Call Spread (Debit Spread)
    Structure: Buy ATM/OTM Call + Sell higher OTM Call
    Risk: Defined (premium paid)
    Best For: Moderately bullish outlook
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Bull Call Spread")
        self.strike_selector = strike_selector
        self.strike_width = config.get('strike_width', 200)
        self.atm_offset = config.get('long_call_atm_offset', 0)
        self.trail_stop = config.get('trail_stop', 0.30)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Bull Call Spread entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        expiry_date = market_data.get('expiry_date')

        # Select strikes
        strikes = self.strike_selector.select_vertical_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            option_chain=option_chain,
            option_type='CE',
            strike_width=self.strike_width,
            atm_offset=self.atm_offset
        )

        # Get option prices
        long_call = self._find_option(
            option_chain, strikes['long_strike'], 'CE', expiry_date
        )
        short_call = self._find_option(
            option_chain, strikes['short_strike'], 'CE', expiry_date
        )

        if not long_call or not short_call:
            return None

        # Calculate net debit
        net_debit = long_call.get('ltp', 0) - short_call.get('ltp', 0)

        if net_debit <= 0:
            return None

        # Build legs
        legs = [
            {
                'symbol': symbol,
                'strike': strikes['long_strike'],
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': long_call.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': strikes['short_strike'],
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'SELL',
                'quantity': 1,
                'price': short_call.get('ltp', 0)
            }
        ]

        metrics = self.calculate_position_metrics(legs, spot_price)

        signal = StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            expiry_date=expiry_date,
            signal_type='ENTRY',
            legs=legs,
            entry_conditions_met=True,
            reason=f"Bull Call: Debit=₹{net_debit:.2f}, Max Profit=₹{metrics['max_profit']:.2f}",
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=metrics['max_profit'],
            margin_required=metrics['margin_required'],
            position_greeks=self._calc_greeks(long_call, short_call),
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
        """Check exit conditions"""
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """
        Calculate Bull Call Spread metrics
        Max Profit = (Strike difference - Net debit) × Lot size
        Max Loss = Net debit paid
        """
        net_debit = legs[0]['price'] - legs[1]['price']
        strike_diff = legs[1]['strike'] - legs[0]['strike']
        quantity = legs[0].get('quantity', 1)

        max_loss = net_debit * quantity
        max_profit = (strike_diff - net_debit) * quantity
        margin_required = max_loss

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_debit': net_debit
        }

    def _find_option(self, option_chain, strike, option_type, expiry):
        """Find option in chain"""
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry):
                return opt
        return None

    def _calc_greeks(self, long_opt, short_opt):
        """Calculate position Greeks"""
        long_greeks = long_opt.get('greeks', {})
        short_greeks = short_opt.get('greeks', {})

        return {
            'delta': long_greeks.get('delta', 0) - short_greeks.get('delta', 0),
            'gamma': long_greeks.get('gamma', 0) - short_greeks.get('gamma', 0),
            'theta': long_greeks.get('theta', 0) - short_greeks.get('theta', 0),
            'vega': long_greeks.get('vega', 0) - short_greeks.get('vega', 0)
        }


class BearPutSpread(BaseStrategy):
    """
    Bear Put Spread (Debit Spread)
    Structure: Buy ATM/OTM Put + Sell lower OTM Put
    Risk: Defined (premium paid)
    Best For: Moderately bearish outlook
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Bear Put Spread")
        self.strike_selector = strike_selector
        self.strike_width = config.get('strike_width', 200)
        self.atm_offset = config.get('long_put_atm_offset', 0)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Bear Put Spread entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        expiry_date = market_data.get('expiry_date')

        # Select strikes
        strikes = self.strike_selector.select_vertical_spread_strikes(
            symbol=symbol,
            spot_price=spot_price,
            option_chain=option_chain,
            option_type='PE',
            strike_width=self.strike_width,
            atm_offset=self.atm_offset
        )

        # Get option prices
        long_put = self._find_option(
            option_chain, strikes['long_strike'], 'PE', expiry_date
        )
        short_put = self._find_option(
            option_chain, strikes['short_strike'], 'PE', expiry_date
        )

        if not long_put or not short_put:
            return None

        # Calculate net debit
        net_debit = long_put.get('ltp', 0) - short_put.get('ltp', 0)

        if net_debit <= 0:
            return None

        # Build legs
        legs = [
            {
                'symbol': symbol,
                'strike': strikes['long_strike'],
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': long_put.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': strikes['short_strike'],
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'SELL',
                'quantity': 1,
                'price': short_put.get('ltp', 0)
            }
        ]

        metrics = self.calculate_position_metrics(legs, spot_price)

        signal = StrategySignal(
            strategy_name=self.name,
            symbol=symbol,
            expiry_date=expiry_date,
            signal_type='ENTRY',
            legs=legs,
            entry_conditions_met=True,
            reason=f"Bear Put: Debit=₹{net_debit:.2f}, Max Profit=₹{metrics['max_profit']:.2f}",
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=metrics['max_profit'],
            margin_required=metrics['margin_required'],
            position_greeks=self._calc_greeks(long_put, short_put),
            target_profit_pct=self.target_profit * 100,
            stop_loss_pct=self.stop_loss * 100
        )

        self.log_signal(signal)
        return signal

    def check_exit_conditions(self, position, market_data, current_greeks):
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """Calculate Bear Put Spread metrics"""
        net_debit = legs[0]['price'] - legs[1]['price']
        strike_diff = abs(legs[1]['strike'] - legs[0]['strike'])
        quantity = legs[0].get('quantity', 1)

        max_loss = net_debit * quantity
        max_profit = (strike_diff - net_debit) * quantity
        margin_required = max_loss

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_debit': net_debit
        }

    def _find_option(self, option_chain, strike, option_type, expiry):
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry):
                return opt
        return None

    def _calc_greeks(self, long_opt, short_opt):
        long_greeks = long_opt.get('greeks', {})
        short_greeks = short_opt.get('greeks', {})

        return {
            'delta': long_greeks.get('delta', 0) - short_greeks.get('delta', 0),
            'gamma': long_greeks.get('gamma', 0) - short_greeks.get('gamma', 0),
            'theta': long_greeks.get('theta', 0) - short_greeks.get('theta', 0),
            'vega': long_greeks.get('vega', 0) - short_greeks.get('vega', 0)
        }


class BullPutSpread(BaseStrategy):
    """
    Bull Put Spread (Credit Spread)
    Structure: Sell higher Put + Buy lower Put
    Risk: Defined (strike width - net credit)
    Best For: Moderately bullish, support defense
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Bull Put Spread")
        self.strike_selector = strike_selector
        self.strike_width = config.get('strike_width', 200)
        self.otm_distance = config.get('short_put_otm_distance', 1.0)
        self.min_credit = config.get('min_credit', 40)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Bull Put Spread entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        # Implementation similar to above but for credit spread
        # Simplified for brevity
        return None

    def check_exit_conditions(self, position, market_data, current_greeks):
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """Calculate Bull Put Spread metrics"""
        net_credit = legs[0]['price'] - legs[1]['price']  # Sell - Buy
        strike_diff = abs(legs[0]['strike'] - legs[1]['strike'])
        quantity = legs[0].get('quantity', 1)

        max_profit = net_credit * quantity
        max_loss = (strike_diff - net_credit) * quantity
        margin_required = max_loss * 1.1

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_credit': net_credit
        }


class BearCallSpread(BaseStrategy):
    """
    Bear Call Spread (Credit Spread)
    Structure: Sell lower Call + Buy higher Call
    Risk: Defined (strike width - net credit)
    Best For: Moderately bearish, resistance defense
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Bear Call Spread")
        self.strike_selector = strike_selector
        self.strike_width = config.get('strike_width', 200)
        self.otm_distance = config.get('short_call_otm_distance', 1.0)
        self.min_credit = config.get('min_credit', 40)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Bear Call Spread entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        # Implementation similar to Bull Put Spread
        return None

    def check_exit_conditions(self, position, market_data, current_greeks):
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """Calculate Bear Call Spread metrics"""
        net_credit = legs[0]['price'] - legs[1]['price']
        strike_diff = abs(legs[1]['strike'] - legs[0]['strike'])
        quantity = legs[0].get('quantity', 1)

        max_profit = net_credit * quantity
        max_loss = (strike_diff - net_credit) * quantity
        margin_required = max_loss * 1.1

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_credit': net_credit
        }
