"""
Volatility Strategies
Long Straddle, Long Strangle, Iron Butterfly
REQ-STRAT-006 to REQ-STRAT-008
"""

from typing import Dict, List, Optional
from datetime import datetime
from .base_strategy import BaseStrategy, StrategySignal
import logging


class LongStraddle(BaseStrategy):
    """
    Long Straddle (Volatility Play)
    Structure: Buy ATM Call + Buy ATM Put
    Risk: Defined (total premium paid)
    Best For: Major events, expecting large movement
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Long Straddle")
        self.strike_selector = strike_selector
        self.max_vix = config.get('max_vix', 25)
        self.exit_same_day = config.get('exit_same_day', True)
        self.event_driven = config.get('event_driven', True)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """
        Generate Long Straddle entry signal
        Entry when expecting significant price movement (direction unknown)
        """
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        expiry_date = market_data.get('expiry_date')
        vix = market_data.get('vix', 0)

        # Check VIX - prefer low VIX for cheaper entry
        if vix > self.max_vix:
            return None

        # Find ATM strike
        atm_strike = self._find_atm_strike(option_chain, spot_price)
        if not atm_strike:
            return None

        # Get ATM call and put
        atm_call = self._find_option(option_chain, atm_strike, 'CE', expiry_date)
        atm_put = self._find_option(option_chain, atm_strike, 'PE', expiry_date)

        if not atm_call or not atm_put:
            return None

        # Calculate total premium
        total_premium = atm_call.get('ltp', 0) + atm_put.get('ltp', 0)

        # Build legs
        legs = [
            {
                'symbol': symbol,
                'strike': atm_strike,
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': atm_call.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': atm_strike,
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': atm_put.get('ltp', 0)
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
            reason=f"Straddle: Premium=₹{total_premium:.2f}, VIX={vix:.1f}",
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=float('inf'),  # Theoretically unlimited
            margin_required=metrics['margin_required'],
            position_greeks=self._calc_greeks(atm_call, atm_put),
            target_profit_pct=self.target_profit * 100,
            stop_loss_pct=self.stop_loss * 100
        )

        self.log_signal(signal)
        return signal

    def check_exit_conditions(self, position, market_data, current_greeks):
        """Long straddle should exit same day or next day due to theta decay"""
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """
        Calculate Long Straddle metrics
        Max Loss = Total premium paid
        Max Profit = Unlimited (theoretically)
        """
        total_premium = sum(leg['price'] for leg in legs)
        quantity = legs[0].get('quantity', 1)

        max_loss = total_premium * quantity
        max_profit = float('inf')  # Unlimited
        margin_required = max_loss

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'total_premium': total_premium
        }

    def _find_atm_strike(self, option_chain, spot_price):
        """Find ATM strike closest to spot"""
        strikes = list(set(opt['strike'] for opt in option_chain))
        if not strikes:
            return None
        return min(strikes, key=lambda x: abs(x - spot_price))

    def _find_option(self, option_chain, strike, option_type, expiry):
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry):
                return opt
        return None

    def _calc_greeks(self, call_opt, put_opt):
        call_greeks = call_opt.get('greeks', {})
        put_greeks = put_opt.get('greeks', {})

        return {
            'delta': call_greeks.get('delta', 0) + put_greeks.get('delta', 0),
            'gamma': call_greeks.get('gamma', 0) + put_greeks.get('gamma', 0),
            'theta': call_greeks.get('theta', 0) + put_greeks.get('theta', 0),
            'vega': call_greeks.get('vega', 0) + put_greeks.get('vega', 0)
        }


class LongStrangle(BaseStrategy):
    """
    Long Strangle (Cheaper Volatility Play)
    Structure: Buy OTM Call + Buy OTM Put
    Risk: Defined (total premium paid, less than straddle)
    Best For: Very large expected moves
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Long Strangle")
        self.strike_selector = strike_selector
        self.call_otm_strikes = config.get('call_otm_strikes', 2)
        self.put_otm_strikes = config.get('put_otm_strikes', 2)
        self.max_vix = config.get('max_vix', 25)
        self.exit_same_day = config.get('exit_same_day', True)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Long Strangle entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        expiry_date = market_data.get('expiry_date')
        vix = market_data.get('vix', 0)

        if vix > self.max_vix:
            return None

        # Find ATM strike
        atm_strike = self._find_atm_strike(option_chain, spot_price)
        if not atm_strike:
            return None

        # Get strike interval
        strike_interval = 100 if 'BANKNIFTY' in symbol.upper() else 50

        # Calculate OTM strikes
        call_strike = atm_strike + (self.call_otm_strikes * strike_interval)
        put_strike = atm_strike - (self.put_otm_strikes * strike_interval)

        # Get options
        otm_call = self._find_option(option_chain, call_strike, 'CE', expiry_date)
        otm_put = self._find_option(option_chain, put_strike, 'PE', expiry_date)

        if not otm_call or not otm_put:
            return None

        # Calculate total premium
        total_premium = otm_call.get('ltp', 0) + otm_put.get('ltp', 0)

        # Build legs
        legs = [
            {
                'symbol': symbol,
                'strike': call_strike,
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': otm_call.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': put_strike,
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': otm_put.get('ltp', 0)
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
            reason=f"Strangle: Premium=₹{total_premium:.2f}, VIX={vix:.1f}",
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=float('inf'),
            margin_required=metrics['margin_required'],
            position_greeks=self._calc_greeks(otm_call, otm_put),
            target_profit_pct=self.target_profit * 100,
            stop_loss_pct=self.stop_loss * 100
        )

        self.log_signal(signal)
        return signal

    def check_exit_conditions(self, position, market_data, current_greeks):
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """Calculate Long Strangle metrics"""
        total_premium = sum(leg['price'] for leg in legs)
        quantity = legs[0].get('quantity', 1)

        max_loss = total_premium * quantity
        max_profit = float('inf')
        margin_required = max_loss

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'total_premium': total_premium
        }

    def _find_atm_strike(self, option_chain, spot_price):
        strikes = list(set(opt['strike'] for opt in option_chain))
        if not strikes:
            return None
        return min(strikes, key=lambda x: abs(x - spot_price))

    def _find_option(self, option_chain, strike, option_type, expiry):
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry):
                return opt
        return None

    def _calc_greeks(self, call_opt, put_opt):
        call_greeks = call_opt.get('greeks', {})
        put_greeks = put_opt.get('greeks', {})

        return {
            'delta': call_greeks.get('delta', 0) + put_greeks.get('delta', 0),
            'gamma': call_greeks.get('gamma', 0) + put_greeks.get('gamma', 0),
            'theta': call_greeks.get('theta', 0) + put_greeks.get('theta', 0),
            'vega': call_greeks.get('vega', 0) + put_greeks.get('vega', 0)
        }


