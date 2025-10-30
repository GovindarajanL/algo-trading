"""
Black-Scholes-Merton Option Pricing Model
Calculates option prices and Greeks
REQ-GREEK-001 to REQ-GREEK-007, REQ-GREEK-013, REQ-GREEK-014
"""

import math
from typing import Dict, Optional
from scipy.stats import norm
import logging


class BlackScholesCalculator:
    """
    Black-Scholes-Merton model for European options
    Calculates theoretical prices and Greeks
    """

    def __init__(self, risk_free_rate: float = 0.065):
        """
        Initialize Black-Scholes calculator

        Args:
            risk_free_rate: Annual risk-free rate (default: 6.5% for Indian T-Bill)
        """
        self.logger = logging.getLogger(__name__)
        self.risk_free_rate = risk_free_rate
        self.logger.info(f"Black-Scholes Calculator initialized (r={risk_free_rate:.4f})")

    def calculate_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> float:
        """
        Calculate theoretical option price
        REQ-GREEK-005: Black-Scholes-Merton model

        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (annual)
            option_type: 'CE' for call, 'PE' for put
            dividend_yield: Annual dividend yield (default: 0)

        Returns:
            Theoretical option price
        """
        if time_to_expiry <= 0:
            # Handle expired/expiring options (REQ-GREEK-007)
            return self._intrinsic_value(spot_price, strike_price, option_type)

        try:
            d1, d2 = self._calculate_d1_d2(
                spot_price, strike_price, time_to_expiry, volatility, dividend_yield
            )

            if option_type.upper() in ['CE', 'CALL']:
                price = (
                    spot_price * math.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1) -
                    strike_price * math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
                )
            elif option_type.upper() in ['PE', 'PUT']:
                price = (
                    strike_price * math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2) -
                    spot_price * math.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1)
                )
            else:
                raise ValueError(f"Invalid option type: {option_type}")

            return max(price, 0)  # Price cannot be negative

        except Exception as e:
            self.logger.error(f"Error calculating price: {e}")
            return self._intrinsic_value(spot_price, strike_price, option_type)

    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate all Greeks for an option
        REQ-GREEK-001 to REQ-GREEK-004: Calculate Delta, Gamma, Theta, Vega

        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (annual)
            option_type: 'CE' for call, 'PE' for put
            dividend_yield: Annual dividend yield

        Returns:
            Dictionary with all Greeks
        """
        if time_to_expiry <= 0:
            # Handle expired options (REQ-GREEK-007)
            return self._expired_greeks(spot_price, strike_price, option_type)

        try:
            d1, d2 = self._calculate_d1_d2(
                spot_price, strike_price, time_to_expiry, volatility, dividend_yield
            )

            # Calculate Greeks
            delta = self._calculate_delta(d1, option_type, time_to_expiry, dividend_yield)
            gamma = self._calculate_gamma(spot_price, d1, time_to_expiry, volatility, dividend_yield)
            theta = self._calculate_theta(
                spot_price, strike_price, d1, d2, time_to_expiry, volatility, option_type, dividend_yield
            )
            vega = self._calculate_vega(spot_price, d1, time_to_expiry, dividend_yield)
            rho = self._calculate_rho(strike_price, d2, time_to_expiry, option_type)

            # Validate Greeks (REQ-GREEK-013)
            greeks = {
                'delta': self._validate_greek(delta, 'delta', -1, 1),
                'gamma': self._validate_greek(gamma, 'gamma', 0, 1),
                'theta': theta,  # Theta can be negative
                'vega': self._validate_greek(vega, 'vega', 0, None),
                'rho': rho
            }

            return greeks

        except Exception as e:
            self.logger.error(f"Error calculating Greeks: {e}")
            return self._default_greeks()

    def _calculate_d1_d2(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        dividend_yield: float
    ) -> tuple:
        """Calculate d1 and d2 for Black-Scholes formula"""
        d1 = (
            (math.log(spot_price / strike_price) +
             (self.risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_to_expiry) /
            (volatility * math.sqrt(time_to_expiry))
        )
        d2 = d1 - volatility * math.sqrt(time_to_expiry)
        return d1, d2

    def _calculate_delta(
        self,
        d1: float,
        option_type: str,
        time_to_expiry: float,
        dividend_yield: float
    ) -> float:
        """
        Calculate Delta
        REQ-GREEK-001: Delta calculation
        """
        if option_type.upper() in ['CE', 'CALL']:
            delta = math.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1)
        else:  # PUT
            delta = -math.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1)
        return delta

    def _calculate_gamma(
        self,
        spot_price: float,
        d1: float,
        time_to_expiry: float,
        volatility: float,
        dividend_yield: float
    ) -> float:
        """
        Calculate Gamma
        REQ-GREEK-002: Gamma calculation
        """
        gamma = (
            math.exp(-dividend_yield * time_to_expiry) * norm.pdf(d1) /
            (spot_price * volatility * math.sqrt(time_to_expiry))
        )
        return gamma

    def _calculate_theta(
        self,
        spot_price: float,
        strike_price: float,
        d1: float,
        d2: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        dividend_yield: float
    ) -> float:
        """
        Calculate Theta (time decay)
        REQ-GREEK-003: Theta calculation
        """
        term1 = -(
            spot_price * norm.pdf(d1) * volatility * math.exp(-dividend_yield * time_to_expiry) /
            (2 * math.sqrt(time_to_expiry))
        )

        if option_type.upper() in ['CE', 'CALL']:
            term2 = (
                self.risk_free_rate * strike_price *
                math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2)
            )
            term3 = (
                -dividend_yield * spot_price *
                math.exp(-dividend_yield * time_to_expiry) * norm.cdf(d1)
            )
            theta = (term1 - term2 + term3) / 365  # Per day
        else:  # PUT
            term2 = (
                -self.risk_free_rate * strike_price *
                math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2)
            )
            term3 = (
                dividend_yield * spot_price *
                math.exp(-dividend_yield * time_to_expiry) * norm.cdf(-d1)
            )
            theta = (term1 + term2 + term3) / 365  # Per day

        return theta

    def _calculate_vega(
        self,
        spot_price: float,
        d1: float,
        time_to_expiry: float,
        dividend_yield: float
    ) -> float:
        """
        Calculate Vega (volatility sensitivity)
        REQ-GREEK-004: Vega calculation
        """
        vega = (
            spot_price * math.exp(-dividend_yield * time_to_expiry) *
            norm.pdf(d1) * math.sqrt(time_to_expiry) / 100  # Per 1% change in IV
        )
        return vega

    def _calculate_rho(
        self,
        strike_price: float,
        d2: float,
        time_to_expiry: float,
        option_type: str
    ) -> float:
        """Calculate Rho (interest rate sensitivity)"""
        if option_type.upper() in ['CE', 'CALL']:
            rho = (
                strike_price * time_to_expiry *
                math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(d2) / 100
            )
        else:  # PUT
            rho = (
                -strike_price * time_to_expiry *
                math.exp(-self.risk_free_rate * time_to_expiry) * norm.cdf(-d2) / 100
            )
        return rho

    def _intrinsic_value(
        self,
        spot_price: float,
        strike_price: float,
        option_type: str
    ) -> float:
        """Calculate intrinsic value of option"""
        if option_type.upper() in ['CE', 'CALL']:
            return max(spot_price - strike_price, 0)
        else:  # PUT
            return max(strike_price - spot_price, 0)

    def _expired_greeks(
        self,
        spot_price: float,
        strike_price: float,
        option_type: str
    ) -> Dict[str, float]:
        """Handle Greeks for expired options (REQ-GREEK-007)"""
        itm = (
            (spot_price > strike_price and option_type.upper() in ['CE', 'CALL']) or
            (spot_price < strike_price and option_type.upper() in ['PE', 'PUT'])
        )

        return {
            'delta': 1.0 if itm else 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0
        }

    def _default_greeks(self) -> Dict[str, float]:
        """Return default Greeks on error"""
        return {
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0
        }

    def _validate_greek(
        self,
        value: float,
        greek_name: str,
        min_val: Optional[float],
        max_val: Optional[float]
    ) -> float:
        """
        Validate Greek values against reasonable ranges
        REQ-GREEK-013: Validate Greeks against reasonable ranges
        """
        if math.isnan(value) or math.isinf(value):
            self.logger.warning(f"Invalid {greek_name}: {value}, using 0")
            return 0.0

        if min_val is not None and value < min_val:
            self.logger.warning(
                f"{greek_name} {value:.4f} below min {min_val}, capping"
            )
            return min_val

        if max_val is not None and value > max_val:
            self.logger.warning(
                f"{greek_name} {value:.4f} above max {max_val}, capping"
            )
            return max_val

        return value

    def validate_model_price(
        self,
        model_price: float,
        market_price: float,
        threshold_pct: float = 15.0
    ) -> bool:
        """
        Validate model price against market price
        REQ-GREEK-014: Warn if model price diverges from market price

        Args:
            model_price: Theoretical price from Black-Scholes
            market_price: Actual market price
            threshold_pct: Maximum acceptable divergence percentage

        Returns:
            True if within threshold, False otherwise
        """
        if market_price == 0:
            return True  # Can't validate against zero price

        divergence_pct = abs((model_price - market_price) / market_price * 100)

        if divergence_pct > threshold_pct:
            self.logger.warning(
                f"⚠️  Model price divergence: {divergence_pct:.2f}% "
                f"(Model: ₹{model_price:.2f}, Market: ₹{market_price:.2f})"
            )
            return False

        return True

    def calculate_probability_itm(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> float:
        """
        Calculate probability of option expiring in-the-money

        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: 'CE' or 'PE'
            dividend_yield: Annual dividend yield

        Returns:
            Probability (0 to 1)
        """
        if time_to_expiry <= 0:
            return 1.0 if self._intrinsic_value(spot_price, strike_price, option_type) > 0 else 0.0

        try:
            d1, d2 = self._calculate_d1_d2(
                spot_price, strike_price, time_to_expiry, volatility, dividend_yield
            )

            if option_type.upper() in ['CE', 'CALL']:
                prob_itm = norm.cdf(d2)
            else:  # PUT
                prob_itm = norm.cdf(-d2)

            return prob_itm

        except Exception as e:
            self.logger.error(f"Error calculating probability ITM: {e}")
            return 0.5  # Default to 50% on error
