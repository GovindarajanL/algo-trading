"""
Backtest Analyzer
Comprehensive analysis and visualization of backtest results
"""

from typing import Dict, List
import logging
import pandas as pd


class BacktestAnalyzer:
    """
    Analyze backtest results and generate reports
    """

    def __init__(self):
        """Initialize backtest analyzer"""
        self.logger = logging.getLogger(__name__)

    def generate_report(self, results: Dict) -> str:
        """
        Generate comprehensive text report

        Args:
            results: Backtest results dictionary

        Returns:
            Formatted report string
        """
        report = []
        report.append("="*80)
        report.append("BACKTEST RESULTS REPORT")
        report.append("="*80)

        # Summary
        report.append("\n📊 TRADING SUMMARY")
        report.append("-"*80)
        report.append(f"Total Trades:        {results['total_trades']}")
        report.append(f"Winning Trades:      {results['winning_trades']}")
        report.append(f"Losing Trades:       {results['losing_trades']}")
        report.append(f"Win Rate:            {results['win_rate']:.2f}%")

        # P&L
        report.append("\n💰 PROFIT & LOSS")
        report.append("-"*80)
        report.append(f"Initial Capital:     ₹{results['initial_capital']:,.2f}")
        report.append(f"Final Capital:       ₹{results['final_capital']:,.2f}")
        report.append(f"Total P&L:           ₹{results['total_pnl']:,.2f}")
        report.append(f"Total Return:        {results['total_return_pct']:.2f}%")
        report.append(f"Average Win:         ₹{results['avg_win']:,.2f}")
        report.append(f"Average Loss:        ₹{results['avg_loss']:,.2f}")

        # Risk Metrics
        report.append("\n📉 RISK METRICS")
        report.append("-"*80)
        report.append(f"Profit Factor:       {results['profit_factor']:.2f}")
        report.append(f"Sharpe Ratio:        {results['sharpe_ratio']:.3f}")
        report.append(f"Max Drawdown:        {results['max_drawdown']:.2f}%")

        # Trade Stats
        report.append("\n⏱️  TRADE STATISTICS")
        report.append("-"*80)
        report.append(f"Avg Holding Time:    {results['avg_holding_time_minutes']:.0f} minutes")

        # Rating
        rating = self._calculate_rating(results)
        report.append(f"\n{'='*80}")
        report.append(f"OVERALL RATING: {rating}")
        report.append(f"{'='*80}")

        return "\n".join(report)

    def generate_trade_log(self, results: Dict) -> str:
        """Generate detailed trade log"""
        log = []
        log.append("\n📝 TRADE LOG")
        log.append("="*100)

        for i, trade in enumerate(results['trades'], 1):
            pnl_symbol = "✅" if trade['pnl'] > 0 else "❌"
            log.append(
                f"{i}. {pnl_symbol} {trade['entry']} → {trade['exit']} | "
                f"{trade['strategy']} | P&L: ₹{trade['pnl']:.2f} | {trade['reason']}"
            )

        return "\n".join(log)

    def export_to_csv(self, results: Dict, filepath: str):
        """
        Export results to CSV

        Args:
            results: Backtest results
            filepath: Output CSV path
        """
        try:
            df = pd.DataFrame(results['trades'])
            df.to_csv(filepath, index=False)
            self.logger.info(f"Results exported to {filepath}")

        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")

    def plot_equity_curve(self, results: Dict, save_path: str = None):
        """
        Plot equity curve

        Args:
            results: Backtest results
            save_path: Path to save plot (optional)
        """
        try:
            import matplotlib.pyplot as plt

            equity_data = results['equity_curve']
            dates = [e['date'] for e in equity_data]
            equity_values = [e['equity'] for e in equity_data]

            plt.figure(figsize=(12, 6))
            plt.plot(dates, equity_values, linewidth=2)
            plt.axhline(y=results['initial_capital'], color='r', linestyle='--', label='Initial Capital')
            plt.title('Equity Curve', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Capital (₹)')
            plt.grid(True, alpha=0.3)
            plt.legend()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"Equity curve saved to {save_path}")
            else:
                plt.show()

        except ImportError:
            self.logger.warning("matplotlib not installed, skipping plot")
        except Exception as e:
            self.logger.error(f"Error plotting equity curve: {e}")

    def plot_drawdown(self, results: Dict, save_path: str = None):
        """Plot drawdown chart"""
        try:
            import matplotlib.pyplot as plt

            equity_data = results['equity_curve']
            dates = [e['date'] for e in equity_data]
            equity_values = [results['initial_capital']] + [e['equity'] for e in equity_data]

            # Calculate drawdown
            peak = equity_values[0]
            drawdowns = []

            for value in equity_values:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100 if peak > 0 else 0
                drawdowns.append(dd)

            plt.figure(figsize=(12, 6))
            plt.fill_between(range(len(drawdowns)), drawdowns, 0, color='red', alpha=0.3)
            plt.plot(drawdowns, color='red', linewidth=2)
            plt.title('Drawdown', fontsize=14, fontweight='bold')
            plt.xlabel('Time')
            plt.ylabel('Drawdown (%)')
            plt.grid(True, alpha=0.3)

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()

        except ImportError:
            self.logger.warning("matplotlib not installed, skipping plot")
        except Exception as e:
            self.logger.error(f"Error plotting drawdown: {e}")

    def compare_strategies(self, multiple_results: List[Dict]) -> pd.DataFrame:
        """
        Compare multiple strategy results

        Args:
            multiple_results: List of backtest results from different strategies

        Returns:
            DataFrame with comparison
        """
        comparison = []

        for result in multiple_results:
            comparison.append({
                'Strategy': result.get('strategy_name', 'Unknown'),
                'Total Trades': result['total_trades'],
                'Win Rate': f"{result['win_rate']:.2f}%",
                'Total P&L': f"₹{result['total_pnl']:,.2f}",
                'Return %': f"{result['total_return_pct']:.2f}%",
                'Sharpe': f"{result['sharpe_ratio']:.3f}",
                'Max DD': f"{result['max_drawdown']:.2f}%",
                'Profit Factor': f"{result['profit_factor']:.2f}"
            })

        return pd.DataFrame(comparison)

    def _calculate_rating(self, results: Dict) -> str:
        """Calculate overall strategy rating"""
        score = 0

        # Win rate (max 30 points)
        if results['win_rate'] >= 60:
            score += 30
        elif results['win_rate'] >= 50:
            score += 20
        elif results['win_rate'] >= 40:
            score += 10

        # Sharpe ratio (max 30 points)
        if results['sharpe_ratio'] >= 2.0:
            score += 30
        elif results['sharpe_ratio'] >= 1.5:
            score += 20
        elif results['sharpe_ratio'] >= 1.0:
            score += 10

        # Max drawdown (max 20 points)
        if results['max_drawdown'] < 10:
            score += 20
        elif results['max_drawdown'] < 20:
            score += 15
        elif results['max_drawdown'] < 30:
            score += 10

        # Profit factor (max 20 points)
        if results['profit_factor'] >= 2.0:
            score += 20
        elif results['profit_factor'] >= 1.5:
            score += 15
        elif results['profit_factor'] >= 1.2:
            score += 10

        # Rating
        if score >= 80:
            return "⭐⭐⭐⭐⭐ EXCELLENT (Ready for live)"
        elif score >= 60:
            return "⭐⭐⭐⭐ GOOD (Consider live with caution)"
        elif score >= 40:
            return "⭐⭐⭐ AVERAGE (Needs improvement)"
        elif score >= 20:
            return "⭐⭐ POOR (Not recommended)"
        else:
            return "⭐ VERY POOR (Do not use)"
