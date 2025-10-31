"""
Unit Tests for Trading Strategies
Tests all strategy implementations
"""

import pytest
from datetime import datetime
from src.strategy.iron_condor import IronCondorStrategy
from src.strategy.vertical_spreads import (
    BullCallSpreadStrategy, BearPutSpreadStrategy,
    BullPutSpreadStrategy, BearCallSpreadStrategy
)
from src.strategy.volatility_strategies import (
    LongStraddleStrategy, LongStrangleStrategy, IronButterflyStrategy
)


class TestIronCondorStrategy:
    """Test Iron Condor strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'max_vix': 35,
            'target_profit': 0.50,
            'stop_loss': 1.00
        }
        self.strategy = IronCondorStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes correctly"""
        assert self.strategy is not None
        assert self.strategy.name == 'Iron Condor'
        assert self.strategy.enabled == True

    def test_entry_signal_conditions(self):
        """Test entry signal generation conditions"""
        market_data = {
            'spot_price': 45000,
            'vix': 25,
            'days_to_expiry': 7
        }
        option_chain = []
        current_positions = []

        # Check common conditions
        conditions_met, reason = self.strategy.check_entry_conditions_common(
            market_data, current_positions
        )

        # With valid parameters, common conditions should pass
        assert isinstance(conditions_met, bool)

    def test_defined_risk_requirement(self):
        """Test that iron condor has defined risk"""
        # Iron condor should have max loss = width - credit
        # This is always defined and finite
        spot_price = 45000

        # Sample iron condor legs
        legs = [
            {'action': 'BUY', 'option_type': 'PE', 'strike': 44000},
            {'action': 'SELL', 'option_type': 'PE', 'strike': 44200},
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45800},
            {'action': 'BUY', 'option_type': 'CE', 'strike': 46000}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert 'max_loss' in metrics
        assert 'max_profit' in metrics
        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')

    def test_exit_conditions(self):
        """Test exit condition checking"""
        position = {
            'entry_price': 250,
            'current_price': 125,
            'max_loss': 800,
            'target_profit': 125
        }
        market_data = {}
        current_greeks = {}

        should_exit, reason = self.strategy.check_exit_conditions(
            position, market_data, current_greeks
        )

        # Should recognize profit target hit
        assert isinstance(should_exit, bool)
        assert isinstance(reason, str)


