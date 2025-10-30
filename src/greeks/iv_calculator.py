"""
Implied Volatility Calculator
Calculates IV from market prices using Newton-Raphson method
REQ-GREEK-006: Calculate Implied Volatility from market prices
"""

import math
from typing import Optional
import logging


class ImpliedVolatilityCalculator:
    """
    Calculate implied volatility from market option prices
    Uses Newton-Raphson iterative method
    """

    def __init__(self, black_scholes_calculator):
        """
        Initialize IV calculator

        Args:
            black_scholes_calculator: Instance of BlackScholesCalculator
        """
        self.logger = logging.getLogger(__name__)
        self.bs_calc = black_scholes_calculator

        # Newton-Raphson parameters
        self.max_iterations = 100
        self.tolerance = 0.0001
        self.initial_guess = 0.30  # 30% initial IV guess

    def calculate_iv(
        self,
        market_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        option_type: str,
        dividend_yield: float = 0.0,
        initial_guess: Optional[float] = None
    ) -> Optional[float]:
        """
        Calculate implied volatility from market price
        REQ-GREEK-006: Calculate IV from market prices

        Args:
            market_price: Market price of the option
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            option_type: 'CE' for call, 'PE' for put
            dividend_yield: Annual dividend yield
            initial_guess: Initial IV guess (default: 0.30)

        Returns:
            Implied volatility (annual) or None if calculation fails
        """
        # Validation
        if market_price <= 0:
            self.logger.warning(f"Invalid market price: {market_price}")
            return None

        if time_to_expiry <= 0:
            self.logger.warning("Cannot calculate IV for expired option")
            return None

        # Check intrinsic value
        if option_type.upper() in ['CE', 'CALL']:
            intrinsic = max(spot_price - strike_price, 0)
        else:
            intrinsic = max(strike_price - spot_price, 0)

        if market_price < intrinsic:
            self.logger.warning(
                f"Market price {market_price:.2f} < Intrinsic {intrinsic:.2f}"
            )
            return None

        # Use provided initial guess or default
        volatility = initial_guess if initial_guess else self.initial_guess

        # Newton-Raphson iteration
        for iteration in range(self.max_iterations):
            # Calculate theoretical price with current volatility
            theoretical_price = self.bs_calc.calculate_price(
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                option_type=option_type,
                dividend_yield=dividend_yield
            )

            # Calculate price difference
            price_diff = theoretical_price - market_price

            # Check convergence
            if abs(price_diff) < self.tolerance:
                # Validate reasonable IV range (5% to 200%)
                if 0.05 <= volatility <= 2.0:
                    return volatility
                else:
                    self.logger.warning(
                        f"IV {volatility:.4f} outside reasonable range"
                    )
                    return None

            # Calculate vega for Newton-Raphson
            greeks = self.bs_calc.calculate_greeks(
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                option_type=option_type,
                dividend_yield=dividend_yield
            )

            vega = greeks['vega'] * 100  # Convert back to per 100% change

            # Avoid division by zero
            if abs(vega) < 1e-10:
                self.logger.warning("Vega too small for Newton-Raphson")
                return None

            # Newton-Raphson update
            volatility_new = volatility - price_diff / vega

            # Ensure volatility stays positive and reasonable
            volatility_new = max(0.01, min(volatility_new, 3.0))

            # Check if stuck
            if abs(volatility_new - volatility) < 1e-8:
                break

            volatility = volatility_new

        # Failed to converge
        self.logger.warning(
            f"IV calculation did not converge after {self.max_iterations} iterations "
            f"(Market: {market_price:.2f}, Last IV: {volatility:.4f})"
        )
        return None

    def calculate_atm_iv(
        self,
        option_chain: list,
        spot_price: float,
        time_to_expiry: float,
        dividend_yield: float = 0.0
    ) -> Optional[float]:
        """
        Calculate ATM (at-the-money) implied volatility
        Used for strike selection and expected move calculation

        Args:
            option_chain: List of options with strikes, prices, and types
            spot_price: Current price of underlying
            time_to_expiry: Time to expiry in years
            dividend_yield: Annual dividend yield

        Returns:
            ATM implied volatility or None
        """
        # Find ATM strike (closest to spot)
        atm_strike = self._find_atm_strike(option_chain, spot_price)

        if atm_strike is None:
            self.logger.warning("Could not find ATM strike")
            return None

        # Get ATM call and put prices
        atm_call = next(
            (opt for opt in option_chain
             if opt['strike'] == atm_strike and opt['option_type'] in ['CE', 'CALL']),
            None
        )

        atm_put = next(
            (opt for opt in option_chain
             if opt['strike'] == atm_strike and opt['option_type'] in ['PE', 'PUT']),
            None
        )

        ivs = []

        # Calculate IV for ATM call
        if atm_call and atm_call.get('ltp', 0) > 0:
            call_iv = self.calculate_iv(
                market_price=atm_call['ltp'],
                spot_price=spot_price,
                strike_price=atm_strike,
                time_to_expiry=time_to_expiry,
                option_type='CE',
                dividend_yield=dividend_yield
            )
            if call_iv:
                ivs.append(call_iv)

        # Calculate IV for ATM put
        if atm_put and atm_put.get('ltp', 0) > 0:
            put_iv = self.calculate_iv(
                market_price=atm_put['ltp'],
                spot_price=spot_price,
                strike_price=atm_strike,
                time_to_expiry=time_to_expiry,
                option_type='PE',
                dividend_yield=dividend_yield
            )
            if put_iv:
                ivs.append(put_iv)

        # Average of call and put IVs
        if ivs:
            atm_iv = sum(ivs) / len(ivs)
            self.logger.debug(f"ATM IV: {atm_iv:.4f} (strike: {atm_strike})")
            return atm_iv

        return None

    def calculate_expected_move(
        self,
        spot_price: float,
        atm_iv: float,
        days_to_expiry: int
    ) -> float:
        """
        Calculate expected move based on IV
        Formula: Expected Move = Spot × IV × √(DTE / 365)

        Args:
            spot_price: Current price of underlying
            atm_iv: ATM implied volatility (annual)
            days_to_expiry: Days to expiry

        Returns:
            Expected move in points (1 standard deviation)
        """
        if days_to_expiry <= 0:
            return 0.0

        time_factor = math.sqrt(days_to_expiry / 365)
        expected_move = spot_price * atm_iv * time_factor

        self.logger.debug(
            f"Expected move: ±{expected_move:.2f} points "
            f"(Spot: {spot_price:.2f}, IV: {atm_iv:.2%}, DTE: {days_to_expiry})"
        )

        return expected_move

    def calculate_strike_for_probability(
        self,
        spot_price: float,
        atm_iv: float,
        days_to_expiry: int,
        probability_otm: float,
        option_type: str
    ) -> float:
        """
        Calculate strike price for desired probability of expiring OTM
        Used for strike selection in strategies

        Args:
            spot_price: Current price of underlying
            atm_iv: ATM implied volatility
            days_to_expiry: Days to expiry
            probability_otm: Desired probability of expiring OTM (e.g., 0.84 for 1 SD)
            option_type: 'CE' for call, 'PE' for put

        Returns:
            Strike price
        """
        # Standard deviation mapping
        # 68% (1 SD) → 0.84 OTM, 95% (2 SD) → 0.975 OTM
        from scipy.stats import norm

        # Convert probability OTM to z-score
        z_score = norm.ppf(probability_otm)

        # Calculate expected move
        expected_move = self.calculate_expected_move(spot_price, atm_iv, days_to_expiry)

        # Calculate strike
        if option_type.upper() in ['CE', 'CALL']:
            # For calls, move up from spot
            strike = spot_price + (z_score * expected_move / math.sqrt(days_to_expiry / 365))
        else:  # PUT
            # For puts, move down from spot
            strike = spot_price - (z_score * expected_move / math.sqrt(days_to_expiry / 365))

        return strike

    def _find_atm_strike(self, option_chain: list, spot_price: float) -> Optional[float]:
        """
        Find ATM strike (closest to spot price)

        Args:
            option_chain: List of options
            spot_price: Current price of underlying

        Returns:
            ATM strike or None
        """
        if not option_chain:
            return None

        strikes = list(set(opt['strike'] for opt in option_chain))
        strikes.sort()

        # Find closest strike to spot
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))

        return atm_strike

    def validate_iv_surface(self, option_chain: list, spot_price: float, time_to_expiry: float) -> Dict:
        """
        Validate IV surface for anomalies
        Check for reasonable IV skew and term structure

        Args:
            option_chain: Complete option chain
            spot_price: Current spot price
            time_to_expiry: Time to expiry in years

        Returns:
            Dictionary with validation results
        """
        warnings = []
        ivs = []

        for option in option_chain:
            if option.get('ltp', 0) > 0:
                iv = self.calculate_iv(
                    market_price=option['ltp'],
                    spot_price=spot_price,
                    strike_price=option['strike'],
                    time_to_expiry=time_to_expiry,
                    option_type=option['option_type']
                )
                if iv:
                    ivs.append({
                        'strike': option['strike'],
                        'type': option['option_type'],
                        'iv': iv,
                        'moneyness': option['strike'] / spot_price
                    })

        if not ivs:
            warnings.append("No valid IVs calculated")
            return {'valid': False, 'warnings': warnings}

        # Check for extreme IVs
        iv_values = [item['iv'] for item in ivs]
        min_iv = min(iv_values)
        max_iv = max(iv_values)

        if min_iv < 0.10:
            warnings.append(f"Very low IV detected: {min_iv:.2%}")

        if max_iv > 1.50:
            warnings.append(f"Very high IV detected: {max_iv:.2%}")

        # Check IV range
        iv_range = max_iv - min_iv
        if iv_range > 0.50:
            warnings.append(f"Wide IV range: {iv_range:.2%}")

        return {
            'valid': len(warnings) == 0,
            'warnings': warnings,
            'min_iv': min_iv,
            'max_iv': max_iv,
            'iv_range': iv_range,
            'iv_count': len(ivs)
        }
