# Algorithmic Options Day Trading System

## Overview

A fully automated algorithmic day trading system for Indian options market (NSE - Nifty/Bank Nifty) with institutional-grade risk management.

### Key Features

- **Zero Infinite Loss Risk**: Only executes defined-risk strategies
- **Intraday Trading**: All positions closed by 3:20 PM daily
- **Advanced Risk Management**: Multi-layer validation, circuit breakers, portfolio Greeks monitoring
- **9 Trading Strategies**: Iron Condor, Bull/Bear Spreads, Straddles, Strangles, etc.
- **Real-time Greeks**: Black-Scholes-Merton model for accurate Greeks calculation
- **Smart Order Execution**: Progressive limit orders with liquidity validation
- **Comprehensive Monitoring**: Telegram alerts, email notifications, real-time dashboard
- **Paper Trading**: Robust simulation mode for strategy testing

## Architecture

```
Market Data Layer → Strategy Engine → Risk Management → Order Execution → Monitoring
                         ↓                    ↓                ↓
                   Greeks Calculator    Circuit Breakers   Position Manager
```

## Safety Features

### Non-Negotiable Rules
1. **Never Sell Naked Options**: All short options must have protective hedges
2. **Defined Risk Only**: Every trade has predetermined maximum loss
3. **Capital Protection**: Maximum loss limited to allocated capital
4. **Mandatory Square-off**: All positions closed by 3:20 PM

### Circuit Breakers
- Daily loss limit breach
- Consecutive losses threshold
- Extreme volatility (VIX > 40)
- Margin utilization alert
- System health monitoring

## Project Structure

```
algo-trading/
├── config/              # Configuration files
├── src/
│   ├── broker/          # Broker integration (Angel One)
│   ├── data/            # Market data collection
│   ├── greeks/          # Options pricing and Greeks
│   ├── risk/            # Risk management layer
│   ├── strategy/        # Trading strategies
│   ├── execution/       # Order execution
│   ├── position/        # Position management
│   ├── monitoring/      # Alerts and logging
│   └── database/        # Data storage
├── tests/               # Test suite
├── logs/                # Application logs
└── data/                # Database files
```

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd algo-trading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example configuration
cp config/.env.example config/.env

# Edit configuration files
nano config/.env              # Add API credentials
nano config/risk_limits.yaml  # Configure risk parameters
nano config/strategy_params.yaml  # Configure strategies
```

### 3. Paper Trading (Required)

```bash
# Run in paper trading mode (minimum 6 months recommended)
python src/main.py --mode paper
```

### 4. Live Trading (After Successful Paper Trading)

```bash
# Run in live trading mode
python src/main.py --mode live
```

## Configuration

### Risk Limits (`config/risk_limits.yaml`)

```yaml
max_loss_per_trade: 1000      # Maximum loss per position (₹)
max_daily_loss: 5000          # Daily loss circuit breaker (₹)
max_positions: 5              # Maximum concurrent positions
total_capital: 50000          # Total trading capital (₹)
risk_per_trade_pct: 2         # Risk percentage per trade
```

### Strategy Parameters (`config/strategy_params.yaml`)

```yaml
iron_condor:
  sd_distance: 1.0            # Standard deviation for strike selection
  wing_width: 200             # Protection wing width (points)
  target_profit: 0.50         # Target profit (50% of max)
  stop_loss: 1.00             # Stop loss (100% of credit)
  min_dte: 5                  # Minimum days to expiry
  max_dte: 15                 # Maximum days to expiry
