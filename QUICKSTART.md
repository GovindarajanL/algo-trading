## Quick Start Guide

**Algorithmic Options Day Trading System**

### Prerequisites

- Python 3.8 or higher
- Angel One trading account (for live trading)
- Basic understanding of options trading
- Linux/Mac/Windows system

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone <repository-url>
cd algo-trading

# 2. Create virtual environment
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create configuration from template
cp config/.env.example config/.env
```

### Configuration (5 minutes)

Edit `config/.env`:

```bash
# Angel One Credentials
API_KEY=your_api_key_here
CLIENT_ID=your_client_id_here
PASSWORD=your_password_here

# Start with PAPER mode
TRADING_MODE=paper

# Telegram Alerts (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

Edit `config/risk_limits.yaml`:

```yaml
total_capital: 50000         # Your trading capital
max_loss_per_trade: 1000     # Maximum loss per trade
max_daily_loss: 5000         # Daily stop loss
```

### Run Paper Trading (Recommended: 6+ months)

```bash
# Start paper trading
python src/main.py --mode paper
```

**What happens:**
- System connects in simulation mode
- No real money is used
- All trades are simulated
- You get complete system testing

### Monitor Your System

Watch the logs:
```bash
tail -f logs/trading_$(date +%Y-%m-%d).log
```

Key things to monitor:
- ✅ Trade entries and exits
- ✅ Risk validations
- ✅ Circuit breaker status
- ✅ Daily P&L
- ✅ System health

### Telegram Notifications

If configured, you'll receive:
- 📈 Trade entry alerts
- 📉 Trade exit alerts with P&L
- ⚠️ Risk limit warnings
- 🚨 Circuit breaker triggers
- 📊 Daily summary

### Emergency Controls

**Stop System:**
```bash
# Press Ctrl+C in terminal
# Or
pkill -f "python src/main.py"
```

**Emergency Close All Positions:**
```bash
python src/emergency_squareoff.py --mode paper
```

### System Features

#### ✅ Safety Features Active

1. **No Naked Options**: System CANNOT sell naked calls or puts
2. **Defined Risk Only**: Every trade has maximum loss before execution
3. **Multi-Layer Validation**: 6 checks before each trade
4. **Circuit Breakers**: Automatic halts on risk limits
5. **Force Square-Off**: All positions closed by 3:20 PM
6. **Daily Loss Limits**: Trading stops at daily loss limit

#### 📊 Implemented Strategies

1. **Iron Condor** - Neutral, low volatility
2. **Bull Call Spread** - Moderately bullish
3. **Bear Put Spread** - Moderately bearish
4. **Bull Put Spread** - Credit spread, bullish
5. **Bear Call Spread** - Credit spread, bearish
6. **Long Straddle** - High volatility, event-driven
7. **Long Strangle** - Very high volatility
8. **Iron Butterfly** - Very low volatility

#### 🎯 Risk Management

- **Position Sizing**: Automatic based on capital
- **Greeks Monitoring**: Delta, Gamma, Theta, Vega tracked
- **Portfolio Limits**: Max positions, max loss enforced
- **Delta-Based Stops**: Exit at Delta 0.50 (critical)
- **Time-Based Stops**: Mandatory exit by 3:20 PM

### Typical Day Timeline

```
08:55 - System startup
09:00 - Pre-market checks
09:15 - Market opens
09:20 - Trading begins (after stabilization)
       ... Monitor positions ...
       ... Check for entry signals ...
15:00 - No new positions allowed
15:20 - Force square-off time
15:30 - Market closes
15:35 - Daily summary sent
```

### Performance Tracking

View performance:
```bash
# Check database
sqlite3 data/trading.db
SELECT * FROM daily_summary;
```

Metrics tracked:
- Total trades
- Win/Loss ratio
- Sharpe ratio
- Maximum drawdown
- Profit factor
- Average holding time

### Configuration Files

**Risk Limits** (`config/risk_limits.yaml`):
- Capital allocation
- Position limits
- Greek limits
- Circuit breaker thresholds

