# Contributing to Algorithmic Options Trading System

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Virtual environment tool (venv)
- Git

### Setup Instructions

1. Clone the repository
```bash
git clone <repository-url>
cd algo-trading
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment
```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

5. Run tests
```bash
pytest
```

## Project Structure

The codebase follows a modular architecture:

```
src/
├── broker/          # Broker API integration
├── data/            # Market data collection
├── greeks/          # Options pricing and Greeks
├── risk/            # Risk management (MOST CRITICAL)
├── strategy/        # Trading strategies
├── execution/       # Order execution
├── position/        # Position management
├── monitoring/      # Alerts and logging
└── database/        # Data storage
```

## Development Guidelines

### Safety First

This system trades real money. **Safety is paramount.**

1. **Never bypass risk checks**
2. **Always test in paper mode first**
3. **Validate all calculations**
4. **Handle errors gracefully**
5. **Log everything**

### Code Standards

- **Type hints**: Use type hints for all functions
- **Documentation**: Document all public methods
- **Testing**: Write tests for new features
- **Logging**: Use appropriate log levels
- **Error handling**: Handle all exceptions

### Adding a New Strategy

1. Inherit from `BaseStrategy`
2. Implement required abstract methods:
   - `generate_entry_signal()`
   - `check_exit_conditions()`
   - `calculate_position_metrics()`

3. Add configuration to `config/strategy_params.yaml`
4. Write unit tests
5. Test in paper mode extensively
6. Document strategy logic

Example:
```python
from src.strategy.base_strategy import BaseStrategy, StrategySignal

class MyStrategy(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__(config, name="my_strategy")

    def generate_entry_signal(self, market_data, option_chain, current_positions):
        # Implementation
        pass
```

### Risk Management Rules

**NON-NEGOTIABLE**:
- Every trade must have defined maximum loss
- No naked option selling
- All short options must have protective hedges
- Max loss must be validated before execution

### Testing Requirements

- **Unit tests**: Test individual components
- **Integration tests**: Test component interactions
- **Paper trading**: Minimum 6 months before live
- **Backtesting**: Validate on historical data

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_risk.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Configuration Changes

- Never hardcode parameters
- Add to appropriate YAML file
- Validate on startup
- Document in README

### Adding Dependencies

1. Add to `requirements.txt`
2. Document why it's needed
3. Verify license compatibility
4. Test installation

### Commit Guidelines

Use semantic commit messages:

```
feat: Add bull call spread strategy
fix: Correct Delta calculation for deep ITM options
docs: Update configuration guide
test: Add tests for circuit breakers
refactor: Simplify strike selection logic
```

### Pull Request Process

1. Create feature branch
2. Make changes with tests
3. Ensure all tests pass
4. Update documentation
5. Submit PR with description
6. Address review comments

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling present
- [ ] Logging appropriate
- [ ] Risk validation included
- [ ] Paper trading tested

## Safety Checklist for New Features

Before merging any code:

- [ ] Cannot cause infinite loss
- [ ] Validates maximum loss
- [ ] Handles API failures
- [ ] Logs all decisions
- [ ] Has emergency stop capability
- [ ] Tested in paper mode
- [ ] Reviewed by another developer

## Common Development Tasks

### Running Paper Trading
```bash
python src/main.py --mode paper
```

### Running Tests
```bash
pytest -v
```

### Checking Code Quality
```bash
flake8 src/
pylint src/
black src/ --check
mypy src/
```

### Generating Documentation
```bash
# Add your documentation generation commands
```

## Troubleshooting

### API Connection Issues
- Check credentials in `.env`
- Verify API key is active
- Check network connectivity
- Review logs in `logs/` directory

### Configuration Errors
- Validate YAML syntax
- Check parameter ranges
- Review validation errors in logs

### Database Issues
- Verify database path exists
- Check file permissions
- Review database logs

## Resources

- [Requirements Document](docs/REQUIREMENTS.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Strategy Guide](docs/STRATEGIES.md)

## Getting Help

- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas
- Email: [your-email]

## License

[Your License]

---

**Remember**: This system trades real money. Always prioritize safety over features.