```

### Trading Hours (`config/trading_hours.yaml`)

```yaml
market_open: "09:15"
trading_start: "09:20"        # Allow market to stabilize
trading_end: "15:00"          # No new positions after 3 PM
force_square_off: "15:20"     # Mandatory exit time
market_close: "15:30"
```

## Supported Strategies

### 1. Iron Condor
- **Type**: Credit spread (neutral)
- **Risk**: Defined (strike width - net credit)
- **Best For**: Low volatility, range-bound markets

### 2. Bull Call Spread
- **Type**: Debit spread (bullish)
- **Risk**: Defined (premium paid)
- **Best For**: Moderately bullish outlook

### 3. Bear Put Spread
- **Type**: Debit spread (bearish)
- **Risk**: Defined (premium paid)
- **Best For**: Moderately bearish outlook

### 4. Iron Butterfly
- **Type**: Credit spread (neutral)
- **Risk**: Defined (wing width - net credit)
- **Best For**: Very low volatility, tight range

### 5. Bull Put Spread
- **Type**: Credit spread (bullish)
- **Risk**: Defined (strike width - net credit)
- **Best For**: Support level defense

### 6. Bear Call Spread
- **Type**: Credit spread (bearish)
- **Risk**: Defined (strike width - net credit)
- **Best For**: Resistance level defense

### 7. Long Straddle
- **Type**: Debit spread (volatility)
- **Risk**: Defined (total premium paid)
- **Best For**: Major events, large expected moves

### 8. Long Strangle
- **Type**: Debit spread (volatility)
- **Risk**: Defined (total premium paid)
- **Best For**: Very large expected moves

### 9. Calendar Spread
- **Type**: Time spread
- **Risk**: Defined (net debit paid)
- **Best For**: Time decay harvesting

## Risk Management

### Pre-Trade Validation (6 Checks)
1. ✅ Defined risk verification
2. ✅ Maximum loss acceptability
3. ✅ Capital availability
4. ✅ Position limits
5. ✅ Daily loss limit
6. ✅ Strategy whitelist

### Position-Level Risk
- Per-position maximum loss
- Delta-based stops (0.40 danger, 0.50 critical)
- Time-based mandatory exit
- Greeks monitoring

### Portfolio-Level Risk
- Net Delta management (±50 tolerance)
- Net Gamma limits (|Gamma| < 100)
- Net Theta targets (positive preferred)
- Net Vega limits (|Vega| < 1000)

## Monitoring and Alerts

### Telegram Notifications
- Trade entry/exit confirmations
- Position adjustments
- Risk limit warnings
- Circuit breaker triggers
- Daily performance summary

### Dashboard (Real-time)
- Current positions with P&L
- Portfolio Greeks
- Daily statistics
- System health status

### Logging
- Structured logging with millisecond precision
- Daily log rotation
- Comprehensive audit trail
- All decisions logged with reasoning

## Performance Metrics

The system tracks:
- Win/Loss ratio
- Sharpe ratio
- Maximum drawdown
- Profit factor
- Average holding time
- Risk-adjusted returns

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test module
pytest tests/test_risk.py
```

## Emergency Procedures

### Kill Switch
```bash
# Emergency stop all trading
pkill -f "python src/main.py"
```

### Manual Square-off
```bash
# Force close all positions
python src/emergency_squareoff.py --confirm
```

## Requirements

- Python 3.8+
- Angel One trading account
- Indian bank account
- Minimum capital: ₹50,000 recommended
- VPS/Cloud server (for production)
- Mumbai region (low latency)

## Compliance

- SEBI algorithmic trading regulations compliant
- Complete audit trail maintained
- Risk management as per regulatory requirements
- Paper trading mandatory before live deployment

## Safety Warnings

⚠️ **IMPORTANT**
- This system trades real money in live mode
- Always start with paper trading (minimum 6 months)
- Verify all configurations before live trading
- Never disable safety mechanisms
- Monitor system during trading hours
- Maintain adequate capital buffer

⚠️ **PROHIBITED**
- Never sell naked options
- Never bypass risk validation
- Never trade without stop losses
- Never exceed capital limits
- Never leave positions overnight

## Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue]
- Documentation: [docs/](docs/)
- Email: [your-email]

## License

[Your License]

## Disclaimer

This software is for educational and research purposes. Trading derivatives involves substantial risk of loss. Past performance does not guarantee future results. The authors are not responsible for any financial losses incurred while using this system.

**USE AT YOUR OWN RISK**

---

**Version**: 1.0
**Last Updated**: 2025-10-30
**Status**: Development
