"""
Unit Tests for Greeks Calculation
Tests Black-Scholes pricing and IV calculation
"""

import pytest
import math
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator


class TestBlackScholesCalculator:
    """Test Black-Scholes calculations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.bs_calc = BlackScholesCalculator()

    def test_call_option_price(self):
        """Test call option pricing"""
        # Example: ATM call option
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365  # 7 days
        volatility = 0.20  # 20% IV
        option_type = 'CE'

        price = self.bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, volatility, option_type
        )

        # Price should be positive
        assert price > 0
        # ATM call should be worth roughly spot * volatility * sqrt(time)
        expected_approx = spot_price * volatility * math.sqrt(time_to_expiry)
        assert abs(price - expected_approx) / expected_approx < 1.0  # Within 100%

    def test_put_option_price(self):
        """Test put option pricing"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365
        volatility = 0.20
        option_type = 'PE'

        price = self.bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, volatility, option_type
        )

        assert price > 0

    def test_put_call_parity(self):
        """Test put-call parity: C - P = S - K*e^(-r*T)"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 30 / 365
        volatility = 0.25

        call_price = self.bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, volatility, 'CE'
        )
        put_price = self.bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, volatility, 'PE'
        )

        # For ATM options with r=0, C - P should be approximately 0
        difference = abs(call_price - put_price)
        assert difference < spot_price * 0.01  # Within 1% of spot

    def test_greeks_call_option(self):
        """Test Greeks calculation for call option"""
        spot_price = 45000
        strike_price = 44000  # ITM call
        time_to_expiry = 7 / 365
        volatility = 0.20
        option_type = 'CE'

        greeks = self.bs_calc.calculate_greeks(
            spot_price, strike_price, time_to_expiry, volatility, option_type
        )

        # Check all Greeks are present
        assert 'delta' in greeks
        assert 'gamma' in greeks
        assert 'theta' in greeks
        assert 'vega' in greeks
        assert 'rho' in greeks

        # ITM call should have delta between 0.5 and 1.0
        assert 0.5 < greeks['delta'] < 1.0

        # Gamma should be positive
        assert greeks['gamma'] > 0

        # Theta should be negative (time decay)
        assert greeks['theta'] < 0

        # Vega should be positive
        assert greeks['vega'] > 0

    def test_greeks_put_option(self):
        """Test Greeks calculation for put option"""
        spot_price = 45000
        strike_price = 46000  # ITM put
        time_to_expiry = 7 / 365
        volatility = 0.20
        option_type = 'PE'

        greeks = self.bs_calc.calculate_greeks(
            spot_price, strike_price, time_to_expiry, volatility, option_type
        )

        # ITM put should have delta between -1.0 and -0.5
        assert -1.0 < greeks['delta'] < -0.5

        # Gamma should be positive
        assert greeks['gamma'] > 0

        # Theta should be negative
        assert greeks['theta'] < 0

        # Vega should be positive
        assert greeks['vega'] > 0

    def test_delta_bounds(self):
        """Test that delta stays within bounds"""
        spot_price = 45000
        time_to_expiry = 7 / 365
        volatility = 0.20

        # Deep ITM call - delta should approach 1.0
        greeks_itm = self.bs_calc.calculate_greeks(
            spot_price, 40000, time_to_expiry, volatility, 'CE'
        )
        assert 0.8 < greeks_itm['delta'] < 1.0

        # Deep OTM call - delta should approach 0
        greeks_otm = self.bs_calc.calculate_greeks(
            spot_price, 50000, time_to_expiry, volatility, 'CE'
        )
        assert 0.0 < greeks_otm['delta'] < 0.2

    def test_time_decay_effect(self):
        """Test that theta increases as expiry approaches"""
        spot_price = 45000
        strike_price = 45000
        volatility = 0.20

        # 30 days to expiry
        greeks_30d = self.bs_calc.calculate_greeks(
            spot_price, strike_price, 30/365, volatility, 'CE'
        )

        # 7 days to expiry
        greeks_7d = self.bs_calc.calculate_greeks(
            spot_price, strike_price, 7/365, volatility, 'CE'
        )

        # Theta should be more negative (faster decay) closer to expiry
        assert greeks_7d['theta'] < greeks_30d['theta']

    def test_volatility_effect_on_vega(self):
        """Test that vega changes with volatility"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365

        greeks_low_vol = self.bs_calc.calculate_greeks(
            spot_price, strike_price, time_to_expiry, 0.15, 'CE'
        )

        greeks_high_vol = self.bs_calc.calculate_greeks(
            spot_price, strike_price, time_to_expiry, 0.30, 'CE'
        )

        # Both should have positive vega
        assert greeks_low_vol['vega'] > 0
        assert greeks_high_vol['vega'] > 0

    def test_zero_time_to_expiry(self):
        """Test behavior at expiry"""
        spot_price = 45000
        strike_price = 44000
        time_to_expiry = 0.001 / 365  # Very close to expiry
        volatility = 0.20

        price = self.bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, volatility, 'CE'
        )

        # ITM call at expiry should be approximately intrinsic value
        intrinsic_value = max(0, spot_price - strike_price)
        assert abs(price - intrinsic_value) < intrinsic_value * 0.1  # Within 10%


