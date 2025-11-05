"""
Integration Tests
Tests complete workflows and component integration
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta, date
from src.broker.paper_trading import PaperTradingBroker
from src.database.database_manager import DatabaseManager
from src.risk.pre_trade_validator import PreTradeValidator, TradeSignal
from src.risk.circuit_breakers import CircuitBreakers
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator
from src.strategy.iron_condor import IronCondorStrategy
from src.data.market_data_feed import MarketDataFeed
from src.utils.nse_calendar import NSECalendar
from src.execution.order_manager import OrderManager


class TestPaperTradingIntegration:
    """Test paper trading workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create temp database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize components
        config = {
            'database': {
                'type': 'sqlite',
                'path': self.temp_db_path
            },
            'risk_limits': {
                'max_loss_per_trade': 1000,
                'total_capital': 50000,
                'max_positions': 5,
                'max_daily_loss': 5000
            },
            'api_credentials': {
                'mode': 'paper'
            },
            'paper_trading': {
                'initial_capital': 50000,
                'slippage': 0.001
            }
        }

        self.broker = PaperTradingBroker(config)
        self.db = DatabaseManager(config)
        self.validator = PreTradeValidator(config)

    def teardown_method(self):
        """Clean up after tests"""
        self.db.close()
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_complete_trade_lifecycle(self):
        """Test complete trade from entry to exit"""
        # 1. Connect broker
        assert self.broker.connect() == True

        # 2. Create trade signal
        signal = TradeSignal(
            strategy_name="Iron Condor",
            symbol="BANKNIFTY",
            expiry_date="2025-11-06",
            legs=[
                {'action': 'BUY', 'option_type': 'PE', 'strike': 44000, 'symbol': 'BANKNIFTY26DEC2444000PE', 'quantity': 25, 'price': 50},
                {'action': 'SELL', 'option_type': 'PE', 'strike': 44200, 'symbol': 'BANKNIFTY26DEC2444200PE', 'quantity': 25, 'price': 100},
                {'action': 'SELL', 'option_type': 'CE', 'strike': 45800, 'symbol': 'BANKNIFTY26DEC2445800CE', 'quantity': 25, 'price': 100},
                {'action': 'BUY', 'option_type': 'CE', 'strike': 46000, 'symbol': 'BANKNIFTY26DEC2446000CE', 'quantity': 25, 'price': 50}
            ],
            max_loss=800,
            max_profit=400,
            margin_required=1000,
            position_greeks={'delta': 0, 'gamma': 0, 'theta': 10, 'vega': -50},
            timestamp=datetime.now().isoformat()
        )

        # 3. Validate trade
        validation = self.validator.validate_trade(signal, [], {'daily_pnl': 0})
        assert validation.approved == True

        # 4. Place orders
        for leg in signal.legs:
            order = {
                'symbol': leg['symbol'],
                'transaction_type': 'BUY' if leg['action'] == 'BUY' else 'SELL',
                'quantity': leg['quantity'],
                'order_type': 'MARKET',
                'product_type': 'INTRADAY'
            }

            order_id = self.broker.place_order(order)
            assert order_id is not None

        # 5. Store position in database
        position = {
            'strategy_name': signal.strategy_name,
            'symbol': signal.symbol,
            'expiry_date': signal.expiry_date,
            'entry_time': datetime.now().isoformat(),
            'legs': str(signal.legs),
            'entry_price': 250.0,
            'quantity': 25,
            'max_loss': signal.max_loss,
            'max_profit': signal.max_profit,
            'target_profit': 200,
            'stop_loss': 800,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)
        assert position_id > 0

        # 6. Retrieve position
        retrieved = self.db.get_position(position_id)
        assert retrieved['strategy_name'] == 'Iron Condor'

        # 7. Close position
        exit_data = {
            'exit_time': datetime.now().isoformat(),
            'exit_price': 200.0,
            'realized_pnl': 50.0,
            'exit_reason': 'Target reached'
        }

        self.db.close_position(position_id, exit_data)

        # 8. Verify trade history
        trades = self.db.get_trades_history(limit=1)
        assert len(trades) > 0
        assert trades[0]['realized_pnl'] == 50.0


