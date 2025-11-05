"""
90-Day Paper Trading Validation Framework
Tracks system performance and validates readiness for live trading
"""

import os
import sys
import json
from datetime import datetime, timedelta, date
from typing import Dict, List
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.database_manager import DatabaseManager
from src.utils.nse_calendar import NSECalendar


class PaperTradingValidator:
    """
    Validates paper trading performance over 90 days
    Ensures system is ready for live trading
    """

    def __init__(self, db_path: str = "data/trading.db"):
        """
        Initialize validator

        Args:
            db_path: Path to trading database
        """
        self.db = DatabaseManager({'database': {'type': 'sqlite', 'path': db_path}})
        self.calendar = NSECalendar()

        # Validation criteria
        self.criteria = {
            'min_days': 90,              # Minimum trading days
            'min_trades': 50,            # Minimum number of trades
            'min_win_rate': 0.55,        # Minimum 55% win rate
            'max_consecutive_losses': 10, # Maximum consecutive losses
            'min_sharpe_ratio': 1.0,     # Minimum Sharpe ratio
            'max_drawdown_pct': 20,      # Maximum drawdown %
            'min_profit_factor': 1.5,    # Minimum profit factor
            'max_daily_loss_breaches': 5, # Max daily loss limit breaches
        }

        self.validation_results = {}

    def run_validation(self) -> Dict:
        """
        Run complete validation
        REQ-VAL-001: 90-day validation

        Returns:
            Dictionary with validation results
        """
        print("="*80)
        print("90-DAY PAPER TRADING VALIDATION")
        print("="*80)

        # 1. Check trading period
        period_valid = self._validate_trading_period()

        # 2. Validate trade count
        trades_valid = self._validate_trade_count()

        # 3. Validate performance metrics
        performance_valid = self._validate_performance()

        # 4. Validate risk management
        risk_valid = self._validate_risk_management()

        # 5. Validate consistency
        consistency_valid = self._validate_consistency()

        # 6. Check system stability
        stability_valid = self._validate_system_stability()

        # Compile results
        self.validation_results = {
            'validation_date': datetime.now().isoformat(),
            'period_valid': period_valid,
            'trades_valid': trades_valid,
            'performance_valid': performance_valid,
            'risk_valid': risk_valid,
            'consistency_valid': consistency_valid,
            'stability_valid': stability_valid,
            'overall_passed': all([
                period_valid,
                trades_valid,
                performance_valid,
                risk_valid,
                consistency_valid,
                stability_valid
            ]),
            'criteria': self.criteria
        }

        # Generate report
        self._generate_report()

        return self.validation_results

    def _validate_trading_period(self) -> bool:
        """Validate trading period >= 90 days"""
        print("\n1. Validating Trading Period...")
        print("-" * 40)

        trades = self.db.get_trades_history(limit=10000)

        if not trades:
            print("❌ No trades found")
            return False

        # Get first and last trade dates
        trade_dates = [datetime.fromisoformat(t['entry_time']).date() for t in trades]
        first_trade = min(trade_dates)
        last_trade = max(trade_dates)

        # Calculate trading days
        trading_days = 0
        current_date = first_trade

        while current_date <= last_trade:
            if self.calendar.is_trading_day(current_date):
                trading_days += 1
            current_date += timedelta(days=1)

        period_days = (last_trade - first_trade).days

        print(f"First Trade: {first_trade}")
        print(f"Last Trade: {last_trade}")
        print(f"Total Days: {period_days}")
        print(f"Trading Days: {trading_days}")
        print(f"Required: {self.criteria['min_days']} trading days")

        if trading_days >= self.criteria['min_days']:
            print(f"✅ PASSED - {trading_days} trading days")
            return True
        else:
            print(f"❌ FAILED - Only {trading_days} trading days (need {self.criteria['min_days']})")
            return False

    def _validate_trade_count(self) -> bool:
        """Validate minimum number of trades"""
        print("\n2. Validating Trade Count...")
        print("-" * 40)

        trades = self.db.get_trades_history(limit=10000)
        trade_count = len(trades)

        print(f"Total Trades: {trade_count}")
        print(f"Required: {self.criteria['min_trades']}")

        if trade_count >= self.criteria['min_trades']:
            print(f"✅ PASSED - {trade_count} trades")
            return True
        else:
            print(f"❌ FAILED - Only {trade_count} trades (need {self.criteria['min_trades']})")
            return False

    def _validate_performance(self) -> bool:
        """Validate performance metrics"""
        print("\n3. Validating Performance Metrics...")
        print("-" * 40)

        trades = self.db.get_trades_history(limit=10000)

        if not trades:
            print("❌ No trades to analyze")
            return False

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('realized_pnl', 0) > 0)
        losing_trades = total_trades - winning_trades

        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0

        # Calculate P&L metrics
        pnls = [t.get('realized_pnl', 0) for t in trades]
        total_pnl = sum(pnls)

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        # Profit factor
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Sharpe ratio (simplified)
        if pnls:
            returns = pd.Series(pnls)
            sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0
        else:
            sharpe = 0

        # Maximum drawdown
        cumulative = pd.Series(pnls).cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_dd = drawdown.min()
        max_dd_pct = (max_dd / self.criteria.get('total_capital', 50000)) * 100 if max_dd < 0 else 0

        print(f"Win Rate: {win_rate:.2%}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Max Drawdown: ₹{max_dd:.2f} ({abs(max_dd_pct):.2f}%)")
        print(f"Total P&L: ₹{total_pnl:.2f}")

        # Check criteria
        checks = {
            'win_rate': win_rate >= self.criteria['min_win_rate'],
            'profit_factor': profit_factor >= self.criteria['min_profit_factor'],
            'sharpe_ratio': sharpe >= self.criteria['min_sharpe_ratio'],
            'max_drawdown': abs(max_dd_pct) <= self.criteria['max_drawdown_pct']
        }

        all_passed = all(checks.values())

        if all_passed:
            print("✅ PASSED - All performance metrics met")
        else:
            print("❌ FAILED - Some metrics below threshold:")
            for metric, passed in checks.items():
                if not passed:
                    print(f"   - {metric}: FAILED")

        return all_passed

    def _validate_risk_management(self) -> bool:
        """Validate risk management"""
        print("\n4. Validating Risk Management...")
        print("-" * 40)

        trades = self.db.get_trades_history(limit=10000)

        if not trades:
            return False

        # Check for consecutive losses
        max_consecutive = 0
        current_consecutive = 0

        for trade in trades:
            if trade.get('realized_pnl', 0) < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        print(f"Max Consecutive Losses: {max_consecutive}")
        print(f"Allowed: {self.criteria['max_consecutive_losses']}")

        # Check for undefined risk trades
        undefined_risk_trades = sum(
            1 for t in trades
            if t.get('max_loss', 0) == float('inf')
        )

        print(f"Undefined Risk Trades: {undefined_risk_trades}")

        # Check risk events
        risk_events = self.db.get_risk_events(limit=1000)
        daily_loss_breaches = sum(
            1 for e in risk_events
            if 'daily loss' in e.get('description', '').lower()
        )

        print(f"Daily Loss Breaches: {daily_loss_breaches}")

        checks = {
            'consecutive_losses': max_consecutive <= self.criteria['max_consecutive_losses'],
            'no_undefined_risk': undefined_risk_trades == 0,
            'daily_loss_breaches': daily_loss_breaches <= self.criteria['max_daily_loss_breaches']
        }

        all_passed = all(checks.values())

        if all_passed:
            print("✅ PASSED - Risk management criteria met")
        else:
            print("❌ FAILED - Risk management issues:")
            for metric, passed in checks.items():
                if not passed:
                    print(f"   - {metric}: FAILED")

        return all_passed

    def _validate_consistency(self) -> bool:
        """Validate consistency across months"""
        print("\n5. Validating Consistency...")
        print("-" * 40)

        trades = self.db.get_trades_history(limit=10000)

        if not trades:
            return False

        # Group by month
        monthly_pnl = {}

        for trade in trades:
            entry_time = datetime.fromisoformat(trade['entry_time'])
            month_key = entry_time.strftime('%Y-%m')

            if month_key not in monthly_pnl:
                monthly_pnl[month_key] = []

            monthly_pnl[month_key].append(trade.get('realized_pnl', 0))

        # Calculate monthly totals
        monthly_totals = {month: sum(pnls) for month, pnls in monthly_pnl.items()}

        print(f"Months Traded: {len(monthly_totals)}")

        for month, total in sorted(monthly_totals.items()):
            print(f"  {month}: ₹{total:.2f}")

        # Check for consistency (at least 60% of months profitable)
        profitable_months = sum(1 for total in monthly_totals.values() if total > 0)
        total_months = len(monthly_totals)

        consistency_rate = (profitable_months / total_months) if total_months > 0 else 0

        print(f"\nProfitable Months: {profitable_months}/{total_months} ({consistency_rate:.2%})")

        if consistency_rate >= 0.60:
            print("✅ PASSED - Consistent profitability")
            return True
        else:
            print("❌ FAILED - Inconsistent performance")
            return False

    def _validate_system_stability(self) -> bool:
        """Validate system stability (no crashes, errors)"""
        print("\n6. Validating System Stability...")
        print("-" * 40)

        # Check for system errors
        risk_events = self.db.get_risk_events(limit=1000)

        critical_errors = sum(
            1 for e in risk_events
            if e.get('severity', '').upper() == 'CRITICAL'
        )

        emergency_squareoffs = sum(
            1 for e in risk_events
            if 'emergency' in e.get('event_type', '').lower()
        )

        print(f"Critical Errors: {critical_errors}")
        print(f"Emergency Square-offs: {emergency_squareoffs}")

        # Check for data consistency
        trades = self.db.get_trades_history(limit=10000)
        incomplete_trades = sum(
            1 for t in trades
            if not t.get('exit_time') or not t.get('realized_pnl')
        )

        print(f"Incomplete Trades: {incomplete_trades}")

        checks = {
            'no_critical_errors': critical_errors == 0,
            'no_emergency_squareoffs': emergency_squareoffs <= 2,  # Allow max 2
            'no_incomplete_trades': incomplete_trades == 0
        }

        all_passed = all(checks.values())

        if all_passed:
            print("✅ PASSED - System stable")
        else:
            print("❌ FAILED - System stability issues")

        return all_passed

    def _generate_report(self):
        """Generate validation report"""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        overall = self.validation_results['overall_passed']

        if overall:
            print("\n🎉 ✅ VALIDATION PASSED - READY FOR LIVE TRADING")
        else:
            print("\n⚠️  ❌ VALIDATION FAILED - MORE PAPER TRADING NEEDED")

        print(f"\nValidation Date: {self.validation_results['validation_date']}")

        print("\nChecks:")
        for key, value in self.validation_results.items():
            if key.endswith('_valid'):
                status = "✅ PASS" if value else "❌ FAIL"
                print(f"  {key.replace('_valid', '').title()}: {status}")

        # Save report to file
        report_path = f"data/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)

        print(f"\nDetailed report saved to: {report_path}")


def main():
    """Main validation script"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate paper trading performance")
    parser.add_argument(
        '--db',
        default='data/trading.db',
        help='Path to trading database'
    )

    args = parser.parse_args()

    validator = PaperTradingValidator(args.db)
    results = validator.run_validation()

    # Exit with appropriate code
    sys.exit(0 if results['overall_passed'] else 1)


if __name__ == "__main__":
    main()
