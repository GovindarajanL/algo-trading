"""
Performance Metrics Tracker
REQ-MON-023 to REQ-MON-029
"""

from typing import Dict, List
from datetime import datetime
import logging
import math


class PerformanceTracker:
    """
    Track and calculate performance metrics
    REQ-MON-023 to REQ-MON-029: Performance metrics
    """

    def __init__(self):
        """Initialize performance tracker"""
        self.logger = logging.getLogger(__name__)
        self.trades = []
        self.daily_pnl = []
        self.equity_curve = []

    def record_trade(self, trade: Dict):
        """
        Record completed trade
        REQ-MON-023: Track total trades

        Args:
            trade: Dictionary with trade details
        """
        self.trades.append({
            'timestamp': trade.get('exit_time', datetime.now()),
            'strategy': trade.get('strategy_name'),
            'symbol': trade.get('symbol'),
            'pnl': trade.get('pnl', 0),
            'max_loss': trade.get('max_loss', 0),
            'max_profit': trade.get('max_profit', 0),
            'entry_premium': trade.get('entry_premium', 0),
            'exit_premium': trade.get('exit_premium', 0),
            'holding_time_minutes': trade.get('holding_time_minutes', 0)
        })

        self.logger.debug(f"Trade recorded: P&L=₹{trade.get('pnl', 0):.2f}")

    def calculate_metrics(self) -> Dict:
        """
        Calculate all performance metrics
        Returns comprehensive performance statistics
        """
        if not self.trades:
            return self._empty_metrics()

        # Total trades (REQ-MON-023)
        total_trades = len(self.trades)

        # Win/Loss ratio (REQ-MON-024)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        breakeven_trades = [t for t in self.trades if t['pnl'] == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        # P&L calculations
        total_pnl = sum(t['pnl'] for t in self.trades)
        avg_win = sum(t['pnl'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / loss_count if loss_count > 0 else 0
        largest_win = max((t['pnl'] for t in winning_trades), default=0)
        largest_loss = min((t['pnl'] for t in losing_trades), default=0)

        # Sharpe Ratio (REQ-MON-025)
        sharpe_ratio = self._calculate_sharpe_ratio()

        # Maximum Drawdown (REQ-MON-026)
        max_drawdown = self._calculate_max_drawdown()

        # Profit Factor (REQ-MON-027)
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # Average Holding Time (REQ-MON-028)
        avg_holding_time = (
            sum(t['holding_time_minutes'] for t in self.trades) / total_trades
            if total_trades > 0 else 0
        )

        # Consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive()

        # Risk-adjusted return
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'breakeven_trades': len(breakeven_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_holding_time_minutes': avg_holding_time,
            'max_consecutive_wins': consecutive_wins,
            'max_consecutive_losses': consecutive_losses
        }

    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.065) -> float:
        """
        Calculate Sharpe Ratio
        REQ-MON-025: Sharpe ratio calculation

        Sharpe Ratio = (Mean Return - Risk Free Rate) / Std Dev of Returns
        """
        if len(self.trades) < 2:
            return 0.0

        returns = [t['pnl'] for t in self.trades]
        mean_return = sum(returns) / len(returns)

        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # Annualize (assuming 252 trading days)
        sharpe = (mean_return - risk_free_rate / 252) / std_dev * math.sqrt(252)

        return sharpe

    def _calculate_max_drawdown(self) -> float:
        """
        Calculate Maximum Drawdown
        REQ-MON-026: Maximum drawdown calculation

        Max DD = (Trough - Peak) / Peak
        """
        if not self.trades:
            return 0.0

        # Build equity curve
        equity = [0]
        for trade in self.trades:
            equity.append(equity[-1] + trade['pnl'])

        # Calculate drawdown
        max_dd = 0
        peak = equity[0]

        for value in equity:
            if value > peak:
                peak = value

            dd = peak - value
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_consecutive(self) -> tuple:
        """Calculate maximum consecutive wins and losses"""
        if not self.trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.trades:
            if trade['pnl'] > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade['pnl'] < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:  # Breakeven
                current_wins = 0
                current_losses = 0

        return max_wins, max_losses

    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'avg_holding_time_minutes': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }

    def get_strategy_breakdown(self) -> Dict:
        """Get performance breakdown by strategy"""
        strategy_metrics = {}

        for trade in self.trades:
            strategy = trade['strategy']
            if strategy not in strategy_metrics:
                strategy_metrics[strategy] = {
                    'trades': [],
                    'total_pnl': 0,
                    'wins': 0,
                    'losses': 0
                }

            strategy_metrics[strategy]['trades'].append(trade)
            strategy_metrics[strategy]['total_pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                strategy_metrics[strategy]['wins'] += 1
            elif trade['pnl'] < 0:
                strategy_metrics[strategy]['losses'] += 1

        # Calculate stats for each strategy
        for strategy, data in strategy_metrics.items():
            total = len(data['trades'])
            data['win_rate'] = (data['wins'] / total * 100) if total > 0 else 0
            data['avg_pnl'] = data['total_pnl'] / total if total > 0 else 0

        return strategy_metrics

    def generate_report(self) -> str:
        """
        Generate performance report
        REQ-MON-029: Generate performance reports
        """
        metrics = self.calculate_metrics()

        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE REPORT")
        report.append("=" * 60)
        report.append("")
        report.append(f"Total Trades: {metrics['total_trades']}")
        report.append(f"Winning Trades: {metrics['winning_trades']}")
        report.append(f"Losing Trades: {metrics['losing_trades']}")
        report.append(f"Win Rate: {metrics['win_rate']:.2f}%")
        report.append("")
        report.append(f"Total P&L: ₹{metrics['total_pnl']:.2f}")
        report.append(f"Average P&L: ₹{metrics['avg_pnl']:.2f}")
        report.append(f"Average Win: ₹{metrics['avg_win']:.2f}")
        report.append(f"Average Loss: ₹{metrics['avg_loss']:.2f}")
        report.append(f"Largest Win: ₹{metrics['largest_win']:.2f}")
        report.append(f"Largest Loss: ₹{metrics['largest_loss']:.2f}")
        report.append("")
        report.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        report.append(f"Max Drawdown: ₹{metrics['max_drawdown']:.2f}")
        report.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
        report.append("")
        report.append(f"Avg Holding Time: {metrics['avg_holding_time_minutes']:.0f} min")
        report.append(f"Max Consecutive Wins: {metrics['max_consecutive_wins']}")
        report.append(f"Max Consecutive Losses: {metrics['max_consecutive_losses']}")
        report.append("=" * 60)

        return "\n".join(report)
