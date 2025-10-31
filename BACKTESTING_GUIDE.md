# Backtesting Guide

## Comprehensive Guide to Backtesting Your Trading Strategies

This guide explains how to backtest your strategies using historical data.

---

## What is Backtesting?

**Backtesting** = Testing your trading strategies on historical data to see how they would have performed in the past.

### Benefits:
- ✅ Test strategies without risking real money
- ✅ Identify profitable strategies before paper trading
- ✅ Optimize parameters for better performance
- ✅ Understand drawdowns and risk metrics
- ✅ Build confidence in your strategies

### Limitations:
- ⚠️ Past performance ≠ future results
- ⚠️ Historical data may not include all market conditions
- ⚠️ Execution assumptions may differ from reality
- ⚠️ Survivorship bias in data
- ⚠️ Look-ahead bias risk

---

## Part 1: Quick Start (15 minutes)

### Option 1: Use Sample Data (Easiest)

```bash
# Navigate to examples directory
cd algo-trading/examples

# Run basic backtest with sample data
python run_backtest.py
```

This will:
- Generate sample price data
- Run Iron Condor strategy
- Show comprehensive results
- Export trades to CSV
- Generate equity curve charts

### Option 2: Use Your Own CSV Data

```bash
# Prepare your CSV file with columns:
# timestamp, open, high, low, close, volume

# Place file in: data/historical_banknifty.csv

# Run backtest
python run_backtest_from_csv.py
```

### Option 3: Use Angel One Historical Data

```bash
# Ensure Angel One credentials configured
# Run backtest with real historical data
python angel_one_backtest.py
```

---

## Part 2: Understanding the Output

### Sample Output:

```
================================================================================
BACKTEST RESULTS REPORT
================================================================================

📊 TRADING SUMMARY
--------------------------------------------------------------------------------
Total Trades:        45
Winning Trades:      28
Losing Trades:       17
Win Rate:            62.22%

💰 PROFIT & LOSS
--------------------------------------------------------------------------------
Initial Capital:     ₹50,000.00
Final Capital:       ₹57,800.00
Total P&L:           ₹7,800.00
Total Return:        15.60%
Average Win:         ₹450.00
Average Loss:        ₹280.00

📉 RISK METRICS
--------------------------------------------------------------------------------
Profit Factor:       2.05
Sharpe Ratio:        1.456
Max Drawdown:        12.50%

⏱️  TRADE STATISTICS
--------------------------------------------------------------------------------
Avg Holding Time:    127 minutes

================================================================================
OVERALL RATING: ⭐⭐⭐⭐ GOOD (Consider live with caution)
================================================================================
```

### Key Metrics Explained:

1. **Win Rate**: Percentage of profitable trades
   - Target: > 50%
   - Good: > 60%

2. **Total Return**: Overall profit/loss percentage
   - Good: > 10% per month
   - Excellent: > 20% per month

3. **Sharpe Ratio**: Risk-adjusted return
   - > 1.0: Good
   - > 1.5: Very good
   - > 2.0: Excellent

4. **Max Drawdown**: Largest peak-to-trough decline
   - Target: < 30%
   - Good: < 20%
   - Excellent: < 10%

5. **Profit Factor**: Gross profit / Gross loss
   - > 1.5: Good
   - > 2.0: Excellent

---

## Part 3: Fetching Historical Data from Angel One

### Method 1: Fetch Spot Price Data

```python
from src.broker.angel_one import AngelOneBroker
from src.backtesting.historical_data import HistoricalDataFetcher
from datetime import datetime, timedelta

# Connect to Angel One
credentials = {
    'api_key': 'YOUR_API_KEY',
    'client_id': 'YOUR_CLIENT_ID',
    'password': 'YOUR_PASSWORD'
}

broker = AngelOneBroker(credentials)
broker.connect()

# Initialize data fetcher
data_fetcher = HistoricalDataFetcher(broker.smartApi)

# Fetch historical candles
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

historical_data = data_fetcher.fetch_historical_candles(
    symbol='BANKNIFTY',
    from_date=start_date,
    to_date=end_date,
    interval='5MINUTE'  # Options: 1MINUTE, 5MINUTE, 15MINUTE, 1HOUR, 1DAY
)

# Save for later use
historical_data.to_csv('data/banknifty_historical.csv', index=False)

print(f"Fetched {len(historical_data)} candles")
broker.logout()
```