**Strategy Parameters** (`config/strategy_params.yaml`):
- Strategy-specific settings
- Entry/exit criteria
- Strike selection parameters

**Trading Hours** (`config/trading_hours.yaml`):
- Market timings
- Trading windows
- Expiry schedules

### Testing Your Setup

Run tests:
```bash
pytest tests/ -v
```

Check configuration:
```bash
python -c "from src.utils.config_loader import ConfigLoader; c=ConfigLoader(); print('✅ Config OK')"
```

### Common Issues

**Issue**: Cannot connect to broker
- **Fix**: Check API credentials in `.env`
- Verify internet connection
- Check Angel One service status

**Issue**: Configuration errors
- **Fix**: Validate YAML syntax
- Ensure all required fields present
- Check parameter ranges

**Issue**: Import errors
- **Fix**: Activate virtual environment
- Reinstall requirements: `pip install -r requirements.txt`

### Going Live (After 6+ Months Paper Trading)

⚠️ **WARNING**: Only proceed if:
- ✅ 6+ months successful paper trading
- ✅ Consistent profitability
- ✅ Sharpe ratio > 1.0
- ✅ Win rate > 50%
- ✅ Zero system failures
- ✅ You understand all risks

```bash
# 1. Update .env
TRADING_MODE=live

# 2. Verify configuration
# Double-check ALL settings

# 3. Start with safety confirmation
python src/main.py --mode live
# You'll be prompted for confirmation
```

### System Architecture

```
Main Engine
    ├── Broker Integration (Angel One / Paper)
    ├── Market Data Layer (Real-time data)
    ├── Risk Management
    │   ├── Pre-Trade Validator
    │   ├── Circuit Breakers
    │   ├── Portfolio Risk Manager
    │   └── Position Risk Manager
    ├── Strategy Engine
    │   ├── Iron Condor
    │   ├── Vertical Spreads
    │   └── Volatility Strategies
    ├── Order Execution
    │   ├── Smart Order Manager
    │   └── Liquidity Validator
    ├── Position Management
    │   └── Delta Monitoring
    ├── Monitoring & Alerts
    │   ├── Telegram Bot
    │   └── Performance Tracker
    └── Database
        ├── Trades
        ├── Positions
        └── Daily Summary
```

### Key Commands

```bash
# Start paper trading
python src/main.py --mode paper

# Start live trading (after paper success)
python src/main.py --mode live

# Emergency square-off
python src/emergency_squareoff.py --mode paper

# Run tests
pytest tests/ -v

# Check logs
tail -f logs/trading_$(date +%Y-%m-%d).log

# View database
sqlite3 data/trading.db
```

### Support and Resources

- **Documentation**: See `README.md`, `CONTRIBUTING.md`, `DEPLOYMENT.md`
- **Configuration**: See `config/` directory
- **Examples**: See `tests/` directory
- **Issues**: GitHub Issues

### Safety Reminders

1. **Start with Paper Trading**: Minimum 6 months
2. **Never Bypass Safety**: All checks are critical
3. **Monitor Actively**: Check system during market hours
4. **Respect Limits**: Don't modify risk limits casually
5. **Emergency Ready**: Know how to stop system
6. **Capital Protection**: Only risk money you can afford to lose

### Next Steps

1. ✅ Complete installation
2. ✅ Configure settings
3. ✅ Start paper trading
4. ✅ Monitor for 6+ months
5. ✅ Analyze performance
6. ✅ Only then consider live trading

### Success Criteria for Paper Trading

Before going live, achieve:
- ✅ **Win Rate**: > 50%
- ✅ **Sharpe Ratio**: > 1.0
- ✅ **Max Drawdown**: < 30%
- ✅ **System Uptime**: > 99%
- ✅ **No Crashes**: Zero failures
- ✅ **Consistent Profit**: 6 months positive

---

**Remember**: This system trades in derivatives. Options can lose 100% of premium. Never trade with money you cannot afford to lose. Past performance does not guarantee future results.

**Good Luck and Trade Safely! 📈**
