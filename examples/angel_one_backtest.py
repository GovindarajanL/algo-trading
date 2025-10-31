"""
Example: Backtest with Angel One Historical Data
Shows how to integrate with Angel One API for historical data
"""

import sys
sys.path.append('..')

from datetime import datetime, timedelta
from src.broker.angel_one import AngelOneBroker
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.historical_data import HistoricalDataFetcher
from src.backtesting.backtest_analyzer import BacktestAnalyzer
from src.strategy.iron_condor import IronCondorStrategy
from src.strategy.strike_selector import StrikeSelector
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator
from src.utils.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger
import pandas as pd

def main():
    """Run backtest with Angel One data"""

    print("="*80)
    print("ANGEL ONE HISTORICAL DATA BACKTESTING")
    print("="*80)

    # Setup
    logger = setup_logger(log_dir="../logs", log_level="INFO")
    config = ConfigLoader(config_dir="../config")

    # Connect to Angel One
    print("\n🔌 Connecting to Angel One...")
    credentials = config.get_credentials()

    if not all(credentials.values()):
        print("❌ Error: Angel One credentials not configured")
        print("   Please set API_KEY, CLIENT_ID, and PASSWORD in config/.env")
        return

    broker = AngelOneBroker(credentials)

    if not broker.connect():
        print("❌ Failed to connect to Angel One")
        print("   Falling back to sample data...")
        broker = None
    else:
        print("✅ Connected to Angel One")

    # Initialize components
    print("\n📐 Initializing components...")
    bs_calc = BlackScholesCalculator(config.get_risk_free_rate())
    iv_calc = ImpliedVolatilityCalculator(bs_calc)
    strike_selector = StrikeSelector(iv_calc, {'BANKNIFTY': 100, 'NIFTY': 50})

    # Load strategies
    strategy_config = config.get_config()['strategy_params']['iron_condor']
    strategies = [IronCondorStrategy(strategy_config, strike_selector)]

    # Initialize data fetcher with Angel One API
    data_fetcher = HistoricalDataFetcher(broker.smartApi if broker else None)

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months

    print(f"\n📅 Fetching historical data: {start_date.date()} to {end_date.date()}")

    # Fetch historical candles
    print("   Fetching BANKNIFTY candles...")
    historical_data = data_fetcher.fetch_historical_candles(
        symbol='BANKNIFTY',
        from_date=start_date,
        end_date=end_date,
        interval='5MINUTE'
    )

    if historical_data.empty:
        print("   ⚠️  No data from API, using sample data")
    else:
        print(f"   ✅ Loaded {len(historical_data)} candles")

        # Save for future use
        historical_data.to_csv('../data/historical_banknifty.csv', index=False)
        print("   💾 Saved to ../data/historical_banknifty.csv")

    # Initialize backtest engine
    print("\n🚀 Running backtest...")
    backtest = BacktestEngine(
        config=config.get_config(),
        strategies=strategies,
        historical_data_fetcher=data_fetcher
    )

    # Run backtest
    results = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        symbol='BANKNIFTY'
    )

    # Analyze results
    print("\n📊 Analyzing results...")
    analyzer = BacktestAnalyzer()

    report = analyzer.generate_report(results)
    print("\n" + report)

    trade_log = analyzer.generate_trade_log(results)
    print(trade_log)

    # Export
    analyzer.export_to_csv(results, '../data/angel_one_backtest_results.csv')

    # Plots
    try:
        analyzer.plot_equity_curve(results, '../data/angel_one_equity_curve.png')
        analyzer.plot_drawdown(results, '../data/angel_one_drawdown.png')
        print("\n✅ Charts saved to ../data/")
    except Exception as e:
        print(f"\n⚠️  Plotting error: {e}")

    # Disconnect
    if broker:
        broker.logout()
        print("\n👋 Disconnected from Angel One")

    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