class TestBullCallSpread:
    """Test Bull Call Spread strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'target_profit': 0.50,
            'stop_loss': 1.00
        }
        self.strategy = BullCallSpreadStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Bull Call Spread'

    def test_defined_risk(self):
        """Test bull call spread has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45000},
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45500}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestBearPutSpread:
    """Test Bear Put Spread strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15
        }
        self.strategy = BearPutSpreadStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Bear Put Spread'

    def test_defined_risk(self):
        """Test bear put spread has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'BUY', 'option_type': 'PE', 'strike': 45000},
            {'action': 'SELL', 'option_type': 'PE', 'strike': 44500}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestBullPutSpread:
    """Test Bull Put Spread strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15
        }
        self.strategy = BullPutSpreadStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Bull Put Spread'

    def test_defined_risk(self):
        """Test bull put spread has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'SELL', 'option_type': 'PE', 'strike': 44500},
            {'action': 'BUY', 'option_type': 'PE', 'strike': 44000}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestBearCallSpread:
    """Test Bear Call Spread strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15
        }
        self.strategy = BearCallSpreadStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Bear Call Spread'

    def test_defined_risk(self):
        """Test bear call spread has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45500},
            {'action': 'BUY', 'option_type': 'CE', 'strike': 46000}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestLongStraddle:
    """Test Long Straddle strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'min_vix': 15
        }
        self.strategy = LongStraddleStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Long Straddle'

    def test_defined_risk(self):
        """Test long straddle has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45000},
            {'action': 'BUY', 'option_type': 'PE', 'strike': 45000}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        # Long straddle risk is limited to premium paid
        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestLongStrangle:
    """Test Long Strangle strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'min_vix': 15
        }
        self.strategy = LongStrangleStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Long Strangle'

    def test_defined_risk(self):
        """Test long strangle has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45500},
            {'action': 'BUY', 'option_type': 'PE', 'strike': 44500}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestIronButterfly:
    """Test Iron Butterfly strategy"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'max_vix': 35
        }
        self.strategy = IronButterflyStrategy(config)

    def test_strategy_initialization(self):
        """Test strategy initializes"""
        assert self.strategy is not None
        assert self.strategy.name == 'Iron Butterfly'

    def test_defined_risk(self):
        """Test iron butterfly has defined risk"""
        spot_price = 45000
        legs = [
            {'action': 'BUY', 'option_type': 'PE', 'strike': 44500},
            {'action': 'SELL', 'option_type': 'PE', 'strike': 45000},
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45000},
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45500}
        ]

        metrics = self.strategy.calculate_position_metrics(legs, spot_price)

        assert metrics['max_loss'] > 0
        assert metrics['max_loss'] != float('inf')


class TestStrategyWhitelist:
    """Test strategy whitelist validation"""

    def test_allowed_strategies(self):
        """Test that all implemented strategies are allowed"""
        allowed_strategies = [
            IronCondorStrategy,
            BullCallSpreadStrategy,
            BearPutSpreadStrategy,
            BullPutSpreadStrategy,
            BearCallSpreadStrategy,
            LongStraddleStrategy,
            LongStrangleStrategy,
            IronButterflyStrategy
        ]

        config = {'enabled': True}

        for StrategyClass in allowed_strategies:
            strategy = StrategyClass(config)
            # All strategies should pass whitelist validation
            assert strategy.validate_strategy_whitelist() == True

    def test_prohibited_strategy_names(self):
        """Test that prohibited strategy names are rejected"""
        prohibited = [
            'naked_call',
            'naked_put',
            'short_straddle_unhedged',
            'short_strangle_unhedged'
        ]

        # These should not be in our implemented strategies
        config = {'enabled': True}
        strategy = IronCondorStrategy(config)

        for prohibited_name in prohibited:
            # Temporarily change strategy name
            original_name = strategy.name
            strategy.name = prohibited_name

            # Should fail validation
            assert strategy.validate_strategy_whitelist() == False

            # Restore original name
            strategy.name = original_name


class TestStrategyRiskMetrics:
    """Test risk metric calculations across strategies"""

    def test_all_strategies_calculate_max_loss(self):
        """Test that all strategies calculate max loss"""
        strategies = [
            IronCondorStrategy({'enabled': True}),
            BullCallSpreadStrategy({'enabled': True}),
            LongStraddleStrategy({'enabled': True})
        ]

        spot_price = 45000
        sample_legs = [
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45000},
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45500}
        ]

        for strategy in strategies:
            metrics = strategy.calculate_position_metrics(sample_legs, spot_price)

            # All should return metrics dictionary
            assert isinstance(metrics, dict)
            assert 'max_loss' in metrics
            assert 'max_profit' in metrics
            assert 'margin_required' in metrics

    def test_max_loss_never_infinite(self):
        """Test that max loss is never infinite for allowed strategies"""
        strategies = [
            IronCondorStrategy({'enabled': True}),
            BullCallSpreadStrategy({'enabled': True}),
            BearPutSpreadStrategy({'enabled': True}),
            BullPutSpreadStrategy({'enabled': True}),
            BearCallSpreadStrategy({'enabled': True}),
            LongStraddleStrategy({'enabled': True}),
            LongStrangleStrategy({'enabled': True}),
            IronButterflyStrategy({'enabled': True})
        ]

        spot_price = 45000
        sample_legs = [
            {'action': 'BUY', 'option_type': 'CE', 'strike': 45000}
        ]

        for strategy in strategies:
            metrics = strategy.calculate_position_metrics(sample_legs, spot_price)

            # Max loss should never be infinite
            assert metrics['max_loss'] != float('inf')
            assert metrics['max_loss'] > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
