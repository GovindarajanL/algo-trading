# 90-Day Paper Trading Validation Guide

## Overview

Before going live with real money, you **MUST** complete a 90-day paper trading validation period. This ensures the system is stable, profitable, and ready for live trading.

## Validation Criteria

The system must meet **ALL** of the following criteria:

### 1. Trading Period ✓
- **Minimum**: 90 trading days
- **Status**: Calendar days may be longer due to weekends/holidays
- **Why**: Sufficient data to validate strategy performance

### 2. Trade Volume ✓
- **Minimum**: 50 trades
- **Status**: Must execute real strategy signals, not manual trades
- **Why**: Statistical significance requires adequate sample size

### 3. Performance Metrics ✓
| Metric | Minimum Required | Description |
|--------|------------------|-------------|
| Win Rate | 55% | Percentage of profitable trades |
| Profit Factor | 1.5 | Total Wins / Total Losses |
| Sharpe Ratio | 1.0 | Risk-adjusted returns |
| Max Drawdown | <20% | Maximum peak-to-trough decline |

### 4. Risk Management ✓
- **Max Consecutive Losses**: ≤ 10
- **Undefined Risk Trades**: 0 (ZERO tolerance)
- **Daily Loss Breaches**: ≤ 5

### 5. Consistency ✓
- **Profitable Months**: ≥ 60%
- **Why**: System should be profitable in majority of months

### 6. System Stability ✓
- **Critical Errors**: 0
- **Emergency Square-offs**: ≤ 2
- **Incomplete Trades**: 0
- **Why**: System must run reliably without crashes

## Running Validation

### Automatic Validation

```bash
# Run validation script
python scripts/validate_paper_trading.py

# Specify custom database path
python scripts/validate_paper_trading.py --db data/custom_trading.db
```

### Manual Validation

1. **Start Paper Trading**
   ```bash
   python src/main.py --mode paper
   ```

2. **Run for 90+ Days**
   - Let the system run continuously
   - Monitor daily via Telegram notifications
   - Check logs regularly for errors

3. **After 90 Days, Run Validation**
   ```bash
   python scripts/validate_paper_trading.py
   ```

4. **Review Results**
   - Check console output for pass/fail status
   - Review detailed JSON report in `data/validation_report_*.json`
   - Fix any failing criteria

## Validation Report

The validation script generates a comprehensive report:

```json
{
  "validation_date": "2025-11-05T10:30:00",
  "period_valid": true,
  "trades_valid": true,
  "performance_valid": true,
  "risk_valid": true,
  "consistency_valid": true,
  "stability_valid": true,
  "overall_passed": true
}
```

## What to Do if Validation Fails

### If Win Rate < 55%
- Review strategy parameters
- Check if market conditions changed
- Consider adjusting entry/exit rules

### If Profit Factor < 1.5
- Reduce stop losses
- Increase profit targets
- Filter low-quality signals

### If Max Drawdown > 20%
- Reduce position sizes
- Implement stricter risk limits
- Diversify strategies

### If Too Many Consecutive Losses
- Review circuit breaker settings
- Consider pausing trading after 5 losses
- Analyze losing trade patterns

### If System Errors
- Fix bugs immediately
- Review error logs
- Restart validation period if critical

## Best Practices

### During Paper Trading

1. **Treat it Like Real Money**
   - Follow all signals
   - Don't interfere manually
   - Let the system run autonomously

2. **Monitor Daily**
   - Check Telegram notifications
   - Review daily P&L
   - Watch for errors/warnings

3. **Keep Detailed Logs**
   - All trades logged automatically
   - Review logs weekly
   - Document any issues

4. **Test Edge Cases**
   - High volatility days (VIX > 30)
   - Expiry days
   - Market gaps/holidays

5. **Gradual Improvement**
   - Week 1-4: System stability
   - Week 5-8: Strategy refinement
   - Week 9-12: Final validation
   - Week 13+: Confidence building

### After Passing Validation

1. **Review Complete History**
   - Analyze all 90+ days of trades
   - Look for any patterns or issues
   - Ensure understanding of all trades

2. **Start Small in Live**
   - Begin with 10-20% of intended capital
   - Gradually scale up over 30 days
   - Monitor closely for any differences

3. **Continuous Monitoring**
   - Paper trading validates system
   - Live trading requires ongoing vigilance
   - Always have circuit breakers active

## Common Pitfalls to Avoid

❌ **Don't**:
- Manually interfere with paper trades
- Skip validation even if "it looks good"
- Start live trading before 90 days
- Ignore failing criteria
- Cherry-pick good periods

✅ **Do**:
- Let system run fully automated
- Complete full 90-day period
- Fix issues and restart if needed
- Document everything
- Be patient and thorough

## Validation Checklist

Before going live, ensure:

- [ ] Completed 90+ trading days
- [ ] 50+ trades executed
- [ ] All performance metrics met
- [ ] Zero undefined-risk trades
- [ ] System ran without crashes
- [ ] Logs reviewed and clean
- [ ] Validation report shows PASS
- [ ] Comfortable with system behavior
- [ ] Emergency procedures tested
- [ ] Live trading capital allocated

## Support

If validation fails repeatedly:
1. Review strategy logic
2. Check risk parameters
3. Analyze market conditions
4. Consider strategy changes
5. Extend paper trading period

## Remember

> **Paper Trading is NOT Optional**

Many traders skip this step and lose real money. The 90-day period:
- Validates the system works
- Builds your confidence
- Identifies edge cases
- Tests all market conditions
- Ensures system stability

**Take this seriously. Your capital depends on it.**

---

## Quick Reference

```bash
# Start paper trading
python src/main.py --mode paper

# Check status
tail -f logs/trading_YYYYMMDD.log

# Run validation
python scripts/validate_paper_trading.py

# View validation report
cat data/validation_report_*.json | jq .
```

For questions or issues, refer to the main README.md or system documentation.
