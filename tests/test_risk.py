"""
Unit Tests for Risk Management
"""

import pytest
from datetime import datetime
from src.risk.pre_trade_validator import PreTradeValidator, TradeSignal


def test_defined_risk_check():
    """Test defined risk validation"""
    config = {
        'risk_limits': {
            'max_loss_per_trade': 1000,
            'total_capital': 50000,
            'max_positions': 5
        }
    }

    validator = PreTradeValidator(config)

    # Test with defined risk
    signal = TradeSignal(
        strategy_name="Iron Condor",
        symbol="BANKNIFTY",
        expiry_date="2025-11-06",
        legs=[
            {'action': 'BUY', 'option_type': 'PE', 'strike': 44000},
            {'action': 'SELL', 'option_type': 'PE', 'strike': 44200},
            {'action': 'SELL', 'option_type': 'CE', 'strike': 45800},
            {'action': 'BUY', 'option_type': 'CE', 'strike': 46000}
        ],
        max_loss=800,
        max_profit=400,
        margin_required=1000,
        position_greeks={'delta': 0, 'gamma': 0, 'theta': 10, 'vega': -50},
        timestamp=datetime.now().isoformat()
    )

    result = validator.validate_trade(signal, [], {'daily_pnl': 0})

    assert result.approved == True
    assert result.checks_passed['defined_risk'] == True


def test_max_loss_exceeds_limit():
    """Test rejection when max loss exceeds limit"""
    config = {
        'risk_limits': {
            'max_loss_per_trade': 500,  # Lower limit
            'total_capital': 50000,
            'max_positions': 5
        }
    }

    validator = PreTradeValidator(config)

    signal = TradeSignal(
        strategy_name="Iron Condor",
        symbol="BANKNIFTY",
        expiry_date="2025-11-06",
        legs=[],
        max_loss=1000,  # Exceeds limit
        max_profit=400,
        margin_required=1200,
        position_greeks={},
        timestamp=datetime.now().isoformat()
    )

    result = validator.validate_trade(signal, [], {'daily_pnl': 0})

    assert result.approved == False
    assert result.checks_passed['max_loss_acceptable'] == False


def test_prohibited_strategy():
    """Test rejection of naked options"""
    config = {
        'risk_limits': {
            'max_loss_per_trade': 1000,
            'total_capital': 50000,
            'prohibited_strategies': ['naked_call', 'naked_put']
        }
    }

    validator = PreTradeValidator(config)

    # Test naked call (prohibited)
    signal = TradeSignal(
        strategy_name="naked_call",
        symbol="BANKNIFTY",
        expiry_date="2025-11-06",
        legs=[{'action': 'SELL', 'option_type': 'CE'}],  # No protection
        max_loss=float('inf'),  # Infinite risk
        max_profit=100,
        margin_required=5000,
        position_greeks={},
        timestamp=datetime.now().isoformat()
    )

    result = validator.validate_trade(signal, [], {'daily_pnl': 0})

    assert result.approved == False


def test_position_limits():
    """Test position limit enforcement"""
    config = {
        'risk_limits': {
            'max_loss_per_trade': 1000,
            'total_capital': 50000,
            'max_positions': 2  # Only 2 positions allowed
        }
    }

    validator = PreTradeValidator(config)

    # Create signal
    signal = TradeSignal(
        strategy_name="Iron Condor",
        symbol="BANKNIFTY",
        expiry_date="2025-11-06",
        legs=[],
        max_loss=800,
        max_profit=400,
        margin_required=1000,
        position_greeks={},
        timestamp=datetime.now().isoformat()
    )

    # Test with 2 existing positions (at limit)
    current_positions = [
        {'id': 1, 'strategy': 'IC1'},
        {'id': 2, 'strategy': 'IC2'}
    ]

    result = validator.validate_trade(signal, current_positions, {'daily_pnl': 0})

    assert result.approved == False
    assert result.checks_passed['position_limits'] == False


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