### Method 2: Store Real-Time Data for Backtesting

```python
# While paper trading is running, store data
from src.backtesting.historical_data import HistoricalDataFetcher

data_fetcher = HistoricalDataFetcher()

# During trading, collect option chain snapshots
option_chain_data = []  # Collect throughout the day

# At EOD, save
data_fetcher.save_realtime_data_for_backtest(
    data=option_chain_data,
    filepath='data/option_chain_2025-11-06.csv'
)
```

### Method 3: Use NSE Website Data

```python
# Fetch from NSE (alternative source)
data_fetcher = HistoricalDataFetcher()

option_chain = data_fetcher.fetch_nse_option_chain(
    symbol='BANKNIFTY',
    expiry_date='2025-11-06'
)
```

### Method 4: Paid Data Providers

Consider these for extensive historical options data:
- **Historical Options Data**: opstra.com, optionistics.com
- **NSE Historical**: Archives available on NSE website
- **Paid APIs**: AlgoTest, TrueData, QuantInsti

---

## Part 4: Running Custom Backtests

### Backtest Single Strategy

```python
from src.backtesting.backtest_engine import BacktestEngine
from src.strategy.iron_condor import IronCondorStrategy

# Initialize strategy
strategy = IronCondorStrategy(config, strike_selector)

# Create backtest
backtest = BacktestEngine(
    config=config,
    strategies=[strategy],  # Single strategy
    historical_data_fetcher=data_fetcher
)

# Run
results = backtest.run_backtest(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 3, 31),
    symbol='BANKNIFTY'
)
```

### Backtest Multiple Strategies

```python
# Load multiple strategies
from src.strategy.iron_condor import IronCondorStrategy
from src.strategy.vertical_spreads import BullCallSpread

strategies = [
    IronCondorStrategy(config['iron_condor'], strike_selector),
    BullCallSpread(config['bull_call_spread'], strike_selector)
]

# Run backtest
backtest = BacktestEngine(config, strategies, data_fetcher)
results = backtest.run_backtest(start_date, end_date, 'BANKNIFTY')
```

### Parameter Optimization

```python
# Test different parameters
results_list = []

for sd_distance in [0.8, 1.0, 1.2, 1.5]:
    for wing_width in [150, 200, 250]:

        # Update config
        config['iron_condor']['sd_distance'] = sd_distance
        config['iron_condor']['wing_width'] = wing_width

        # Run backtest
        strategy = IronCondorStrategy(config['iron_condor'], strike_selector)
        backtest = BacktestEngine(config, [strategy], data_fetcher)
        results = backtest.run_backtest(start_date, end_date, 'BANKNIFTY')

        results['parameters'] = {
            'sd_distance': sd_distance,
            'wing_width': wing_width
        }

        results_list.append(results)

# Find best parameters
best = max(results_list, key=lambda x: x['sharpe_ratio'])
print(f"Best parameters: {best['parameters']}")
print(f"Sharpe Ratio: {best['sharpe_ratio']:.3f}")
```

---

## Part 5: Analyzing Results

### Generate Detailed Report

```python
from src.backtesting.backtest_analyzer import BacktestAnalyzer

analyzer = BacktestAnalyzer()

# Text report
report = analyzer.generate_report(results)
print(report)

# Trade log
trade_log = analyzer.generate_trade_log(results)
print(trade_log)

# Export to CSV
analyzer.export_to_csv(results, 'data/backtest_results.csv')

# Plot equity curve
analyzer.plot_equity_curve(results, 'data/equity_curve.png')

# Plot drawdown
analyzer.plot_drawdown(results, 'data/drawdown.png')
```

### Compare Multiple Strategies

```python
# Run backtests for different strategies
results_iron_condor = backtest_iron_condor()
results_bull_call = backtest_bull_call()
results_bear_put = backtest_bear_put()

# Compare
comparison = analyzer.compare_strategies([
    results_iron_condor,
    results_bull_call,
    results_bear_put
])

print(comparison)
```

---

## Part 6: Best Practices

### 1. Use Sufficient Data
- ✅ Minimum: 3 months of data
- ✅ Better: 6 months
- ✅ Best: 1 year or more

### 2. Test Multiple Market Conditions
- ✅ Trending markets (up and down)
- ✅ Range-bound markets
- ✅ High volatility periods
- ✅ Low volatility periods