class TestImpliedVolatilityCalculator:
    """Test IV calculation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.iv_calc = ImpliedVolatilityCalculator()

    def test_calculate_iv_call_option(self):
        """Test IV calculation for call option"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365
        option_type = 'CE'

        # Calculate theoretical price with known volatility
        known_volatility = 0.25
        bs_calc = BlackScholesCalculator()
        market_price = bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, known_volatility, option_type
        )

        # Now calculate IV from that price
        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, option_type
        )

        # Should recover the original volatility
        assert calculated_iv is not None
        assert abs(calculated_iv - known_volatility) < 0.01  # Within 1%

    def test_calculate_iv_put_option(self):
        """Test IV calculation for put option"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365
        option_type = 'PE'

        known_volatility = 0.30
        bs_calc = BlackScholesCalculator()
        market_price = bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, known_volatility, option_type
        )

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, option_type
        )

        assert calculated_iv is not None
        assert abs(calculated_iv - known_volatility) < 0.01

    def test_iv_bounds(self):
        """Test that calculated IV stays within reasonable bounds"""
        spot_price = 45000
        strike_price = 45000
        time_to_expiry = 7 / 365
        market_price = 500  # ₹500 premium

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, 'CE'
        )

        if calculated_iv is not None:
            # IV should be between 5% and 100%
            assert 0.05 < calculated_iv < 1.0

    def test_iv_for_itm_option(self):
        """Test IV calculation for ITM option"""
        spot_price = 45000
        strike_price = 44000  # ITM call
        time_to_expiry = 7 / 365

        known_volatility = 0.22
        bs_calc = BlackScholesCalculator()
        market_price = bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, known_volatility, 'CE'
        )

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, 'CE'
        )

        assert calculated_iv is not None
        assert abs(calculated_iv - known_volatility) < 0.01

    def test_iv_for_otm_option(self):
        """Test IV calculation for OTM option"""
        spot_price = 45000
        strike_price = 46000  # OTM call
        time_to_expiry = 7 / 365

        known_volatility = 0.28
        bs_calc = BlackScholesCalculator()
        market_price = bs_calc.calculate_price(
            spot_price, strike_price, time_to_expiry, known_volatility, 'CE'
        )

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, 'CE'
        )

        assert calculated_iv is not None
        assert abs(calculated_iv - known_volatility) < 0.01

    def test_iv_very_low_premium(self):
        """Test IV calculation with very low premium"""
        spot_price = 45000
        strike_price = 50000  # Deep OTM
        time_to_expiry = 1 / 365  # 1 day
        market_price = 5  # Very low premium

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, 'CE'
        )

        # May return None or a very high IV for deep OTM
        if calculated_iv is not None:
            assert calculated_iv > 0

    def test_iv_intrinsic_value(self):
        """Test IV when price equals intrinsic value"""
        spot_price = 45000
        strike_price = 44000
        time_to_expiry = 7 / 365
        intrinsic_value = spot_price - strike_price  # 1000

        # Price slightly above intrinsic
        market_price = intrinsic_value + 50

        calculated_iv = self.iv_calc.calculate_iv(
            market_price, spot_price, strike_price, time_to_expiry, 'CE'
        )

        # Should be able to calculate IV
        assert calculated_iv is not None
        assert calculated_iv > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
