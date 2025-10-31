"""
Example: Run Backtesting
Complete example of backtesting strategies
"""

import sys
sys.path.append('..')

from datetime import datetime, timedelta
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.historical_data import HistoricalDataFetcher
from src.backtesting.backtest_analyzer import BacktestAnalyzer
from src.strategy.iron_condor import IronCondorStrategy
from src.strategy.strike_selector import StrikeSelector
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator
from src.utils.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger

def main():
    """Run backtest example"""

    # Setup
    print("="*80)
    print("BACKTESTING EXAMPLE")
    print("="*80)

    # Initialize logging
    logger = setup_logger(log_dir="../logs", log_level="INFO")

    # Load configuration
    print("\n📋 Loading configuration...")
    config = ConfigLoader(config_dir="../config")

    # Initialize Greeks calculator
    print("📐 Initializing Greeks calculator...")
    bs_calc = BlackScholesCalculator(config.get_risk_free_rate())
    iv_calc = ImpliedVolatilityCalculator(bs_calc)

    # Initialize strike selector
    strike_intervals = {'BANKNIFTY': 100, 'NIFTY': 50}
    strike_selector = StrikeSelector(iv_calc, strike_intervals)

    # Initialize strategies
    print("📊 Loading strategies...")
    strategy_config = config.get_config()['strategy_params']['iron_condor']
    strategies = [
        IronCondorStrategy(strategy_config, strike_selector)
    ]

    # Initialize data fetcher
    print("💾 Initializing data fetcher...")
    # Option 1: Use Angel One API (if available)
    # broker = AngelOneBroker(config.get_credentials())
    # broker.connect()
    # data_fetcher = HistoricalDataFetcher(broker.smartApi)

    # Option 2: Use sample data (for demonstration)
    data_fetcher = HistoricalDataFetcher()  # Will generate sample data

    # Initialize backtest engine
    print("🚀 Initializing backtest engine...")
    backtest = BacktestEngine(
        config=config.get_config(),
        strategies=strategies,
        historical_data_fetcher=data_fetcher
    )

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 1 month backtest

    print(f"\n⏱️  Backtest period: {start_date.date()} to {end_date.date()}")
    print("   This will take a few moments...\n")

    # Run backtest
    results = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        symbol='BANKNIFTY'
    )

    if not results:
        print("❌ Backtest failed - no results generated")
        return

    # Analyze results
    print("\n📊 Analyzing results...")
    analyzer = BacktestAnalyzer()

    # Generate report
    report = analyzer.generate_report(results)
    print("\n" + report)

    # Generate trade log
    trade_log = analyzer.generate_trade_log(results)
    print("\n" + trade_log)

    # Export results
    print("\n💾 Exporting results...")
    analyzer.export_to_csv(results, '../data/backtest_results.csv')
    print("   ✅ Results saved to ../data/backtest_results.csv")

    # Plot equity curve (if matplotlib available)
    try:
        print("\n📈 Generating plots...")
        analyzer.plot_equity_curve(results, '../data/equity_curve.png')
        analyzer.plot_drawdown(results, '../data/drawdown.png')
        print("   ✅ Plots saved to ../data/")
    except Exception as e:
        print(f"   ⚠️  Plotting skipped: {e}")

    # Final verdict
    print("\n" + "="*80)
    if results['sharpe_ratio'] > 1.0 and results['win_rate'] > 50:
        print("✅ VERDICT: Strategy shows promise for paper trading")
    elif results['sharpe_ratio'] > 0.5:
        print("⚠️  VERDICT: Strategy needs optimization")
    else:
        print("❌ VERDICT: Strategy not recommended")
    print("="*80)

    print("\n💡 Next Steps:")
    print("   1. Review the detailed trade log above")
    print("   2. Analyze the equity curve and drawdown charts")
    print("   3. Try different strategy parameters")
    print("   4. Run longer backtests (3-6 months)")
    print("   5. If results are good, proceed to paper trading")


if __name__ == "__main__":
    main()
