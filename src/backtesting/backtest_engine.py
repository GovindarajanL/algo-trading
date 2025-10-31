"""
Backtesting Engine
Replays historical data and tests strategies
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import pandas as pd
from dataclasses import dataclass


@dataclass
class BacktestTrade:
    """Trade record for backtesting"""
    entry_date: datetime
    exit_date: datetime
    strategy_name: str
    symbol: str
    entry_premium: float
    exit_premium: float
    pnl: float
    max_loss: float
    max_profit: float
    holding_time_minutes: int
    exit_reason: str


class BacktestEngine:
    """
    Backtesting engine for strategy validation
    Replays historical data and simulates trading
    """

    def __init__(
        self,
        config: Dict,
        strategies: List,
        historical_data_fetcher
    ):
        """
        Initialize backtest engine

        Args:
            config: System configuration
            strategies: List of strategy instances to test
            historical_data_fetcher: Historical data provider
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.strategies = strategies
        self.data_fetcher = historical_data_fetcher

        # Backtest state
        self.current_positions = []
        self.completed_trades = []
        self.daily_pnl = {}
        self.equity_curve = []
        self.initial_capital = config.get('risk_limits', {}).get('total_capital', 50000)
        self.current_capital = self.initial_capital

        # Initialize risk management for backtesting
        from src.risk.pre_trade_validator import PreTradeValidator
        from src.risk.circuit_breakers import CircuitBreakers
        from src.risk.position_risk import PositionRiskManager

        self.validator = PreTradeValidator(config)
        self.breakers = CircuitBreakers(config.get('risk_limits', {}))
        self.position_risk = PositionRiskManager(config.get('risk_limits', {}))

        self.logger.info("Backtest Engine initialized")

    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: str = 'BANKNIFTY'
    ) -> Dict:
        """
        Run backtest for given date range

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            symbol: Underlying symbol to trade

        Returns:
            Dictionary with backtest results
        """
        self.logger.info(f"Starting backtest: {start_date} to {end_date}")

        # Reset state
        self._reset_state()

        # Fetch historical data
        historical_candles = self.data_fetcher.fetch_historical_candles(
            symbol, start_date, end_date, interval='5MINUTE'
        )

        if historical_candles.empty:
            self.logger.error("No historical data available")
            return {}

        self.logger.info(f"Loaded {len(historical_candles)} candles for backtesting")

        # Group by trading days
        historical_candles['date'] = historical_candles['timestamp'].dt.date
        trading_days = historical_candles.groupby('date')

        # Simulate each trading day
        for date, day_data in trading_days:
            self._simulate_trading_day(date, day_data, symbol)

        # Calculate results
        results = self._calculate_backtest_results()

        self.logger.info(f"Backtest completed: {len(self.completed_trades)} trades")

        return results

    def _simulate_trading_day(
        self,
        date,
        day_data: pd.DataFrame,
        symbol: str
    ):
        """
        Simulate one trading day

        Args:
            date: Trading date
            day_data: Minute-by-minute data for the day
            symbol: Underlying symbol
        """
        self.logger.debug(f"Simulating {date}")

        # Reset daily stats
        daily_stats = {
            'daily_pnl': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'consecutive_losses': 0
        }

        # Get expiry date (simplified - would need actual calendar)
        expiry_date = self._get_next_expiry(date, symbol)

        # Iterate through the day minute by minute
        for idx, row in day_data.iterrows():
            current_time = row['timestamp']
            spot_price = row['close']

            # Check circuit breakers
            if self._check_circuit_breakers(current_time, daily_stats):
                self.logger.debug(f"Circuit breaker active at {current_time}")
                continue

            # Update existing positions
            self._update_positions(current_time, spot_price, daily_stats)

            # Check for entry signals (only during trading hours)
            if self._can_enter_new_position(current_time):
                self._check_entry_signals(
                    current_time, spot_price, symbol, expiry_date, daily_stats
                )

        # Force close any remaining positions at EOD
        self._force_close_positions(date, spot_price, "EOD square-off")

        # Record daily P&L
        self.daily_pnl[date] = daily_stats['daily_pnl']
        self.equity_curve.append({
            'date': date,
            'equity': self.current_capital,
            'daily_pnl': daily_stats['daily_pnl']
        })

    def _check_entry_signals(
        self,
        current_time: datetime,
        spot_price: float,
        symbol: str,
        expiry_date: str,
        daily_stats: Dict
    ):
        """Check for entry signals from strategies"""

        # Get market data
        market_data = {
            'symbol': symbol,
            'spot_price': spot_price,
            'vix': 15,  # Would need actual VIX data
            'days_to_expiry': self._calculate_dte(current_time, expiry_date),
            'expiry_date': expiry_date
        }

        # Get option chain (would use historical data in real backtest)
        option_chain = self.data_fetcher.fetch_option_chain_historical(
            symbol, expiry_date, current_time
        )

        # Check each strategy
        for strategy in self.strategies:
            signal = strategy.generate_entry_signal(
                market_data, option_chain, self.current_positions
            )

            if signal:
                # Validate with risk management
                validation = self.validator.validate_trade(
                    signal, self.current_positions, daily_stats
                )

                if validation.approved:
                    self._execute_entry(signal, current_time)

    def _execute_entry(self, signal, entry_time: datetime):
        """Execute trade entry in backtest"""

        # Calculate entry premium
        entry_premium = sum(
            leg['price'] * leg['quantity'] * (1 if leg['action'] == 'SELL' else -1)
            for leg in signal.legs
        )

        position = {
            'id': len(self.current_positions) + 1,
            'entry_time': entry_time,
            'strategy_name': signal.strategy_name,
            'symbol': signal.symbol,
            'expiry_date': signal.expiry_date,
            'legs': signal.legs,
            'entry_premium': abs(entry_premium),
            'max_loss': signal.max_loss,
            'max_profit': signal.max_profit,
            'target_profit_pct': signal.target_profit_pct,
            'stop_loss_pct': signal.stop_loss_pct
        }

        self.current_positions.append(position)
        self.current_capital -= signal.margin_required

        self.logger.debug(
            f"Entered {signal.strategy_name} at {entry_time}: "
            f"Premium=₹{entry_premium:.2f}"
        )

    def _update_positions(
        self,
        current_time: datetime,
        spot_price: float,
        daily_stats: Dict
    ):
        """Update and check exit conditions for open positions"""

        positions_to_close = []

        for position in self.current_positions:
            # Simulate current option prices (simplified)
            current_prices = self._simulate_option_prices(
                position, spot_price, current_time
            )

            # Calculate current P&L
            current_value = sum(
                current_prices.get(self._get_leg_id(leg), leg['price'])
                * leg['quantity']
                * (1 if leg['action'] == 'SELL' else -1)
                for leg in position['legs']
            )

            current_pnl = position['entry_premium'] - abs(current_value)

            # Check exit conditions
            exit_reason = self._check_exit_conditions(
                position, current_pnl, current_time
            )

            if exit_reason:
                positions_to_close.append((position, current_pnl, exit_reason))

        # Close positions
        for position, pnl, reason in positions_to_close:
            self._close_position(position, current_time, pnl, reason, daily_stats)

    def _check_exit_conditions(
        self,
        position: Dict,
        current_pnl: float,
        current_time: datetime
    ) -> Optional[str]:
        """Check if position should be exited"""

        # Target profit
        target_profit = position['max_profit'] * (position['target_profit_pct'] / 100)
        if current_pnl >= target_profit:
            return "Target profit reached"

        # Stop loss
        stop_loss = position['entry_premium'] * (position['stop_loss_pct'] / 100)
        if current_pnl <= -stop_loss:
            return "Stop loss hit"

        # Time-based exit (3:20 PM)
        if current_time.hour >= 15 and current_time.minute >= 20:
            return "Time-based exit"

        return None

    def _close_position(
        self,
        position: Dict,
        exit_time: datetime,
        pnl: float,
        reason: str,
        daily_stats: Dict
    ):
        """Close position and record trade"""

        # Calculate holding time
        holding_time = (exit_time - position['entry_time']).total_seconds() / 60

        # Create trade record
        trade = BacktestTrade(
            entry_date=position['entry_time'],
            exit_date=exit_time,
            strategy_name=position['strategy_name'],
            symbol=position['symbol'],
            entry_premium=position['entry_premium'],
            exit_premium=position['entry_premium'] - pnl,
            pnl=pnl,
            max_loss=position['max_loss'],
            max_profit=position['max_profit'],
            holding_time_minutes=int(holding_time),
            exit_reason=reason
        )

        self.completed_trades.append(trade)

        # Update capital and stats
        self.current_capital += pnl

        daily_stats['total_trades'] += 1
        daily_stats['daily_pnl'] += pnl

        if pnl > 0:
            daily_stats['winning_trades'] += 1
            daily_stats['consecutive_losses'] = 0
        else:
            daily_stats['losing_trades'] += 1
            daily_stats['consecutive_losses'] += 1

        # Remove from open positions
        self.current_positions = [
            p for p in self.current_positions if p['id'] != position['id']
        ]

        self.logger.debug(
            f"Closed {position['strategy_name']} at {exit_time}: "
            f"P&L=₹{pnl:.2f}, Reason={reason}"
        )

    def _force_close_positions(self, date, spot_price: float, reason: str):
        """Force close all positions at end of day"""

        for position in self.current_positions[:]:  # Copy to avoid modification during iteration
            # Assume small loss/profit for forced close
            pnl = 0  # Neutral close
            self._close_position(
                position,
                datetime.combine(date, datetime.min.time().replace(hour=15, minute=30)),
                pnl,
                reason,
                {}
            )

    def _simulate_option_prices(
        self,
        position: Dict,
        spot_price: float,
        current_time: datetime
    ) -> Dict:
        """Simulate current option prices (simplified)"""

        prices = {}
        for leg in position['legs']:
            leg_id = self._get_leg_id(leg)

            # Simplified price simulation based on moneyness
            strike = leg['strike']
            option_type = leg['option_type']

            if option_type == 'CE':
                intrinsic = max(spot_price - strike, 0)
            else:  # PE
                intrinsic = max(strike - spot_price, 0)

            # Add time value (decaying)
            time_value = leg['price'] * 0.5  # Simplified
            prices[leg_id] = intrinsic + time_value

        return prices

    def _get_leg_id(self, leg: Dict) -> str:
        """Generate unique ID for leg"""
        return f"{leg['symbol']}_{leg['strike']}_{leg['option_type']}"

    def _can_enter_new_position(self, current_time: datetime) -> bool:
        """Check if new positions can be entered"""
        # After 3 PM, no new entries
        if current_time.hour >= 15:
            return False

        # Check position limits
        max_positions = self.config.get('risk_limits', {}).get('max_positions', 5)
        if len(self.current_positions) >= max_positions:
            return False

        return True

    def _check_circuit_breakers(
        self,
        current_time: datetime,
        daily_stats: Dict
    ) -> bool:
        """Check if circuit breakers are triggered"""

        system_stats = {
            'api_latency_ms': 100,
            'margin_utilization_pct': 50
        }

        market_data = {'vix': 15}

        return self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, current_time
        )

    def _get_next_expiry(self, date, symbol: str) -> str:
        """Get next expiry date (simplified)"""
        # For BANKNIFTY: Wednesday expiry
        # For NIFTY: Thursday expiry

        from datetime import timedelta

        current_date = pd.to_datetime(date)

        if symbol == 'BANKNIFTY':
            target_weekday = 2  # Wednesday
        elif symbol == 'NIFTY':
            target_weekday = 3  # Thursday
        else:
            target_weekday = 2

        days_ahead = target_weekday - current_date.weekday()
        if days_ahead <= 0:
            days_ahead += 7

        expiry = current_date + timedelta(days=days_ahead)
        return expiry.strftime('%Y-%m-%d')

    def _calculate_dte(self, current_time: datetime, expiry_date: str) -> int:
        """Calculate days to expiry"""
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        return (expiry - current_time).days

    def _reset_state(self):
        """Reset backtest state"""
        self.current_positions = []
        self.completed_trades = []
        self.daily_pnl = {}
        self.equity_curve = []
        self.current_capital = self.initial_capital

    def _calculate_backtest_results(self) -> Dict:
        """Calculate comprehensive backtest results"""

        if not self.completed_trades:
            return {'error': 'No trades executed'}

        # Basic metrics
        total_trades = len(self.completed_trades)
        winning_trades = [t for t in self.completed_trades if t.pnl > 0]
        losing_trades = [t for t in self.completed_trades if t.pnl < 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in self.completed_trades)
        avg_win = sum(t.pnl for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t.pnl for t in losing_trades) / loss_count if loss_count > 0 else 0

        # Risk metrics
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # Drawdown
        equity_values = [self.initial_capital] + [
            e['equity'] for e in self.equity_curve
        ]
        drawdowns = self._calculate_drawdowns(equity_values)
        max_drawdown = max(drawdowns) if drawdowns else 0

        # Sharpe ratio
        returns = [t.pnl for t in self.completed_trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)

        results = {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_return_pct': (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            'avg_holding_time_minutes': sum(t.holding_time_minutes for t in self.completed_trades) / total_trades if total_trades > 0 else 0,
            'trades': [
                {
                    'entry': t.entry_date.strftime('%Y-%m-%d %H:%M'),
                    'exit': t.exit_date.strftime('%Y-%m-%d %H:%M'),
                    'strategy': t.strategy_name,
                    'pnl': t.pnl,
                    'reason': t.exit_reason
                }
                for t in self.completed_trades
            ],
            'equity_curve': self.equity_curve,
            'daily_pnl': self.daily_pnl
        }

        return results

    def _calculate_drawdowns(self, equity_values: List[float]) -> List[float]:
        """Calculate drawdown series"""
        drawdowns = []
        peak = equity_values[0]

        for value in equity_values:
            if value > peak:
                peak = value

            dd = (peak - value) / peak * 100 if peak > 0 else 0
            drawdowns.append(dd)

        return drawdowns

    def _calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.065
    ) -> float:
        """Calculate Sharpe ratio"""
        import numpy as np

        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize (assuming 252 trading days)
        sharpe = (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)

        return sharpe