class IronButterfly(BaseStrategy):
    """
    Iron Butterfly
    Structure: Buy OTM Call + Sell 2 ATM (Call & Put) + Buy OTM Put
    Risk: Defined (wing width - net credit)
    Best For: Very low volatility, tight range
    """

    def __init__(self, config: Dict, strike_selector):
        super().__init__(config, name="Iron Butterfly")
        self.strike_selector = strike_selector
        self.wing_width = config.get('wing_width', 300)
        self.max_vix = config.get('max_vix', 25)
        self.min_credit = config.get('min_credit', 100)
        self.delta_stop = config.get('delta_stop', 0.45)

    def generate_entry_signal(
        self,
        market_data: Dict,
        option_chain: List[Dict],
        current_positions: List[Dict]
    ) -> Optional[StrategySignal]:
        """Generate Iron Butterfly entry signal"""
        conditions_met, reason = self.check_entry_conditions_common(
            market_data, current_positions
        )
        if not conditions_met:
            return None

        symbol = market_data.get('symbol')
        spot_price = market_data.get('spot_price')
        expiry_date = market_data.get('expiry_date')
        vix = market_data.get('vix', 0)

        if vix > self.max_vix:
            return None

        # Find ATM strike
        atm_strike = self._find_atm_strike(option_chain, spot_price)
        if not atm_strike:
            return None

        # Calculate wing strikes
        long_call_strike = atm_strike + self.wing_width
        long_put_strike = atm_strike - self.wing_width

        # Get options
        atm_call = self._find_option(option_chain, atm_strike, 'CE', expiry_date)
        atm_put = self._find_option(option_chain, atm_strike, 'PE', expiry_date)
        long_call = self._find_option(option_chain, long_call_strike, 'CE', expiry_date)
        long_put = self._find_option(option_chain, long_put_strike, 'PE', expiry_date)

        if not all([atm_call, atm_put, long_call, long_put]):
            return None

        # Calculate net credit
        net_credit = (
            atm_call.get('ltp', 0) + atm_put.get('ltp', 0) -
            long_call.get('ltp', 0) - long_put.get('ltp', 0)
        )

        if net_credit < self.min_credit:
            return None

        # Build legs
        legs = [
            {
                'symbol': symbol,
                'strike': long_put_strike,
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': long_put.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': atm_strike,
                'option_type': 'PE',
                'expiry': expiry_date,
                'action': 'SELL',
                'quantity': 1,
                'price': atm_put.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': atm_strike,
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'SELL',
                'quantity': 1,
                'price': atm_call.get('ltp', 0)
            },
            {
                'symbol': symbol,
                'strike': long_call_strike,
                'option_type': 'CE',
                'expiry': expiry_date,
                'action': 'BUY',
                'quantity': 1,
                'price': long_call.get('ltp', 0)
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
            reason=f"Iron Butterfly: Credit=₹{net_credit:.2f}, Max Loss=₹{metrics['max_loss']:.2f}",
            timestamp=datetime.now(),
            max_loss=metrics['max_loss'],
            max_profit=metrics['max_profit'],
            margin_required=metrics['margin_required'],
            position_greeks={'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0},
            target_profit_pct=self.target_profit * 100,
            stop_loss_pct=self.stop_loss * 100
        )

        self.log_signal(signal)
        return signal

    def check_exit_conditions(self, position, market_data, current_greeks):
        return False, "Delegated to PositionRiskManager"

    def calculate_position_metrics(self, legs: List[Dict], spot_price: float) -> Dict:
        """
        Calculate Iron Butterfly metrics
        Max Profit = Net credit
        Max Loss = (Wing width - Net credit) × Lot size
        """
        net_credit = (legs[1]['price'] + legs[2]['price'] -
                     legs[0]['price'] - legs[3]['price'])
        wing_width = legs[3]['strike'] - legs[2]['strike']
        quantity = legs[0].get('quantity', 1)

        max_profit = net_credit * quantity
        max_loss = (wing_width - net_credit) * quantity
        margin_required = max_loss * 1.1

        return {
            'max_loss': max_loss,
            'max_profit': max_profit,
            'margin_required': margin_required,
            'net_credit': net_credit
        }

    def _find_atm_strike(self, option_chain, spot_price):
        strikes = list(set(opt['strike'] for opt in option_chain))
        if not strikes:
            return None
        return min(strikes, key=lambda x: abs(x - spot_price))

    def _find_option(self, option_chain, strike, option_type, expiry):
        for opt in option_chain:
            if (opt['strike'] == strike and
                opt['option_type'] == option_type and
                opt.get('expiry_date') == expiry):
                return opt
        return None
