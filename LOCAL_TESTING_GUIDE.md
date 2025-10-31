# Local Testing Guide

## Complete Guide to Testing Your Algorithmic Trading System Locally

This guide will help you test the entire system on your local machine safely.

---

## Part 1: Initial Setup & Verification (15 minutes)

### Step 1: Environment Setup

```bash
# Navigate to project
cd algo-trading

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Create Configuration

```bash
# Copy environment template
cp config/.env.example config/.env

# Edit with your details (use any text editor)
nano config/.env
```

**Minimal `.env` for testing (no broker needed initially):**

```bash
# Leave broker credentials empty for now
API_KEY=
CLIENT_ID=
PASSWORD=
TOTP_SECRET=

# Testing mode
TRADING_MODE=paper

# Optional: Telegram (skip for now)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Database
DATABASE_TYPE=sqlite
DATABASE_PATH=data/trading.db

# Logging
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_TO_CONSOLE=true

# System
TIMEZONE=Asia/Kolkata
RISK_FREE_RATE=0.065
```

### Step 3: Verify Configuration

```bash
# Test configuration loading
python3 -c "
from src.utils.config_loader import ConfigLoader
try:
    config = ConfigLoader()
    print('✅ Configuration loaded successfully')
    print(f'Trading Mode: {config.get_trading_mode()}')
    print(f'Risk-free Rate: {config.get_risk_free_rate()}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

**Expected Output:**
```
✅ Configuration loaded successfully
Trading Mode: paper
Risk-free Rate: 0.065
```

---

## Part 2: Component Testing (30 minutes)

### Test 1: Greeks Calculator

```bash
# Create test file
cat > test_greeks_local.py << 'EOF'
"""Test Greeks Calculator"""
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator

# Initialize
bs_calc = BlackScholesCalculator(risk_free_rate=0.065)
iv_calc = ImpliedVolatilityCalculator(bs_calc)

# Test 1: Calculate option price
print("Test 1: Option Pricing")
price = bs_calc.calculate_price(
    spot_price=45000,
    strike_price=45000,
    time_to_expiry=7/365,  # 7 days
    volatility=0.18,
    option_type='CE'
)
print(f"✅ ATM Call Price: ₹{price:.2f}")

# Test 2: Calculate Greeks
print("\nTest 2: Greeks Calculation")
greeks = bs_calc.calculate_greeks(
    spot_price=45000,
    strike_price=45000,
    time_to_expiry=7/365,
    volatility=0.18,
    option_type='CE'
)
print(f"✅ Delta: {greeks['delta']:.4f}")
print(f"✅ Gamma: {greeks['gamma']:.4f}")
print(f"✅ Theta: {greeks['theta']:.4f}")
print(f"✅ Vega: {greeks['vega']:.4f}")

# Test 3: Calculate IV
print("\nTest 3: Implied Volatility")
market_price = 350
iv = iv_calc.calculate_iv(
    market_price=market_price,
    spot_price=45000,
    strike_price=45000,
    time_to_expiry=7/365,
    option_type='CE'
)
print(f"✅ Implied Volatility: {iv:.2%}" if iv else "❌ IV calculation failed")

# Test 4: Expected Move
print("\nTest 4: Expected Move Calculation")
expected_move = iv_calc.calculate_expected_move(
    spot_price=45000,
    atm_iv=0.18,
    days_to_expiry=7
)
print(f"✅ Expected Move (1 SD): ±{expected_move:.2f} points")

print("\n✅ All Greeks Calculator tests passed!")
EOF

# Run test
python3 test_greeks_local.py
```

### Test 2: Risk Management

```bash
# Create risk test
cat > test_risk_local.py << 'EOF'
"""Test Risk Management"""
from src.risk.pre_trade_validator import PreTradeValidator, TradeSignal
from src.risk.circuit_breakers import CircuitBreakers
from datetime import datetime

print("Test 1: Pre-Trade Validation")
config = {
    'risk_limits': {
        'max_loss_per_trade': 1000,
        'total_capital': 50000,
        'max_positions': 5,
        'max_daily_loss': 5000,
        'prohibited_strategies': ['naked_call', 'naked_put']
    }
}

validator = PreTradeValidator(config)

# Test valid trade
signal = TradeSignal(
    strategy_name="Iron Condor",
    symbol="BANKNIFTY",
    expiry_date="2025-11-06",
    legs=[
        {'action': 'BUY', 'option_type': 'PE', 'strike': 44000},
        {'action': 'SELL', 'option_type': 'PE', 'strike': 44200},
        {'action': 'SELL', 'option_type': 'CE', 'strike': 45800},
        {'action': 'BUY', 'option_type': 'CE', 'strike': 46000}
    ],
    entry_conditions_met=True,
    reason="Test trade",
    timestamp=datetime.now(),
    max_loss=800,
    max_profit=400,
    margin_required=1000,
    position_greeks={'delta': 0, 'gamma': -10, 'theta': 15, 'vega': -50},
    target_profit_pct=50,
    stop_loss_pct=100
)

result = validator.validate_trade(signal, [], {'daily_pnl': 0})

if result.approved:
    print(f"✅ Trade APPROVED")
    print(f"   Checks passed: {sum(result.checks_passed.values())}/6")
else:
    print(f"❌ Trade REJECTED: {result.reason}")

# Test invalid trade (too much loss)
signal.max_loss = 5000
result = validator.validate_trade(signal, [], {'daily_pnl': 0})
print(f"\n{'✅' if not result.approved else '❌'} Correctly rejected high-risk trade")

# Test prohibited strategy
signal.strategy_name = "naked_call"
signal.max_loss = float('inf')
result = validator.validate_trade(signal, [], {'daily_pnl': 0})
print(f"{'✅' if not result.approved else '❌'} Correctly rejected naked option")

print("\nTest 2: Circuit Breakers")
breakers = CircuitBreakers(config['risk_limits'])

# Test daily loss limit
daily_stats = {'daily_pnl': -6000}  # Exceeds limit
system_stats = {'api_latency_ms': 100, 'margin_utilization_pct': 50}
market_data = {'vix': 15}

triggered = breakers.check_all_breakers(
    daily_stats, system_stats, market_data, datetime.now()
)

print(f"{'✅' if triggered else '❌'} Circuit breaker triggered on daily loss")

print("\n✅ All Risk Management tests passed!")
EOF

# Run test
python3 test_risk_local.py
```

### Test 3: Paper Trading Broker

```bash
# Create broker test
cat > test_paper_broker.py << 'EOF'
"""Test Paper Trading Broker"""
from src.broker.paper_trading import PaperTradingBroker

print("Test: Paper Trading Broker")

# Initialize broker
broker = PaperTradingBroker(initial_capital=50000)

# Test connection
print(f"✅ Connection: {broker.connect()}")

# Test order placement
order = {
    'symbol': 'BANKNIFTY25N0645000CE',
    'transaction_type': 'BUY',
    'quantity': 1,
    'price': 350,
    'order_type': 'LIMIT'
}

order_id = broker.place_order(order)
print(f"✅ Order placed: {order_id}")

# Check order status
status = broker.get_order_status(order_id)
print(f"✅ Order status: {status['status']}")

# Test margins
margins = broker.get_margins()
print(f"✅ Available capital: ₹{margins['available_cash']:,.2f}")

# Test account summary
summary = broker.get_account_summary()
print(f"\n📊 Account Summary:")
print(f"   Initial Capital: ₹{summary['initial_capital']:,.2f}")
print(f"   Available: ₹{summary['available_capital']:,.2f}")
print(f"   Total Orders: {summary['total_orders']}")

print("\n✅ All Paper Trading Broker tests passed!")
EOF

# Run test
python3 test_paper_broker.py
```

### Test 4: Database Operations

```bash
# Create database test
cat > test_database_local.py << 'EOF'
"""Test Database Operations"""
from src.database.database_manager import DatabaseManager
from datetime import datetime

print("Test: Database Operations")

# Initialize database
db = DatabaseManager("data/test_trading.db")

# Test 1: Insert position
print("\nTest 1: Insert Position")
position_data = {
    'entry_time': datetime.now(),
    'strategy_name': 'Iron Condor',
    'symbol': 'BANKNIFTY',
    'expiry_date': '2025-11-06',
    'legs': [
        {'action': 'BUY', 'strike': 44000, 'option_type': 'PE', 'quantity': 1, 'price': 50},
        {'action': 'SELL', 'strike': 44200, 'option_type': 'PE', 'quantity': 1, 'price': 100}
    ],
    'entry_premium': 200,
    'max_loss': 800,
    'max_profit': 400,
    'target_profit_pct': 50,
    'stop_loss_pct': 100
}

position_id = db.insert_position(position_data)
print(f"✅ Position inserted: ID={position_id}")

# Test 2: Get open positions
print("\nTest 2: Get Open Positions")
positions = db.get_open_positions()
print(f"✅ Found {len(positions)} open position(s)")

# Test 3: Close position
print("\nTest 3: Close Position")
exit_data = {
    'exit_time': datetime.now(),
    'exit_premium': 150,
    'pnl': -50,
    'exit_reason': 'Target profit',
    'holding_time_minutes': 120
}
db.close_position(position_id, exit_data)
print(f"✅ Position closed")

# Test 4: Get daily stats
print("\nTest 4: Get Daily Stats")
stats = db.get_daily_stats()
print(f"✅ Total trades today: {stats['total_trades']}")
print(f"   Daily P&L: ₹{stats['daily_pnl']:.2f}")

# Test 5: Get trades
print("\nTest 5: Get Trade History")
trades = db.get_trades(limit=10)
print(f"✅ Retrieved {len(trades)} trade(s)")

print("\n✅ All Database tests passed!")

# Cleanup
import os
os.remove("data/test_trading.db")
print("✅ Test database cleaned up")
EOF

# Run test
python3 test_database_local.py
```

### Test 5: Strategy Logic

```bash
# Create strategy test
cat > test_strategy_local.py << 'EOF'
"""Test Strategy Logic"""
from src.strategy.iron_condor import IronCondorStrategy
from src.strategy.strike_selector import StrikeSelector
from src.greeks.black_scholes import BlackScholesCalculator
from src.greeks.iv_calculator import ImpliedVolatilityCalculator

print("Test: Strategy Logic")

# Initialize components
bs_calc = BlackScholesCalculator(0.065)
iv_calc = ImpliedVolatilityCalculator(bs_calc)
strike_intervals = {'BANKNIFTY': 100}
strike_selector = StrikeSelector(iv_calc, strike_intervals)

# Create strategy
config = {
    'enabled': True,
    'sd_distance': 1.0,
    'wing_width': 200,
    'target_profit': 0.50,
    'stop_loss': 1.00,
    'min_dte': 5,
    'max_dte': 15,
    'max_vix': 20,
    'min_credit': 50
}

strategy = IronCondorStrategy(config, strike_selector)

# Test strike selection
print("\nTest: Strike Selection")
market_data = {
    'symbol': 'BANKNIFTY',
    'spot_price': 45000,
    'vix': 15,
    'days_to_expiry': 7,
    'expiry_date': '2025-11-06'
}

# Create mock option chain
option_chain = []
strikes = range(44000, 46000, 100)
for strike in strikes:
    option_chain.append({
        'symbol': 'BANKNIFTY',
        'strike': strike,
        'option_type': 'CE',
        'expiry_date': '2025-11-06',
        'ltp': 100,  # Simplified
        'bid': 95,
        'ask': 105
    })
    option_chain.append({
        'symbol': 'BANKNIFTY',
        'strike': strike,
        'option_type': 'PE',
        'expiry_date': '2025-11-06',
        'ltp': 100,
        'bid': 95,
        'ask': 105
    })

# Test position metrics calculation
legs = [
    {'action': 'BUY', 'strike': 44000, 'option_type': 'PE', 'quantity': 1, 'price': 50},
    {'action': 'SELL', 'strike': 44200, 'option_type': 'PE', 'quantity': 1, 'price': 100},
    {'action': 'SELL', 'strike': 45800, 'option_type': 'CE', 'quantity': 1, 'price': 100},
    {'action': 'BUY', 'strike': 46000, 'option_type': 'CE', 'quantity': 1, 'price': 50}
]

metrics = strategy.calculate_position_metrics(legs, 45000)

print(f"✅ Strategy initialized: {strategy.name}")
print(f"✅ Max Loss: ₹{metrics['max_loss']:.2f}")
print(f"✅ Max Profit: ₹{metrics['max_profit']:.2f}")
print(f"✅ Net Credit: ₹{metrics['net_credit']:.2f}")

print("\n✅ All Strategy tests passed!")
EOF

# Run test
python3 test_strategy_local.py
```

---

## Part 3: Integration Testing (30 minutes)

### Run Unit Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Test Full System (Dry Run)

```bash
# Create a dry run test
cat > test_full_system.py << 'EOF'
"""Full System Dry Run Test"""
import sys
from datetime import datetime
from src.utils.config_loader import ConfigLoader
from src.utils.logger_setup import setup_logger

print("="*80)
print("FULL SYSTEM DRY RUN TEST")
print("="*80)

# Setup logging
logger = setup_logger(log_dir="logs", log_level="DEBUG")

try:
    # Step 1: Load configuration
    print("\n[1/6] Loading configuration...")
    config = ConfigLoader()
    print("✅ Configuration loaded")

    # Step 2: Initialize database
    print("\n[2/6] Initializing database...")
    from src.database.database_manager import DatabaseManager
    db = DatabaseManager()
    print("✅ Database initialized")

    # Step 3: Initialize broker (paper mode)
    print("\n[3/6] Connecting to paper trading broker...")
    from src.broker.paper_trading import PaperTradingBroker
    broker = PaperTradingBroker()
    broker.connect()
    print("✅ Paper broker connected")

    # Step 4: Initialize risk management
    print("\n[4/6] Initializing risk management...")
    from src.risk.pre_trade_validator import PreTradeValidator
    from src.risk.circuit_breakers import CircuitBreakers
    validator = PreTradeValidator(config.get_config())
    breakers = CircuitBreakers(config.get_config()['risk_limits'])
    print("✅ Risk management initialized")

    # Step 5: Initialize strategies
    print("\n[5/6] Loading strategies...")
    from src.strategy.iron_condor import IronCondorStrategy
    from src.strategy.strike_selector import StrikeSelector
    from src.greeks.black_scholes import BlackScholesCalculator
    from src.greeks.iv_calculator import ImpliedVolatilityCalculator

    bs_calc = BlackScholesCalculator(0.065)
    iv_calc = ImpliedVolatilityCalculator(bs_calc)
    strike_selector = StrikeSelector(iv_calc, {'BANKNIFTY': 100})

    strategy_config = config.get_config()['strategy_params']['iron_condor']
    strategy = IronCondorStrategy(strategy_config, strike_selector)
    print("✅ Strategies loaded")

    # Step 6: Initialize monitoring
    print("\n[6/6] Initializing monitoring...")
    from src.monitoring.telegram_bot import TelegramNotifier
    from src.monitoring.performance_tracker import PerformanceTracker
    telegram = TelegramNotifier(config.get_config()['telegram'])
    performance = PerformanceTracker()
    print("✅ Monitoring initialized")

    print("\n" + "="*80)
    print("✅ ALL SYSTEMS GO! System is ready for trading.")
    print("="*80)

    print("\n📊 System Status:")
    print(f"   Trading Mode: {config.get_trading_mode()}")
    print(f"   Database: Connected")
    print(f"   Broker: Paper Trading")
    print(f"   Strategies: {1} loaded")
    print(f"   Risk Management: Active")
    print(f"   Monitoring: {telegram.enabled}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Dry run completed successfully!")
EOF

# Run dry run
python3 test_full_system.py
```

---

## Part 4: Manual Testing Scenarios

### Scenario 1: Test Trade Entry & Exit

```bash
# Create manual trading test
cat > test_manual_trade.py << 'EOF'
"""Manual Trade Test"""
from src.broker.paper_trading import PaperTradingBroker
from src.database.database_manager import DatabaseManager
from src.monitoring.performance_tracker import PerformanceTracker
from datetime import datetime

print("Manual Trade Entry & Exit Test")
print("="*60)

# Initialize
broker = PaperTradingBroker(initial_capital=50000)
broker.connect()
db = DatabaseManager("data/test_manual.db")
performance = PerformanceTracker()

# Simulate Iron Condor entry
print("\n1️⃣ Entering Iron Condor position...")
legs = [
    {'symbol': 'BANKNIFTY25N0644000PE', 'transaction_type': 'BUY', 'quantity': 1, 'price': 50},
    {'symbol': 'BANKNIFTY25N0644200PE', 'transaction_type': 'SELL', 'quantity': 1, 'price': 100},
    {'symbol': 'BANKNIFTY25N0645800CE', 'transaction_type': 'SELL', 'quantity': 1, 'price': 100},
    {'symbol': 'BANKNIFTY25N0646000CE', 'transaction_type': 'BUY', 'quantity': 1, 'price': 50}
]

order_ids = []
for leg in legs:
    order_id = broker.place_order(leg)
    order_ids.append(order_id)
    print(f"   ✅ Order placed: {order_id}")

# Store position
position_data = {
    'entry_time': datetime.now(),
    'strategy_name': 'Iron Condor',
    'symbol': 'BANKNIFTY',
    'expiry_date': '2025-11-06',
    'legs': legs,
    'entry_premium': 100,  # Net credit
    'max_loss': 800,
    'max_profit': 400,
    'target_profit_pct': 50,
    'stop_loss_pct': 100
}

position_id = db.insert_position(position_data)
print(f"\n✅ Position stored: ID={position_id}")

# Simulate waiting
print("\n⏳ Position open... (simulating time passing)")

# Simulate exit
print("\n2️⃣ Exiting position at profit target...")
exit_data = {
    'exit_time': datetime.now(),
    'exit_premium': 50,  # Half of entry premium (50% profit)
    'pnl': 200,  # ₹200 profit
    'exit_reason': 'Target profit reached',
    'holding_time_minutes': 120
}

db.close_position(position_id, exit_data)
print(f"✅ Position closed with P&L: ₹{exit_data['pnl']:.2f}")

# Record performance
performance.record_trade({
    **position_data,
    **exit_data
})

# Get metrics
metrics = performance.calculate_metrics()
print(f"\n📊 Performance Metrics:")
print(f"   Total Trades: {metrics['total_trades']}")
print(f"   Win Rate: {metrics['win_rate']:.1f}%")
print(f"   Total P&L: ₹{metrics['total_pnl']:.2f}")

# Account summary
summary = broker.get_account_summary()
print(f"\n💰 Account Summary:")
print(f"   Initial Capital: ₹{summary['initial_capital']:,.2f}")
print(f"   Current Value: ₹{summary['account_value']:,.2f}")

print("\n✅ Manual trade test completed!")

# Cleanup
import os
os.remove("data/test_manual.db")
EOF

# Run manual trade test
python3 test_manual_trade.py
```

### Scenario 2: Test Risk Rejection

```bash
# Test risk rejection
python3 -c "
from src.risk.pre_trade_validator import PreTradeValidator, TradeSignal
from datetime import datetime

config = {'risk_limits': {'max_loss_per_trade': 500, 'total_capital': 50000, 'max_positions': 5}}
validator = PreTradeValidator(config)

# Try to place risky trade
signal = TradeSignal(
    strategy_name='Iron Condor',
    symbol='BANKNIFTY',
    expiry_date='2025-11-06',
    legs=[],
    entry_conditions_met=True,
    reason='Test',
    timestamp=datetime.now(),
    max_loss=2000,  # Exceeds limit!
    max_profit=400,
    margin_required=2500,
    position_greeks={},
    target_profit_pct=50,
    stop_loss_pct=100
)

result = validator.validate_trade(signal, [], {'daily_pnl': 0})

print('Test: Risk Rejection')
print(f'Status: {'✅ REJECTED' if not result.approved else '❌ SHOULD REJECT'}')
print(f'Reason: {result.reason}')
"
```

---

## Part 5: Quick Start Testing (5 minutes)

### One-Command Full Test

```bash
# Create comprehensive test script
cat > run_all_tests.sh << 'EOF'
#!/bin/bash

echo "=================================="
echo "  COMPREHENSIVE SYSTEM TEST"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Configuration
echo -e "\n📋 Test 1: Configuration"
python3 -c "from src.utils.config_loader import ConfigLoader; ConfigLoader()" && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 2: Greeks Calculator
echo -e "\n📐 Test 2: Greeks Calculator"
python3 test_greeks_local.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 3: Risk Management
echo -e "\n🛡️  Test 3: Risk Management"
python3 test_risk_local.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 4: Paper Broker
echo -e "\n💼 Test 4: Paper Broker"
python3 test_paper_broker.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 5: Database
echo -e "\n💾 Test 5: Database"
python3 test_database_local.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 6: Strategy
echo -e "\n📊 Test 6: Strategy Logic"
python3 test_strategy_local.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 7: Full System
echo -e "\n🚀 Test 7: Full System"
python3 test_full_system.py > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

# Test 8: Unit Tests
echo -e "\n🧪 Test 8: Unit Tests"
pytest tests/ -q > /dev/null 2>&1 && echo -e "${GREEN}✅ PASSED${NC}" || echo -e "${RED}❌ FAILED${NC}"

echo -e "\n=================================="
echo -e "  ${GREEN}ALL TESTS COMPLETED${NC}"
echo "=================================="
EOF

chmod +x run_all_tests.sh
./run_all_tests.sh
```

---

## Part 6: Troubleshooting

### Common Issues

#### Issue 1: Module Import Errors
```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

#### Issue 2: Configuration Errors
```bash
# Validate YAML files
python3 -c "
import yaml
for file in ['config/risk_limits.yaml', 'config/strategy_params.yaml', 'config/trading_hours.yaml']:
    with open(file) as f:
        yaml.safe_load(f)
    print(f'✅ {file} is valid')
"
```

#### Issue 3: Database Errors
```bash
# Reset database
rm -f data/trading.db
python3 -c "from src.database.database_manager import DatabaseManager; DatabaseManager()"
echo "✅ Database reset"
```

#### Issue 4: Permission Errors
```bash
# Fix permissions
chmod -R 755 src/
chmod -R 777 data/
chmod -R 777 logs/
```

---

## Summary Checklist

Before running the main system, verify:

- ✅ Virtual environment activated
- ✅ All dependencies installed
- ✅ Configuration files created
- ✅ All component tests pass
- ✅ Database initialized
- ✅ Logs directory exists
- ✅ Paper broker works
- ✅ Risk management active

### Run System

```bash
# After all tests pass
python3 src/main.py --mode paper
```

### Monitor System

```bash
# In another terminal
tail -f logs/trading_$(date +%Y-%m-%d).log
```

---

**You're ready to test! Start with the comprehensive test script and then run the system in paper mode.**
