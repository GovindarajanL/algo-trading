"""
Telegram Bot for Alerts and Notifications
REQ-MON-007 to REQ-MON-014
"""

from typing import Dict, Optional
import logging
from datetime import datetime


class TelegramNotifier:
    """
    Send notifications via Telegram
    REQ-MON-007 to REQ-MON-013: Comprehensive alerting
    """

    def __init__(self, config: Dict):
        """
        Initialize Telegram notifier

        Args:
            config: Telegram configuration with bot_token and chat_id
        """
        self.logger = logging.getLogger(__name__)
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.enabled = bool(self.bot_token and self.chat_id)
        self.bot = None

        if self.enabled:
            try:
                # Try to import telegram library
                import telegram
                self.bot = telegram.Bot(token=self.bot_token)
                self.logger.info("✅ Telegram notifier initialized")
            except ImportError:
                self.logger.warning(
                    "python-telegram-bot not installed. "
                    "Install with: pip install python-telegram-bot"
                )
                self.enabled = False
            except Exception as e:
                self.logger.error(f"Telegram initialization error: {e}")
                self.enabled = False
        else:
            self.logger.warning("Telegram not configured (disabled)")

    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send message to Telegram

        Args:
            message: Message text
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_sync(self, message: str) -> bool:
        """
        Send message synchronously (without async)

        Args:
            message: Message text

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            import requests

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, data=data, timeout=5)

            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"Telegram API error: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False

    def notify_trade_entry(self, signal: Dict) -> bool:
        """
        Notify trade entry
        REQ-MON-007: Alert on trade entry
        """
        message = (
            f"📈 <b>TRADE ENTRY</b>\n\n"
            f"Strategy: {signal.get('strategy_name')}\n"
            f"Symbol: {signal.get('symbol')}\n"
            f"Expiry: {signal.get('expiry_date')}\n"
            f"Max Loss: ₹{signal.get('max_loss', 0):.2f}\n"
            f"Max Profit: ₹{signal.get('max_profit', 0):.2f}\n"
            f"Legs: {len(signal.get('legs', []))}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_trade_exit(self, position: Dict, reason: str, pnl: float) -> bool:
        """
        Notify trade exit
        REQ-MON-008: Alert on trade exit
        """
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        message = (
            f"{pnl_emoji} <b>TRADE EXIT</b>\n\n"
            f"Strategy: {position.get('strategy_name')}\n"
            f"Symbol: {position.get('symbol')}\n"
            f"P&L: ₹{pnl:.2f}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_position_adjustment(self, position: Dict, adjustment: str) -> bool:
        """
        Notify position adjustment
        REQ-MON-009: Alert on position adjustment
        """
        message = (
            f"🔧 <b>POSITION ADJUSTMENT</b>\n\n"
            f"Strategy: {position.get('strategy_name')}\n"
            f"Symbol: {position.get('symbol')}\n"
            f"Adjustment: {adjustment}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_risk_limit_breach(self, breach_type: str, details: str) -> bool:
        """
        Notify risk limit breach
        REQ-MON-010: Alert on risk limit breach
        """
        message = (
            f"⚠️ <b>RISK LIMIT BREACH</b>\n\n"
            f"Type: {breach_type}\n"
            f"Details: {details}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_circuit_breaker(self, breaker_type: str, reason: str) -> bool:
        """
        Notify circuit breaker trigger
        REQ-MON-011: Alert on circuit breaker trigger
        """
        message = (
            f"🚨 <b>CIRCUIT BREAKER TRIGGERED</b>\n\n"
            f"Type: {breaker_type}\n"
            f"Reason: {reason}\n"
            f"Action: Trading halted\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_system_error(self, error_type: str, error_message: str) -> bool:
        """
        Notify system error
        REQ-MON-012: Alert on system errors
        """
        message = (
            f"❌ <b>SYSTEM ERROR</b>\n\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_daily_summary(self, summary: Dict) -> bool:
        """
        Send daily summary
        REQ-MON-013: Daily summary at market close
        """
        pnl = summary.get('daily_pnl', 0)
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        message = (
            f"{pnl_emoji} <b>DAILY SUMMARY</b>\n\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"Total Trades: {summary.get('total_trades', 0)}\n"
            f"Winning Trades: {summary.get('winning_trades', 0)}\n"
            f"Losing Trades: {summary.get('losing_trades', 0)}\n"
            f"Win Rate: {summary.get('win_rate', 0):.1f}%\n"
            f"Daily P&L: ₹{pnl:.2f}\n"
            f"Max Drawdown: ₹{summary.get('max_drawdown', 0):.2f}\n"
            f"Circuit Breakers: {summary.get('circuit_breakers', 0)}\n"
            f"\nTime: {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_sync(message)

    def notify_startup(self, mode: str) -> bool:
        """Notify system startup"""
        message = (
            f"🚀 <b>SYSTEM STARTUP</b>\n\n"
            f"Mode: {mode.upper()}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Status: Ready"
        )
        return self.send_sync(message)

    def notify_shutdown(self, reason: str = "Normal shutdown") -> bool:
        """Notify system shutdown"""
        message = (
            f"⏹️ <b>SYSTEM SHUTDOWN</b>\n\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return self.send_sync(message)
