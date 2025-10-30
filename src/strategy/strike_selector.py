"""
Strike Selector
IV-based strike selection using standard deviation method
REQ-STRAT-009 to REQ-STRAT-013
"""

import math
from typing import Dict, List, Optional, Tuple
import logging


class StrikeSelector:
    """
    Select option strikes based on implied volatility and probability
    Uses standard deviation approach for probability-based strike selection
    """

    def __init__(self, iv_calculator, strike_intervals: Dict):
        """
        Initialize strike selector

        Args:
            iv_calculator: ImpliedVolatilityCalculator instance
            strike_intervals: Strike intervals for each symbol
        """
        self.logger = logging.getLogger(__name__)
        self.iv_calculator = iv_calculator
        self.strike_intervals = strike_intervals

    def select_strikes_by_sd(
        self,
        symbol: str,
        spot_price: float,
        option_chain: List[Dict],
        days_to_expiry: int,
        sd_distance: float,
        wing_width: float
    ) -> Dict:
        """
        Select strikes using standard deviation method
        REQ-STRAT-009 to REQ-STRAT-012

        For Iron Condor:
        - Short strikes: Spot ± (SD × Expected move)
        - Long strikes: Short strikes ± Wing width

        Args:
            symbol: Underlying symbol (NIFTY/BANKNIFTY)
            spot_price: Current spot price
            option_chain: Available option chain
            days_to_expiry: Days to expiry
            sd_distance: Standard deviations from spot (e.g., 1.0)
            wing_width: Distance between short and long strikes

        Returns:
            Dictionary with selected strikes
        """
        # Calculate ATM IV (REQ-STRAT-010)
        time_to_expiry = days_to_expiry / 365
        atm_iv = self.iv_calculator.calculate_atm_iv(
            option_chain=option_chain,
            spot_price=spot_price,
            time_to_expiry=time_to_expiry
        )

        if not atm_iv:
            self.logger.warning("Could not calculate ATM IV, using default 0.18")
            atm_iv = 0.18  # Default 18% IV

        # Calculate expected move (REQ-STRAT-011)
        expected_move = self.iv_calculator.calculate_expected_move(
            spot_price=spot_price,
            atm_iv=atm_iv,
            days_to_expiry=days_to_expiry
        )

        self.logger.info(
            f"Strike selection: Spot={spot_price:.2f}, IV={atm_iv:.2%}, "
            f"Expected Move=±{expected_move:.2f} (1 SD)"
        )

        # Calculate short strikes
        short_call_strike_raw = spot_price + (sd_distance * expected_move)
        short_put_strike_raw = spot_price - (sd_distance * expected_move)

        # Round to valid strike intervals (REQ-STRAT-013)
        strike_interval = self.strike_intervals.get(symbol, 50)
        short_call_strike = self._round_to_strike(short_call_strike_raw, strike_interval)
        short_put_strike = self._round_to_strike(short_put_strike_raw, strike_interval)

        # Calculate long strikes (protective wings)
        long_call_strike = self._round_to_strike(
            short_call_strike + wing_width, strike_interval
        )
        long_put_strike = self._round_to_strike(
            short_put_strike - wing_width, strike_interval
        )

        # Verify strikes exist in option chain
        strikes = self._get_available_strikes(option_chain)

        if not all(s in strikes for s in [
            short_call_strike, short_put_strike,
            long_call_strike, long_put_strike
        ]):
            self.logger.warning("Some selected strikes not available in chain")
            return self._select_strikes_fallback(
                spot_price, strikes, strike_interval, wing_width
            )

        # Calculate probabilities (REQ-STRAT-012)
        call_prob_otm = self._calculate_probability_otm(
            spot_price, short_call_strike, atm_iv, days_to_expiry, 'CE'
        )
        put_prob_otm = self._calculate_probability_otm(
            spot_price, short_put_strike, atm_iv, days_to_expiry, 'PE'
        )

        result = {
            'short_call_strike': short_call_strike,
            'long_call_strike': long_call_strike,
            'short_put_strike': short_put_strike,
            'long_put_strike': long_put_strike,
            'atm_iv': atm_iv,
            'expected_move': expected_move,
            'call_prob_otm': call_prob_otm,
            'put_prob_otm': put_prob_otm,
            'prob_profit': call_prob_otm * put_prob_otm  # Both need to stay OTM
        }

        self.logger.info(
            f"Selected strikes - Call: {short_call_strike}/{long_call_strike}, "
            f"Put: {short_put_strike}/{long_put_strike} | "
            f"PoP: {result['prob_profit']:.1%}"
        )

        return result

    def select_vertical_spread_strikes(
        self,
        symbol: str,
        spot_price: float,
        option_chain: List[Dict],
        option_type: str,
        strike_width: float,
        atm_offset: int = 0
    ) -> Dict:
        """
        Select strikes for vertical spreads (bull call, bear put)
        REQ-STRAT-009 to REQ-STRAT-013

        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            option_chain: Available option chain
            option_type: 'CE' or 'PE'
            strike_width: Distance between long and short strikes
            atm_offset: Strikes from ATM (0=ATM, 1=1 strike OTM)

        Returns:
            Dictionary with selected strikes
        """
        strike_interval = self.strike_intervals.get(symbol, 50)
        strikes = sorted(self._get_available_strikes(option_chain))

        # Find ATM strike
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))

        if option_type.upper() in ['CE', 'CALL']:
            # Bull call spread: Buy ATM/OTM call, Sell higher call
            long_strike = atm_strike + (atm_offset * strike_interval)
            short_strike = long_strike + strike_width
        else:  # PUT
            # Bear put spread: Buy ATM/OTM put, Sell lower put
            long_strike = atm_strike - (atm_offset * strike_interval)
            short_strike = long_strike - strike_width

        # Round to valid strikes
        long_strike = self._round_to_strike(long_strike, strike_interval)
        short_strike = self._round_to_strike(short_strike, strike_interval)

        # Verify availability
        if long_strike not in strikes or short_strike not in strikes:
            self.logger.warning("Selected strikes not available, using fallback")
            # Use available strikes closest to calculated ones
            long_strike = min(strikes, key=lambda x: abs(x - long_strike))
            short_strike = min(strikes, key=lambda x: abs(x - short_strike))

        return {
            'long_strike': long_strike,
            'short_strike': short_strike,
            'strike_width': abs(short_strike - long_strike),
            'atm_strike': atm_strike
        }

    def _round_to_strike(self, price: float, interval: int) -> float:
        """
        Round price to nearest valid strike
        REQ-STRAT-013: Round to valid strike intervals
        """
        return round(price / interval) * interval

    def _get_available_strikes(self, option_chain: List[Dict]) -> set:
        """Get set of available strikes from option chain"""
        return set(opt['strike'] for opt in option_chain)

    def _calculate_probability_otm(
        self,
        spot_price: float,
        strike: float,
        iv: float,
        days_to_expiry: int,
        option_type: str
    ) -> float:
        """
        Calculate probability of option expiring OTM
        REQ-STRAT-012: Probability-based strike selection
        """
        from scipy.stats import norm

        time_to_expiry = days_to_expiry / 365

        if time_to_expiry <= 0:
            return 1.0 if (
                (option_type == 'CE' and spot_price < strike) or
                (option_type == 'PE' and spot_price > strike)
            ) else 0.0

        try:
            # Simplified probability calculation
            d2 = (
                (math.log(spot_price / strike) + (0.065 - 0.5 * iv ** 2) * time_to_expiry) /
                (iv * math.sqrt(time_to_expiry))
            )

            if option_type.upper() in ['CE', 'CALL']:
                prob_otm = norm.cdf(-d2)  # Probability of expiring below strike
            else:  # PUT
                prob_otm = norm.cdf(d2)  # Probability of expiring above strike

            return prob_otm

        except Exception as e:
            self.logger.error(f"Error calculating probability: {e}")
            return 0.5  # Default 50%

    def _select_strikes_fallback(
        self,
        spot_price: float,
        strikes: set,
        strike_interval: int,
        wing_width: float
    ) -> Dict:
        """Fallback strike selection if IV-based selection fails"""
        strikes_list = sorted(strikes)

        # Find ATM
        atm_strike = min(strikes_list, key=lambda x: abs(x - spot_price))

        # Simple selection: 2-3 strikes away from ATM
        short_distance = 2 * strike_interval
        wing_strikes = int(wing_width / strike_interval)

        short_call = atm_strike + short_distance
        long_call = short_call + (wing_strikes * strike_interval)
        short_put = atm_strike - short_distance
        long_put = short_put - (wing_strikes * strike_interval)

        # Ensure valid strikes
        short_call = min(strikes_list, key=lambda x: abs(x - short_call))
        long_call = min(strikes_list, key=lambda x: abs(x - long_call))
        short_put = min(strikes_list, key=lambda x: abs(x - short_put))
        long_put = min(strikes_list, key=lambda x: abs(x - long_put))

        self.logger.warning("Using fallback strike selection")

        return {
            'short_call_strike': short_call,
            'long_call_strike': long_call,
            'short_put_strike': short_put,
            'long_put_strike': long_put,
            'atm_iv': 0.18,  # Default
            'expected_move': 0,
            'call_prob_otm': 0.84,  # Assume 1 SD
            'put_prob_otm': 0.84,
            'prob_profit': 0.70
        }
