"""
Main Trading Engine
Orchestrates all system components
"""

import sys
import argparse
import logging
from datetime import datetime, time
import time as time_module
from typing import Dict, List

# Import all components
from utils.config_loader import ConfigLoader
from utils.logger_setup import setup_logger
from broker.angel_one import AngelOneBroker
from broker.paper_trading import PaperTradingBroker
from greeks.black_scholes import BlackScholesCalculator
from greeks.iv_calculator import ImpliedVolatilityCalculator
from risk.pre_trade_validator import PreTradeValidator, TradeSignal
from risk.circuit_breakers import CircuitBreakers
from risk.portfolio_risk import PortfolioRiskManager
from risk.position_risk import PositionRiskManager
from strategy.strike_selector import StrikeSelector
from strategy.iron_condor import IronCondorStrategy
from monitoring.telegram_bot import TelegramNotifier
from monitoring.performance_tracker import PerformanceTracker
from database.database_manager import DatabaseManager


class TradingEngine:
    """
    Main trading engine
    Orchestrates all components and manages trading lifecycle
    """

    def __init__(self, config_dir: str = "config", trading_mode: str = "paper"):
        """
        Initialize trading engine

        Args:
            config_dir: Configuration directory
            trading_mode: 'paper' or 'live'
        """
        # Setup logging first
        self.logger = setup_logger(
            log_dir="logs",
            log_level="INFO",
            log_to_file=True,
            log_to_console=True
        )

        self.logger.info("="*80)
        self.logger.info("ALGORITHMIC OPTIONS TRADING SYSTEM - STARTING")
        self.logger.info("="*80)

        # Load configuration
        self.config_loader = ConfigLoader(config_dir)
        self.config = self.config_loader.get_config()
        self.trading_mode = trading_mode

        self.logger.info(f"Trading Mode: {trading_mode.upper()}")

        # Initialize components
        self._initialize_components()

        # System state
        self.is_running = False
        self.open_positions = []
        self.daily_stats = {
            'daily_pnl': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'consecutive_losses': 0,
            'circuit_breakers': 0
        }

    def _initialize_components(self):
        """Initialize all system components"""
        self.logger.info("Initializing components...")

        # Database
        db_config = self.config['database']
        self.db = DatabaseManager(db_config.get('path', 'data/trading.db'))

        # Broker
        if self.trading_mode == 'paper':
            self.broker = PaperTradingBroker(
                initial_capital=self.config['risk_limits'].get('total_capital', 50000)
            )
        else:
            self.broker = AngelOneBroker(self.config['credentials'])

        # Greeks calculator
        self.bs_calc = BlackScholesCalculator(
            risk_free_rate=self.config.get('risk_free_rate', 0.065)
        )
        self.iv_calc = ImpliedVolatilityCalculator(self.bs_calc)

        # Risk management
        self.pre_trade_validator = PreTradeValidator({'risk_limits': self.config['risk_limits']})
        self.circuit_breakers = CircuitBreakers(self.config['risk_limits'])
        self.portfolio_risk = PortfolioRiskManager(self.config['risk_limits'])
        self.position_risk = PositionRiskManager(self.config['risk_limits'])

        # Strike selector
        strike_intervals = {
            'NIFTY': 50,
            'BANKNIFTY': 100,
            'FINNIFTY': 50
        }
        self.strike_selector = StrikeSelector(self.iv_calc, strike_intervals)

        # Strategies
        self._initialize_strategies()

        # Monitoring
        self.telegram = TelegramNotifier(self.config['telegram'])
        self.performance = PerformanceTracker()

        self.logger.info("✅ All components initialized")

    def _initialize_strategies(self):
        """Initialize trading strategies"""
        self.strategies = []

        # Iron Condor
        if self.config['strategy_params'].get('iron_condor', {}).get('enabled', True):
            self.strategies.append(
                IronCondorStrategy(
                    self.config['strategy_params']['iron_condor'],
                    self.strike_selector
                )
            )

        # Add other strategies as needed

        self.logger.info(f"Loaded {len(self.strategies)} strategies")

    def start(self):
        """Start the trading engine"""
        self.logger.info("Starting trading engine...")

        # Connect to broker
        if not self.broker.connect():
            self.logger.error("Failed to connect to broker")
            return False

        # Send startup notification
        self.telegram.notify_startup(self.trading_mode)

        self.is_running = True
        self.logger.info("✅ Trading engine started")

        # Main trading loop
        try:
            self._trading_loop()
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def _trading_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                current_time = datetime.now()

                # Check if within trading hours
                if not self._is_trading_hours(current_time):
                    self.logger.debug("Outside trading hours, waiting...")
                    time_module.sleep(60)
                    continue

                # Check circuit breakers
                if not self._check_circuit_breakers(current_time):
                    self.logger.warning("Circuit breaker active, trading halted")
                    time_module.sleep(60)
                    continue

                # Update open positions
                self._monitor_positions(current_time)

                # Check for new entry signals (if allowed)
                if self._can_enter_new_positions(current_time):
                    self._check_entry_signals(current_time)

                # Force square-off time check
                if self._is_force_square_off_time(current_time):
                    self.logger.critical("🚨 Force square-off time reached!")
                    self._emergency_square_off()

                # Sleep before next iteration
                time_module.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in trading loop iteration: {e}", exc_info=True)
                time_module.sleep(10)

    def _is_trading_hours(self, current_time: datetime) -> bool:
        """Check if current time is within trading hours"""
        current_time_only = current_time.time()
        trading_hours = self.config['trading_hours']['trading_windows']

        start_time = time.fromisoformat(trading_hours['trading_start'])
        end_time = time.fromisoformat(trading_hours['trading_end'])

        return start_time <= current_time_only <= end_time

    def _check_circuit_breakers(self, current_time: datetime) -> bool:
        """Check all circuit breakers"""
        market_data = {
            'vix': 15,  # Would come from live data
        }

        system_stats = {
            'api_latency_ms': 100,  # Would measure actual latency
            'margin_utilization_pct': 50
        }

        any_triggered = self.circuit_breakers.check_all_breakers(
            daily_stats=self.daily_stats,
            system_stats=system_stats,
            market_data=market_data,
            current_time=current_time
        )

        if any_triggered:
            # Send alert
            status = self.circuit_breakers.get_breaker_status()
            self.telegram.notify_circuit_breaker(
                "Multiple breakers",
                status['halt_reason']
            )

        return not any_triggered

    def _monitor_positions(self, current_time: datetime):
        """Monitor and update open positions"""
        self.open_positions = self.db.get_open_positions()

        for position in self.open_positions:
            # Get current prices (would come from market data)
            current_prices = {}  # Placeholder
            current_greeks = {}  # Placeholder

            # Check exit conditions
            risk_status = self.position_risk.get_position_risk_status(
                position, current_prices, current_greeks
            )

            if risk_status['should_exit']:
                self._exit_position(position, risk_status['exit_reason'])

    def _can_enter_new_positions(self, current_time: datetime) -> bool:
        """Check if new positions can be entered"""
        # Check time
        if current_time.time() >= time.fromisoformat("15:00"):
            return False

        # Check position limits
        if len(self.open_positions) >= self.config['risk_limits'].get('max_positions', 5):
            return False

        # Check if circuit breakers allow
        if not self.circuit_breakers.is_trading_allowed():
            return False

        return True

    def _check_entry_signals(self, current_time: datetime):
        """Check for entry signals from strategies"""
        # Get market data (simplified - would come from data layer)
        market_data = {
            'symbol': 'BANKNIFTY',
            'spot_price': 45000,
            'vix': 15,
            'days_to_expiry': 7,
            'expiry_date': '2025-11-06'
        }

        option_chain = []  # Would come from broker

        for strategy in self.strategies:
            signal = strategy.generate_entry_signal(
                market_data, option_chain, self.open_positions
            )

            if signal:
                self._process_entry_signal(signal)

    def _process_entry_signal(self, signal: TradeSignal):
        """Process and validate entry signal"""
        self.logger.info(f"Processing entry signal: {signal.strategy_name}")

        # Pre-trade validation
        validation = self.pre_trade_validator.validate_trade(
            signal, self.open_positions, self.daily_stats
        )

        if not validation.approved:
            self.logger.warning(f"Trade rejected: {validation.reason}")
            return

        # Execute trade
        self._execute_entry(signal)

    def _execute_entry(self, signal: TradeSignal):
        """Execute trade entry"""
        self.logger.info(f"Executing entry: {signal.strategy_name}")

        # Place orders for all legs
        order_ids = []
        for leg in signal.legs:
            order = {
                'symbol': leg['symbol'],
                'transaction_type': 'BUY' if leg['action'] == 'BUY' else 'SELL',
                'quantity': leg['quantity'],
                'price': leg['price'],
                'order_type': 'LIMIT'
            }

            order_id = self.broker.place_order(order)
            if order_id:
                order_ids.append(order_id)
            else:
                self.logger.error(f"Failed to place order for leg: {leg}")
                # Cancel other orders
                for oid in order_ids:
                    self.broker.cancel_order(oid)
                return

        # Store position in database
        position_data = {
            'entry_time': signal.timestamp,
            'strategy_name': signal.strategy_name,
            'symbol': signal.symbol,
            'expiry_date': signal.expiry_date,
            'legs': signal.legs,
            'entry_premium': sum(leg['price'] * leg['quantity'] for leg in signal.legs),
            'max_loss': signal.max_loss,
            'max_profit': signal.max_profit,
            'target_profit_pct': signal.target_profit_pct,
            'stop_loss_pct': signal.stop_loss_pct
        }

        position_id = self.db.insert_position(position_data)

        # Send notification
        self.telegram.notify_trade_entry(signal.__dict__)

        self.logger.info(f"✅ Position entered: ID={position_id}")

    def _exit_position(self, position: Dict, reason: str):
        """Exit position"""
        self.logger.info(f"Exiting position: {position['strategy_name']} - {reason}")

        # Place exit orders
        # ... order placement logic ...

        # Calculate P&L
        pnl = 0  # Would calculate from actual fills

        # Update database
        exit_data = {
            'exit_time': datetime.now(),
            'exit_premium': 0,  # Actual exit premium
            'pnl': pnl,
            'exit_reason': reason,
            'holding_time_minutes': 0
        }

        self.db.close_position(position['id'], exit_data)

        # Update daily stats
        self.daily_stats['total_trades'] += 1
        if pnl > 0:
            self.daily_stats['winning_trades'] += 1
            self.daily_stats['consecutive_losses'] = 0
        else:
            self.daily_stats['losing_trades'] += 1
            self.daily_stats['consecutive_losses'] += 1

        self.daily_stats['daily_pnl'] += pnl

        # Send notification
        self.telegram.notify_trade_exit(position, reason, pnl)

        # Record for performance tracking
        self.performance.record_trade({
            **position,
            'pnl': pnl,
            'exit_time': datetime.now()
        })

        self.logger.info(f"✅ Position exited: P&L=₹{pnl:.2f}")

    def _is_force_square_off_time(self, current_time: datetime) -> bool:
        """Check if force square-off time reached"""
        force_time = time.fromisoformat(
            self.config['trading_hours']['trading_windows']['force_square_off']
        )
        return current_time.time() >= force_time

    def _emergency_square_off(self):
        """Emergency square-off all positions"""
        self.logger.critical("🚨 EMERGENCY SQUARE-OFF INITIATED")

        for position in self.open_positions:
            self._exit_position(position, "Emergency square-off")

        self.telegram.notify_system_error(
            "Emergency Square-off",
            "All positions closed at market close"
        )

    def shutdown(self):
        """Shutdown trading engine"""
        self.logger.info("Shutting down trading engine...")

        # Send daily summary
        summary = self.daily_stats.copy()
        summary['win_rate'] = (
            (summary['winning_trades'] / summary['total_trades'] * 100)
            if summary['total_trades'] > 0 else 0
        )
        summary['max_drawdown'] = 0  # Would calculate

        self.telegram.notify_daily_summary(summary)

        # Logout from broker
        self.broker.logout()

        # Close database connections
        # ... cleanup ...

        self.telegram.notify_shutdown("Normal shutdown")

        self.logger.info("="*80)
        self.logger.info("TRADING ENGINE SHUTDOWN COMPLETE")
        self.logger.info("="*80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Algorithmic Options Trading System")
    parser.add_argument(
        '--mode',
        choices=['paper', 'live'],
        default='paper',
        help='Trading mode (default: paper)'
    )
    parser.add_argument(
        '--config-dir',
        default='config',
        help='Configuration directory (default: config)'
    )

    args = parser.parse_args()

    # Safety check for live mode
    if args.mode == 'live':
        print("\n" + "="*80)
        print("⚠️  WARNING: LIVE TRADING MODE")
        print("="*80)
        print("You are about to start live trading with real money.")
        print("Have you completed 6+ months of successful paper trading?")
        confirm = input("Type 'YES I AM READY' to continue: ")

        if confirm != "YES I AM READY":
            print("Live trading cancelled. Use --mode paper for paper trading.")
            sys.exit(0)

    # Create and start trading engine
    engine = TradingEngine(
        config_dir=args.config_dir,
        trading_mode=args.mode
    )

    engine.start()


if __name__ == "__main__":
    main()