### 3. Walk-Forward Testing
```python
# Test on rolling windows
for i in range(0, 12, 3):  # 3-month windows
    start = base_date + timedelta(days=i*30)
    end = start + timedelta(days=90)

    results = backtest.run_backtest(start, end, 'BANKNIFTY')
    print(f"Period {i}: Sharpe = {results['sharpe_ratio']:.3f}")
```

### 4. Out-of-Sample Testing
```python
# Train on first 70% of data
# Test on last 30% of data

train_end = start_date + timedelta(days=int((end_date - start_date).days * 0.7))

# Train
train_results = backtest.run_backtest(start_date, train_end, 'BANKNIFTY')

# Optimize parameters based on train results
# ...

# Test on unseen data
test_results = backtest.run_backtest(train_end, end_date, 'BANKNIFTY')
```

### 5. Reality Checks
- ⚠️ Include transaction costs
- ⚠️ Account for slippage
- ⚠️ Consider liquidity constraints
- ⚠️ Model execution delays

---

## Part 7: Common Pitfalls

### ❌ Overfitting
**Problem**: Parameters work perfectly on historical data but fail in live trading

**Solution**:
- Use simple strategies
- Test on out-of-sample data
- Avoid too many parameters

### ❌ Look-Ahead Bias
**Problem**: Using future information in past decisions

**Solution**:
- Only use data available at decision time
- Be careful with data alignment

### ❌ Survivorship Bias
**Problem**: Only testing on successful instruments

**Solution**:
- Include delisted/failed instruments
- Use complete dataset

### ❌ Ignoring Market Impact
**Problem**: Assuming perfect execution

**Solution**:
- Model slippage
- Consider bid-ask spreads
- Account for liquidity

---

## Part 8: Integration with Angel One

### Full Integration Example

```python
"""
Complete Angel One Integration for Backtesting
"""

from src.broker.angel_one import AngelOneBroker
from src.backtesting.historical_data import HistoricalDataFetcher
from src.backtesting.backtest_engine import BacktestEngine
from datetime import datetime, timedelta

# Step 1: Connect and fetch data
broker = AngelOneBroker(credentials)
broker.connect()

data_fetcher = HistoricalDataFetcher(broker.smartApi)

# Step 2: Fetch multiple symbols
symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
all_data = {}

for symbol in symbols:
    data = data_fetcher.fetch_historical_candles(
        symbol=symbol,
        from_date=datetime.now() - timedelta(days=90),
        to_date=datetime.now(),
        interval='5MINUTE'
    )
    all_data[symbol] = data
    data.to_csv(f'data/{symbol}_historical.csv', index=False)

# Step 3: Run backtests
for symbol, data in all_data.items():
    print(f"\nBacktesting {symbol}...")

    backtest = BacktestEngine(config, strategies, data_fetcher)
    results = backtest.run_backtest(
        start_date=data['timestamp'].min(),
        end_date=data['timestamp'].max(),
        symbol=symbol
    )

    analyzer = BacktestAnalyzer()
    print(analyzer.generate_report(results))

broker.logout()
```

---

## Part 9: Next Steps After Backtesting

### If Results are EXCELLENT (⭐⭐⭐⭐⭐):
1. ✅ Run longer backtests (6+ months)
2. ✅ Test on different market conditions
3. ✅ Proceed to paper trading
4. ✅ Monitor paper trading for 6 months

### If Results are GOOD (⭐⭐⭐⭐):
1. ✅ Optimize parameters
2. ✅ Test on more data
3. ✅ Consider paper trading with small size

### If Results are AVERAGE (⭐⭐⭐):
1. ⚠️ Improve strategy
2. ⚠️ Optimize parameters
3. ⚠️ Do NOT proceed to paper trading yet

### If Results are POOR (⭐⭐ or ⭐):
1. ❌ Do NOT use this strategy
2. ❌ Completely redesign approach
3. ❌ Test different strategies

---

## Summary

**Backtesting Steps**:
1. ✅ Fetch historical data (Angel One or CSV)
2. ✅ Run backtest with your strategy
3. ✅ Analyze results (Sharpe, drawdown, win rate)
4. ✅ Optimize parameters if needed
5. ✅ Test on out-of-sample data
6. ✅ If excellent, proceed to paper trading

**Remember**:
- Past performance ≠ future results
- Always paper trade before live
- Monitor metrics continuously
- Be skeptical of perfect results

---

**Ready to backtest? Start with the examples!**

```bash
cd examples
python run_backtest.py
```