class TestMarketDataIntegration:
    """Test market data feed integration"""

    def test_market_data_caching(self):
        """Test market data feed with caching"""
        config = {
            'api_credentials': {'mode': 'paper'},
            'data': {
                'enable_cache': True,
                'cache_ttl_seconds': 5
            }
        }

        broker = PaperTradingBroker(config)
        feed = MarketDataFeed(broker, config)

        # Fetch spot price (should cache)
        price1 = feed.get_spot_price('BANKNIFTY')
        assert price1 > 0

        # Fetch again (should use cache)
        price2 = feed.get_spot_price('BANKNIFTY')
        assert price1 == price2

        # Invalidate cache
        feed.invalidate_cache('spot')

        # Fetch again (should fetch fresh)
        price3 = feed.get_spot_price('BANKNIFTY')
        assert price3 is not None


class TestNSECalendarIntegration:
    """Test NSE calendar integration"""

    def test_expiry_calculations(self):
        """Test expiry date calculations"""
        calendar = NSECalendar()

        # Test weekly expiry
        banknifty_expiry = calendar.get_weekly_expiry('BANKNIFTY')
        assert banknifty_expiry.weekday() == 2  # Wednesday

        nifty_expiry = calendar.get_weekly_expiry('NIFTY')
        assert nifty_expiry.weekday() == 3  # Thursday

        # Test expiry formatting
        formatted = calendar.format_expiry_for_symbol(banknifty_expiry)
        assert len(formatted) == 7  # DDMMMYY format

        # Test trading day validation
        assert isinstance(calendar.is_trading_day(date.today()), bool)

    def test_holiday_handling(self):
        """Test holiday handling"""
        calendar = NSECalendar()

        # Republic Day 2024
        republic_day = date(2024, 1, 26)
        assert calendar.is_trading_day(republic_day) == False

        # Get next trading day after holiday
        next_day = calendar.get_next_trading_day(republic_day)
        assert calendar.is_trading_day(next_day) == True


class TestOrderExecutionIntegration:
    """Test order execution manager"""

    def test_order_retry_logic(self):
        """Test order retry with price improvement"""
        config = {
            'api_credentials': {'mode': 'paper'},
            'paper_trading': {'initial_capital': 50000},
            'execution': {
                'max_retry': 3,
                'timeout_seconds': 60,
                'price_improvement_ticks': 1,
                'tick_size': 0.05
            }
        }

        broker = PaperTradingBroker(config)
        broker.connect()

        order_manager = OrderManager(broker, config)

        # Place order with retry
        order = {
            'symbol': 'BANKNIFTY26DEC2445000CE',
            'transaction_type': 'BUY',
            'quantity': 25,
            'price': 250.0,
            'order_type': 'LIMIT',
            'product_type': 'INTRADAY'
        }

        order_id = order_manager.place_order_with_retry(order)

        # Should eventually succeed (paper trading always fills)
        assert order_id is not None

    def test_multi_leg_execution(self):
        """Test multi-leg order execution"""
        config = {
            'api_credentials': {'mode': 'paper'},
            'paper_trading': {'initial_capital': 50000},
            'execution': {
                'max_retry': 3,
                'timeout_seconds': 60
            }
        }

        broker = PaperTradingBroker(config)
        broker.connect()

        order_manager = OrderManager(broker, config)

        # Multi-leg Iron Condor
        legs = [
            {'symbol': 'BANKNIFTY26DEC2444000PE', 'transaction_type': 'BUY', 'quantity': 25, 'price': 50, 'order_type': 'MARKET'},
            {'symbol': 'BANKNIFTY26DEC2444200PE', 'transaction_type': 'SELL', 'quantity': 25, 'price': 100, 'order_type': 'MARKET'},
            {'symbol': 'BANKNIFTY26DEC2445800CE', 'transaction_type': 'SELL', 'quantity': 25, 'price': 100, 'order_type': 'MARKET'},
            {'symbol': 'BANKNIFTY26DEC2446000CE', 'transaction_type': 'BUY', 'quantity': 25, 'price': 50, 'order_type': 'MARKET'}
        ]

        results = order_manager.place_multi_leg_order(legs, atomic=False)

        # All legs should be placed
        assert len(results) == 4
        filled_count = sum(1 for v in results.values() if v is not None)
        assert filled_count >= 3  # At least 3 legs filled


