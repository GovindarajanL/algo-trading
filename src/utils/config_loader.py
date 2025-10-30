"""
Configuration Loader
Loads and validates all configuration files
REQ-ARCH-012 to REQ-ARCH-016
"""

import os
import yaml
from typing import Dict
from dotenv import load_dotenv
import logging


class ConfigLoader:
    """
    Load and manage system configuration
    REQ-ARCH-012: All parameters externalized in configuration
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration loader

        Args:
            config_dir: Directory containing configuration files
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = config_dir

        # Load environment variables (REQ-ARCH-026, REQ-ARCH-027)
        env_file = os.path.join(config_dir, '.env')
        if os.path.exists(env_file):
            load_dotenv(env_file)
            self.logger.info(f"Loaded environment from {env_file}")
        else:
            self.logger.warning(f"No .env file found at {env_file}")

        # Load all configurations
        self.risk_limits = self._load_yaml('risk_limits.yaml')
        self.strategy_params = self._load_yaml('strategy_params.yaml')
        self.trading_hours = self._load_yaml('trading_hours.yaml')

        # Validate configurations (REQ-ARCH-013)
        self._validate_config()

        self.logger.info("Configuration loaded successfully")

    def _load_yaml(self, filename: str) -> Dict:
        """Load YAML configuration file"""
        filepath = os.path.join(self.config_dir, filename)

        try:
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)
                self.logger.debug(f"Loaded {filename}")
                return config or {}
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {filepath}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing {filename}: {e}")
            return {}

    def _validate_config(self):
        """
        Validate configuration values
        REQ-ARCH-013: Validate configuration on startup
        REQ-STRAT-027: Validate parameter ranges
        """
        errors = []

        # Validate risk limits
        if self.risk_limits.get('max_loss_per_trade', 0) <= 0:
            errors.append("max_loss_per_trade must be positive")

        if self.risk_limits.get('total_capital', 0) <= 0:
            errors.append("total_capital must be positive")

        if self.risk_limits.get('max_positions', 0) <= 0:
            errors.append("max_positions must be positive")

        # Validate percentages
        risk_pct = self.risk_limits.get('risk_per_trade_pct', 0)
        if not (0 < risk_pct <= 100):
            errors.append(f"risk_per_trade_pct must be 0-100, got {risk_pct}")

        # Validate strategy parameters
        for strategy, params in self.strategy_params.items():
            if isinstance(params, dict):
                # Check DTE ranges
                min_dte = params.get('min_dte', 0)
                max_dte = params.get('max_dte', 0)
                if min_dte > max_dte:
                    errors.append(f"{strategy}: min_dte > max_dte")

                # Check profit/loss percentages
                target = params.get('target_profit', 0)
                stop = params.get('stop_loss', 0)
                if target <= 0 or stop <= 0:
                    errors.append(f"{strategy}: invalid profit/loss targets")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info("✅ Configuration validation passed")

    def get_credentials(self) -> Dict:
        """
        Get API credentials from environment
        REQ-ARCH-028: Use environment variables for sensitive data
        """
        return {
            'api_key': os.getenv('API_KEY'),
            'client_id': os.getenv('CLIENT_ID'),
            'password': os.getenv('PASSWORD'),
            'totp_secret': os.getenv('TOTP_SECRET')
        }

    def get_trading_mode(self) -> str:
        """Get trading mode (paper/live)"""
        return os.getenv('TRADING_MODE', 'paper').lower()

    def get_telegram_config(self) -> Dict:
        """Get Telegram bot configuration"""
        return {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID')
        }

    def get_database_config(self) -> Dict:
        """Get database configuration"""
        return {
            'type': os.getenv('DATABASE_TYPE', 'sqlite'),
            'path': os.getenv('DATABASE_PATH', 'data/trading.db')
        }

    def get_risk_free_rate(self) -> float:
        """Get risk-free rate for Greeks calculation"""
        return float(os.getenv('RISK_FREE_RATE', '0.065'))

    def get_config(self) -> Dict:
        """
        Get complete configuration
        REQ-ARCH-015: Environment-specific configurations
        """
        return {
            'risk_limits': self.risk_limits,
            'strategy_params': self.strategy_params,
            'trading_hours': self.trading_hours,
            'trading_mode': self.get_trading_mode(),
            'credentials': self.get_credentials(),
            'telegram': self.get_telegram_config(),
            'database': self.get_database_config(),
            'risk_free_rate': self.get_risk_free_rate()
        }
