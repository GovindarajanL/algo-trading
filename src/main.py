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
        """
        Monitor and update open positions
        Fetches current prices, calculates Greeks, checks exit conditions
        """
        self.open_positions = self.db.get_open_positions()

        if not self.open_positions:
            return

        self.logger.debug(f"Monitoring {len(self.open_positions)} open positions")

        for position in self.open_positions:
            try:
                # Get position legs
                legs = position.get('legs', [])
                if isinstance(legs, str):
                    import json
                    legs = json.loads(legs)

                # Fetch current prices for all legs
                current_prices = {}
                symbols = [leg.get('symbol', leg.get('tradingsymbol', '')) for leg in legs]

                try:
                    # Batch fetch LTPs for efficiency
                    ltp_data = self.broker.get_ltp_batch(symbols) if hasattr(self.broker, 'get_ltp_batch') else {}

                    for leg in legs:
                        symbol = leg.get('symbol', leg.get('tradingsymbol', ''))
                        if symbol in ltp_data:
                            current_prices[symbol] = ltp_data[symbol]
                        else:
                            # Fallback: fetch individually
                            market_data = self.broker.get_market_data(symbol)
                            if market_data:
                                current_prices[symbol] = market_data.get('ltp', 0)

                except Exception as e:
                    self.logger.warning(f"Error fetching prices for position {position.get('id')}: {e}")
                    continue

                # Calculate current position value
                current_position_value = 0
                for leg in legs:
                    symbol = leg.get('symbol', leg.get('tradingsymbol', ''))
                    quantity = leg.get('quantity', 0)
                    current_price = current_prices.get(symbol, 0)

                    # For sold options, we receive premium (negative in P&L calc)
                    if leg.get('action') == 'SELL':
                        current_position_value -= current_price * quantity
                    else:  # BUY
                        current_position_value += current_price * quantity

                # Calculate P&L
                entry_premium = position.get('entry_premium', 0)
                current_pnl = entry_premium - current_position_value

                # Calculate current Greeks for the position
                current_greeks = {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}

                try:
                    # Get market data for underlying
                    underlying_symbol = position.get('symbol', 'BANKNIFTY')
                    spot_data = self.broker.get_market_data(underlying_symbol)
                    spot_price = spot_data.get('ltp', 45000) if spot_data else 45000

                    # Calculate time to expiry
                    expiry_str = position.get('expiry_date', '')
                    if expiry_str:
                        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                        dte_days = (expiry_date - datetime.now().date()).days
                        time_to_expiry = max(dte_days / 365.0, 0.001)  # Avoid zero

                        # Calculate Greeks for each leg and aggregate
                        for leg in legs:
                            strike = leg.get('strike', 0)
                            option_type = leg.get('option_type', 'CE')
                            quantity = leg.get('quantity', 0)
                            action = leg.get('action', 'BUY')

                            if strike > 0:
                                # Use current market IV or default
                                volatility = 0.25  # Default 25% IV (could fetch actual IV)

                                leg_greeks = self.bs_calc.calculate_greeks(
                                    spot_price=spot_price,
                                    strike_price=strike,
                                    time_to_expiry=time_to_expiry,
                                    volatility=volatility,
                                    option_type=option_type
                                )

                                # Aggregate Greeks (sold options have negative Greeks)
                                multiplier = quantity if action == 'BUY' else -quantity

                                for greek in ['delta', 'gamma', 'theta', 'vega', 'rho']:
                                    current_greeks[greek] += leg_greeks.get(greek, 0) * multiplier

                except Exception as e:
                    self.logger.warning(f"Error calculating Greeks: {e}")

                # Update position in database
                self.db.update_position(position['id'], {
                    'current_value': current_position_value,
                    'current_pnl': current_pnl,
                    'current_greeks': str(current_greeks),
                    'last_update': datetime.now().isoformat()
                })

                # Check exit conditions
                should_exit = False
                exit_reason = ""

                # 1. Check profit target
                target_profit = position.get('target_profit', 0)
                if target_profit > 0 and current_pnl >= target_profit:
                    should_exit = True
                    exit_reason = f"Target profit reached (₹{current_pnl:.2f})"

                # 2. Check stop loss
                max_loss = position.get('max_loss', 0)
                stop_loss_amount = position.get('stop_loss', max_loss)
                if current_pnl <= -stop_loss_amount:
                    should_exit = True
                    exit_reason = f"Stop loss hit (₹{current_pnl:.2f})"

                # 3. Check Greeks limits
                greeks_check = self.position_risk.check_position_greeks(current_greeks)
                if not greeks_check.get('all_within_limits', True):
                    should_exit = True
                    exit_reason = f"Greeks limit breach: {greeks_check.get('violations', [])}"

                # 4. Check time-based exit (expiry day exit)
                if hasattr(self, 'nse_calendar'):
                    if self.nse_calendar.is_expiry_day(underlying_symbol, datetime.now().date()):
                        if current_time.time() >= time.fromisoformat("15:00"):
                            should_exit = True
                            exit_reason = "Expiry day - closing before 3:20 PM"

                # 5. Risk manager override
                try:
                    position_with_prices = position.copy()
                    position_with_prices['current_price'] = current_position_value / position.get('quantity', 1)
                    position_with_prices['current_pnl'] = current_pnl

                    risk_should_exit, risk_reason = self.position_risk.should_exit(
                        position_with_prices,
                        current_greeks
                    )

                    if risk_should_exit:
                        should_exit = True
                        exit_reason = risk_reason

                except Exception as e:
                    self.logger.warning(f"Error in risk manager check: {e}")

                # Execute exit if needed
                if should_exit:
                    self.logger.info(
                        f"Exit signal for position {position.get('id')}: {exit_reason}"
                    )
                    self._exit_position(position, exit_reason, current_prices, current_pnl)

                # Log position status
                self.logger.debug(
                    f"Position {position.get('id')}: {position.get('strategy_name')} | "
                    f"P&L: ₹{current_pnl:.2f} | Delta: {current_greeks['delta']:.2f}"
                )

            except Exception as e:
                self.logger.error(f"Error monitoring position {position.get('id')}: {e}")
                continue

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

    def _exit_position(self, position: Dict, reason: str, current_prices: Dict = None, calculated_pnl: float = None):
        """
        Exit position by placing orders to close all legs

        Args:
            position: Position dictionary
            reason: Exit reason
            current_prices: Current market prices for the legs
            calculated_pnl: Pre-calculated P&L (optional)
        """
        self.logger.info(f"Exiting position {position.get('id')}: {position['strategy_name']} - {reason}")

        # Get legs
        legs = position.get('legs', [])
        if isinstance(legs, str):
            import json
            legs = json.loads(legs)

        # Place exit orders for all legs (reverse the original action)
        exit_order_ids = []
        exit_fills = []

        for leg in legs:
            try:
                symbol = leg.get('symbol', leg.get('tradingsymbol', ''))
                quantity = leg.get('quantity', 0)
                original_action = leg.get('action', 'BUY')

                # Reverse the action to close
                exit_action = 'SELL' if original_action == 'BUY' else 'BUY'

                # Get current price or use last known
                if current_prices and symbol in current_prices:
                    exit_price = current_prices[symbol]
                else:
                    # Fetch current price
                    market_data = self.broker.get_market_data(symbol)
                    exit_price = market_data.get('ltp', 0) if market_data else 0

                # Place market order for immediate exit
                exit_order = {
                    'symbol': symbol,
                    'transaction_type': exit_action,
                    'quantity': quantity,
                    'order_type': 'MARKET',  # Market order for quick exit
                    'product_type': 'INTRADAY'
                }

                self.logger.info(
                    f"Placing exit order: {exit_action} {quantity} x {symbol} @ MARKET"
                )

                order_id = self.broker.place_order(exit_order)

                if order_id:
                    exit_order_ids.append(order_id)
                    exit_fills.append({
                        'symbol': symbol,
                        'price': exit_price,
                        'quantity': quantity,
                        'action': exit_action
                    })
                    self.logger.info(f"✅ Exit order placed: {order_id}")
                else:
                    self.logger.error(f"❌ Failed to place exit order for {symbol}")

            except Exception as e:
                self.logger.error(f"Error placing exit order for leg: {e}")
                continue

        # Calculate exit premium and P&L
        exit_premium = 0
        for fill in exit_fills:
            price = fill['price']
            quantity = fill['quantity']
            action = fill['action']

            # For exit: SELL gives us money (positive), BUY costs money (negative)
            if action == 'SELL':
                exit_premium += price * quantity
            else:  # BUY
                exit_premium -= price * quantity

        # Calculate P&L
        entry_premium = position.get('entry_premium', 0)

        if calculated_pnl is not None:
            # Use pre-calculated P&L
            pnl = calculated_pnl
        else:
            # Calculate from entry and exit premiums
            # P&L = Entry Premium - Exit Premium
            # (For a credit spread, we want exit premium to be less than entry)
            pnl = entry_premium - exit_premium

        # Calculate holding time
        entry_time_str = position.get('entry_time', '')
        if entry_time_str:
            try:
                entry_time = datetime.fromisoformat(entry_time_str)
                holding_minutes = (datetime.now() - entry_time).total_seconds() / 60
            except Exception:
                holding_minutes = 0
        else:
            holding_minutes = 0

        # Update database
        exit_data = {
            'exit_time': datetime.now().isoformat(),
            'exit_premium': exit_premium,
            'realized_pnl': pnl,
            'exit_reason': reason,
            'holding_time_minutes': int(holding_minutes),
            'exit_orders': str(exit_order_ids)
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
        try:
            self.telegram.notify_trade_exit(position, reason, pnl)
        except Exception as e:
            self.logger.warning(f"Failed to send exit notification: {e}")

        # Record for performance tracking
        try:
            self.performance.record_trade({
                **position,
                'pnl': pnl,
                'exit_time': datetime.now(),
                'exit_reason': reason,
                'holding_time_minutes': holding_minutes
            })
        except Exception as e:
            self.logger.warning(f"Failed to record trade in performance tracker: {e}")

        self.logger.info(
            f"✅ Position {position.get('id')} exited: "
            f"P&L=₹{pnl:.2f} | Holding Time={holding_minutes:.0f} mins"
        )

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