class TestStrategyIntegration:
    """Test strategy integration"""

    def test_iron_condor_signal_generation(self):
        """Test Iron Condor strategy signal generation"""
        config = {
            'enabled': True,
            'min_dte': 5,
            'max_dte': 15,
            'max_vix': 35,
            'target_profit': 0.50,
            'stop_loss': 1.00
        }

        strategy = IronCondorStrategy(config)

        # Market data
        market_data = {
            'spot_price': 45000,
            'vix': 25,
            'days_to_expiry': 7
        }

        # Option chain (simplified)
        option_chain = [
            {'strike': 44000, 'option_type': 'PE', 'ltp': 50},
            {'strike': 44200, 'option_type': 'PE', 'ltp': 100},
            {'strike': 45800, 'option_type': 'CE', 'ltp': 100},
            {'strike': 46000, 'option_type': 'CE', 'ltp': 50},
        ]

        current_positions = []

        # Signal may or may not be generated based on conditions
        # Just verify it doesn't crash
        signal = strategy.generate_entry_signal(market_data, option_chain, current_positions)

        # If signal generated, verify it has defined risk
        if signal:
            assert signal.max_loss != float('inf')
            assert signal.max_loss > 0


class TestFullSystemIntegration:
    """Test full system integration"""

    def test_end_to_end_workflow(self):
        """Test complete end-to-end trading workflow"""
        # Setup
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_path = temp_db.name
        temp_db.close()

        try:
            config = {
                'database': {'type': 'sqlite', 'path': temp_db_path},
                'risk_limits': {
                    'max_loss_per_trade': 1000,
                    'total_capital': 50000,
                    'max_positions': 5
                },
                'circuit_breakers': {
                    'daily_loss_limit': 5000,
                    'consecutive_loss_limit': 5
                },
                'api_credentials': {'mode': 'paper'},
                'paper_trading': {'initial_capital': 50000}
            }

            # Initialize all components
            broker = PaperTradingBroker(config)
            db = DatabaseManager(config)
            validator = PreTradeValidator(config)
            breakers = CircuitBreakers(config)
            calendar = NSECalendar()
            bs_calc = BlackScholesCalculator()

            # 1. Check if trading day
            assert isinstance(calendar.is_trading_day(date.today()), bool)

            # 2. Connect broker
            assert broker.connect() == True

            # 3. Check circuit breakers
            status = breakers.check_all_breakers({}, {}, {}, datetime.now())
            assert status is not None

            # 4. Calculate Greeks
            greeks = bs_calc.calculate_greeks(45000, 45000, 7/365, 0.25, 'CE')
            assert 'delta' in greeks
            assert 'gamma' in greeks

            # 5. Create and validate signal
            signal = TradeSignal(
                strategy_name="Test Strategy",
                symbol="BANKNIFTY",
                expiry_date="2025-11-06",
                legs=[{'action': 'BUY', 'strike': 45000}],
                max_loss=500,
                max_profit=500,
                margin_required=600,
                position_greeks=greeks,
                timestamp=datetime.now().isoformat()
            )

            validation = validator.validate_trade(signal, [], {'daily_pnl': 0})
            assert validation is not None

            # System integration successful
            assert True

        finally:
            # Cleanup
            db.close()
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
