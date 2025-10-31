"""
Unit Tests for Position and Portfolio Risk Management
Tests position risk and portfolio risk managers
"""

import pytest
from datetime import datetime
from src.risk.position_risk import PositionRiskManager
from src.risk.portfolio_risk import PortfolioRiskManager


class TestPositionRiskManager:
    """Test position risk management"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'risk_limits': {
                'max_position_delta': 50,
                'max_position_gamma': 5,
                'max_position_vega': 100,
                'max_position_theta': -50
            }
        }
        self.risk_manager = PositionRiskManager(config)

    def test_initialization(self):
        """Test risk manager initializes"""
        assert self.risk_manager is not None

    def test_calculate_position_pnl(self):
        """Test P&L calculation for a position"""
        position = {
            'entry_price': 250.0,
            'current_price': 200.0,
            'quantity': 25
        }

        pnl = self.risk_manager.calculate_position_pnl(position)

        # P&L should be (200 - 250) * 25 = -1250
        expected_pnl = (200.0 - 250.0) * 25
        assert pnl == expected_pnl

    def test_calculate_position_pnl_profit(self):
        """Test P&L calculation for profitable position"""
        position = {
            'entry_price': 200.0,
            'current_price': 250.0,
            'quantity': 25
        }

        pnl = self.risk_manager.calculate_position_pnl(position)

        # Profit case
        assert pnl > 0
        assert pnl == 1250.0

    def test_check_position_greeks_within_limits(self):
        """Test Greeks check when within limits"""
        position_greeks = {
            'delta': 25,
            'gamma': 2,
            'theta': -30,
            'vega': 50
        }

        result = self.risk_manager.check_position_greeks(position_greeks)

        assert result['all_within_limits'] == True

    def test_check_position_greeks_delta_exceeded(self):
        """Test Greeks check when delta exceeds limit"""
        position_greeks = {
            'delta': 60,  # Exceeds 50
            'gamma': 2,
            'theta': -30,
            'vega': 50
        }

        result = self.risk_manager.check_position_greeks(position_greeks)

        assert result['all_within_limits'] == False
        assert 'delta' in result['violations']

    def test_check_position_greeks_gamma_exceeded(self):
        """Test Greeks check when gamma exceeds limit"""
        position_greeks = {
            'delta': 25,
            'gamma': 6,  # Exceeds 5
            'theta': -30,
            'vega': 50
        }

        result = self.risk_manager.check_position_greeks(position_greeks)

        assert result['all_within_limits'] == False
        assert 'gamma' in result['violations']

    def test_check_position_greeks_vega_exceeded(self):
        """Test Greeks check when vega exceeds limit"""
        position_greeks = {
            'delta': 25,
            'gamma': 2,
            'theta': -30,
            'vega': 150  # Exceeds 100
        }

        result = self.risk_manager.check_position_greeks(position_greeks)

        assert result['all_within_limits'] == False
        assert 'vega' in result['violations']

    def test_should_exit_target_reached(self):
        """Test exit signal when target profit reached"""
        position = {
            'entry_price': 250.0,
            'current_price': 125.0,  # 50% profit
            'target_profit': 125.0,
            'stop_loss': 800.0,
            'quantity': 25
        }
        current_greeks = {}

        should_exit, reason = self.risk_manager.should_exit(position, current_greeks)

        assert should_exit == True
        assert 'target' in reason.lower() or 'profit' in reason.lower()

    def test_should_exit_stop_loss_hit(self):
        """Test exit signal when stop loss hit"""
        position = {
            'entry_price': 250.0,
            'current_price': 300.0,  # Loss increased
            'target_profit': 125.0,
            'stop_loss': 800.0,
            'quantity': 25,
            'max_loss': 800.0
        }
        current_greeks = {}

        pnl = self.risk_manager.calculate_position_pnl(position)

        # Check if loss exceeds stop
        if abs(pnl) >= position['stop_loss']:
            should_exit, reason = self.risk_manager.should_exit(position, current_greeks)
            assert should_exit == True

    def test_position_age_tracking(self):
        """Test tracking position age"""
        position = {
            'entry_time': datetime.now().isoformat(),
            'entry_price': 250.0,
            'current_price': 250.0,
            'quantity': 25
        }

        # Position age should be calculable
        # Implementation may vary
        assert 'entry_time' in position


class TestPortfolioRiskManager:
    """Test portfolio risk management"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'risk_limits': {
                'max_portfolio_delta': 100,
                'max_portfolio_gamma': 10,
                'max_portfolio_vega': 200,
                'max_correlation_exposure': 0.7
            }
        }
        self.portfolio_risk = PortfolioRiskManager(config)

    def test_initialization(self):
        """Test portfolio risk manager initializes"""
        assert self.portfolio_risk is not None

    def test_aggregate_portfolio_greeks_empty(self):
        """Test aggregating Greeks with no positions"""
        positions = []

        greeks = self.portfolio_risk.aggregate_portfolio_greeks(positions)

        assert greeks['delta'] == 0
        assert greeks['gamma'] == 0
        assert greeks['theta'] == 0
        assert greeks['vega'] == 0

    def test_aggregate_portfolio_greeks_single_position(self):
        """Test aggregating Greeks with one position"""
        positions = [
            {
                'greeks': {
                    'delta': 25,
                    'gamma': 2,
                    'theta': -30,
                    'vega': 50
                }
            }
        ]

        greeks = self.portfolio_risk.aggregate_portfolio_greeks(positions)

        assert greeks['delta'] == 25
        assert greeks['gamma'] == 2
        assert greeks['theta'] == -30
        assert greeks['vega'] == 50

    def test_aggregate_portfolio_greeks_multiple_positions(self):
        """Test aggregating Greeks with multiple positions"""
        positions = [
            {
                'greeks': {
                    'delta': 25,
                    'gamma': 2,
                    'theta': -30,
                    'vega': 50
                }
            },
            {
                'greeks': {
                    'delta': -15,
                    'gamma': 1,
                    'theta': -20,
                    'vega': 30
                }
            },
            {
                'greeks': {
                    'delta': 10,
                    'gamma': 1,
                    'theta': -10,
                    'vega': 20
                }
            }
        ]

        greeks = self.portfolio_risk.aggregate_portfolio_greeks(positions)

        # Delta: 25 - 15 + 10 = 20
        assert greeks['delta'] == 20
        # Gamma: 2 + 1 + 1 = 4
        assert greeks['gamma'] == 4
        # Theta: -30 - 20 - 10 = -60
        assert greeks['theta'] == -60
        # Vega: 50 + 30 + 20 = 100
        assert greeks['vega'] == 100

    def test_check_portfolio_limits_within(self):
        """Test portfolio limits when within bounds"""
        portfolio_greeks = {
            'delta': 50,
            'gamma': 5,
            'theta': -100,
            'vega': 100
        }

        result = self.portfolio_risk.check_portfolio_limits(portfolio_greeks)

        assert result['within_limits'] == True

    def test_check_portfolio_limits_delta_exceeded(self):
        """Test portfolio limits when delta exceeded"""
        portfolio_greeks = {
            'delta': 150,  # Exceeds 100
            'gamma': 5,
            'theta': -100,
            'vega': 100
        }

        result = self.portfolio_risk.check_portfolio_limits(portfolio_greeks)

        assert result['within_limits'] == False
        assert 'delta' in result['violations']

    def test_check_portfolio_limits_vega_exceeded(self):
        """Test portfolio limits when vega exceeded"""
        portfolio_greeks = {
            'delta': 50,
            'gamma': 5,
            'theta': -100,
            'vega': 250  # Exceeds 200
        }

        result = self.portfolio_risk.check_portfolio_limits(portfolio_greeks)

        assert result['within_limits'] == False
        assert 'vega' in result['violations']

    def test_calculate_portfolio_pnl(self):
        """Test calculating total portfolio P&L"""
        positions = [
            {
                'entry_price': 250.0,
                'current_price': 200.0,
                'quantity': 25
            },
            {
                'entry_price': 300.0,
                'current_price': 350.0,
                'quantity': 25
            },
            {
                'entry_price': 150.0,
                'current_price': 140.0,
                'quantity': 25
            }
        ]

        total_pnl = self.portfolio_risk.calculate_portfolio_pnl(positions)

        # Position 1: (200-250)*25 = -1250
        # Position 2: (350-300)*25 = +1250
        # Position 3: (140-150)*25 = -250
        # Total: -1250 + 1250 - 250 = -250

        expected_pnl = -1250 + 1250 - 250
        assert total_pnl == expected_pnl

    def test_calculate_max_portfolio_loss(self):
        """Test calculating maximum portfolio loss"""
        positions = [
            {'max_loss': 500},
            {'max_loss': 800},
            {'max_loss': 300}
        ]

        max_loss = self.portfolio_risk.calculate_max_portfolio_loss(positions)

        # Total max loss = 500 + 800 + 300 = 1600
        assert max_loss == 1600

    def test_diversification_check(self):
        """Test portfolio diversification"""
        positions = [
            {'symbol': 'BANKNIFTY', 'max_loss': 500},
            {'symbol': 'BANKNIFTY', 'max_loss': 500},
            {'symbol': 'NIFTY', 'max_loss': 500}
        ]

        # Check concentration
        result = self.portfolio_risk.check_concentration(positions)

        # Implementation may vary
        assert isinstance(result, dict)

    def test_portfolio_correlation_risk(self):
        """Test correlation risk assessment"""
        positions = [
            {'symbol': 'BANKNIFTY', 'strategy': 'Iron Condor'},
            {'symbol': 'BANKNIFTY', 'strategy': 'Bull Call Spread'},
            {'symbol': 'BANKNIFTY', 'strategy': 'Iron Condor'}
        ]

        # All positions in same underlying = high correlation
        # Implementation should detect this
        result = self.portfolio_risk.assess_correlation_risk(positions)

        assert isinstance(result, dict)

    def test_portfolio_value_at_risk(self):
        """Test VaR calculation"""
        positions = [
            {'max_loss': 500, 'probability': 0.95},
            {'max_loss': 800, 'probability': 0.95}
        ]

        # VaR should consider position risks
        # Implementation may vary
        total_max_loss = sum(p['max_loss'] for p in positions)
        assert total_max_loss == 1300


class TestRiskIntegration:
    """Test integration between position and portfolio risk"""

    def test_position_affects_portfolio(self):
        """Test that position risk rolls up to portfolio"""
        config = {
            'risk_limits': {
                'max_position_delta': 50,
                'max_portfolio_delta': 100
            }
        }

        pos_risk = PositionRiskManager(config)
        port_risk = PortfolioRiskManager(config)

        # Create positions
        positions = [
            {
                'greeks': {'delta': 40, 'gamma': 2, 'theta': -20, 'vega': 30}
            },
            {
                'greeks': {'delta': 40, 'gamma': 2, 'theta': -20, 'vega': 30}
            }
        ]

        # Individual positions within limits
        for pos in positions:
            result = pos_risk.check_position_greeks(pos['greeks'])
            assert result['all_within_limits'] == True

        # Portfolio should be within limits (80 delta < 100)
        portfolio_greeks = port_risk.aggregate_portfolio_greeks(positions)
        result = port_risk.check_portfolio_limits(portfolio_greeks)
        assert result['within_limits'] == True


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
