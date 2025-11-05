"""
NSE Holiday Calendar and Expiry Date Calculator
Handles NSE trading holidays and weekly expiry calculations
REQ-COMP-015: Handle market holidays
"""

from datetime import datetime, timedelta, date
from typing import List, Optional
import logging


class NSECalendar:
    """
    NSE Holiday Calendar and Expiry Calculator
    Manages trading holidays and expiry date calculations
    """

    def __init__(self):
        """Initialize NSE Calendar"""
        self.logger = logging.getLogger(__name__)

        # NSE Holidays for 2024-2025 (Update annually)
        # Source: https://www.nseindia.com/resources/exchange-communication-holidays
        self.holidays_2024 = [
            date(2024, 1, 26),   # Republic Day
            date(2024, 3, 8),    # Mahashivratri
            date(2024, 3, 25),   # Holi
            date(2024, 3, 29),   # Good Friday
            date(2024, 4, 11),   # Id-Ul-Fitr
            date(2024, 4, 17),   # Ram Navami
            date(2024, 4, 21),   # Mahavir Jayanti
            date(2024, 5, 1),    # Maharashtra Day
            date(2024, 6, 17),   # Bakri Id
            date(2024, 7, 17),   # Muharram
            date(2024, 8, 15),   # Independence Day
            date(2024, 9, 16),   # Milad-un-Nabi
            date(2024, 10, 2),   # Mahatma Gandhi Jayanti
            date(2024, 10, 12),  # Dussehra
            date(2024, 11, 1),   # Diwali Laxmi Pujan
            date(2024, 11, 15),  # Gurunanak Jayanti
            date(2024, 12, 25),  # Christmas
        ]

        self.holidays_2025 = [
            date(2025, 1, 26),   # Republic Day
            date(2025, 2, 26),   # Mahashivratri
            date(2025, 3, 14),   # Holi
            date(2025, 3, 31),   # Id-Ul-Fitr
            date(2025, 4, 6),    # Ram Navami
            date(2025, 4, 10),   # Mahavir Jayanti
            date(2025, 4, 18),   # Good Friday
            date(2025, 5, 1),    # Maharashtra Day
            date(2025, 6, 7),    # Bakri Id
            date(2025, 7, 6),    # Muharram
            date(2025, 8, 15),   # Independence Day
            date(2025, 9, 5),    # Milad-un-Nabi
            date(2025, 10, 2),   # Mahatma Gandhi Jayanti
            date(2025, 10, 2),   # Dussehra
            date(2025, 10, 20),  # Diwali Laxmi Pujan
            date(2025, 11, 5),   # Gurunanak Jayanti
            date(2025, 12, 25),  # Christmas
        ]

        # Combine all holidays
        self.all_holidays = set(self.holidays_2024 + self.holidays_2025)

        self.logger.info(f"NSE Calendar initialized with {len(self.all_holidays)} holidays")

    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if a given date is a trading day
        REQ-COMP-015: Validate trading days

        Args:
            check_date: Date to check

        Returns:
            True if trading day, False otherwise
        """
        # Check if weekend (Saturday=5, Sunday=6)
        if check_date.weekday() >= 5:
            return False

        # Check if holiday
        if check_date in self.all_holidays:
            return False

        return True

    def get_next_trading_day(self, from_date: Optional[date] = None) -> date:
        """
        Get next trading day from given date
        REQ-COMP-015: Calculate next trading day

        Args:
            from_date: Starting date (default: today)

        Returns:
            Next trading day
        """
        if from_date is None:
            from_date = date.today()

        next_day = from_date + timedelta(days=1)

        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)

        return next_day

    def get_previous_trading_day(self, from_date: Optional[date] = None) -> date:
        """
        Get previous trading day from given date

        Args:
            from_date: Starting date (default: today)

        Returns:
            Previous trading day
        """
        if from_date is None:
            from_date = date.today()

        prev_day = from_date - timedelta(days=1)

        while not self.is_trading_day(prev_day):
            prev_day -= timedelta(days=1)

        return prev_day

    def get_weekly_expiry(
        self,
        symbol: str,
        from_date: Optional[date] = None
    ) -> date:
        """
        Get next weekly expiry for index options
        REQ-COMP-016: Calculate weekly expiry dates

        Index expiry schedule:
        - NIFTY: Weekly expiry on Thursday
        - BANKNIFTY: Weekly expiry on Wednesday
        - FINNIFTY: Weekly expiry on Tuesday

        Args:
            symbol: Index symbol ('NIFTY', 'BANKNIFTY', 'FINNIFTY')
            from_date: Starting date (default: today)

        Returns:
            Next weekly expiry date
        """
        if from_date is None:
            from_date = date.today()

        # Determine expiry day of week
        if 'BANK' in symbol.upper():
            expiry_weekday = 2  # Wednesday
        elif 'FINN' in symbol.upper():
            expiry_weekday = 1  # Tuesday
        else:  # NIFTY
            expiry_weekday = 3  # Thursday

        # Find next expiry day
        days_ahead = expiry_weekday - from_date.weekday()

        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        expiry_date = from_date + timedelta(days=days_ahead)

        # If expiry falls on holiday, move to previous trading day
        while not self.is_trading_day(expiry_date):
            expiry_date -= timedelta(days=1)

        return expiry_date

    def get_monthly_expiry(
        self,
        symbol: str,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> date:
        """
        Get monthly expiry for index options
        REQ-COMP-016: Calculate monthly expiry dates

        Monthly expiry: Last Thursday of the month

        Args:
            symbol: Index symbol
            year: Year (default: current year)
            month: Month (default: current month)

        Returns:
            Monthly expiry date
        """
        if year is None:
            year = date.today().year
        if month is None:
            month = date.today().month

        # Get last day of month
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Find last Thursday (weekday 3)
        while last_day.weekday() != 3:
            last_day -= timedelta(days=1)

        # If falls on holiday, move to previous trading day
        while not self.is_trading_day(last_day):
            last_day -= timedelta(days=1)

        return last_day

    def format_expiry_for_symbol(self, expiry_date: date) -> str:
        """
        Format expiry date for option symbol
        Format: DDMMMYY (e.g., 26DEC24)

        Args:
            expiry_date: Expiry date

        Returns:
            Formatted expiry string
        """
        month_names = [
            'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'
        ]

        day = expiry_date.day
        month = month_names[expiry_date.month - 1]
        year = str(expiry_date.year)[2:]  # Last 2 digits

        return f"{day:02d}{month}{year}"

    def get_days_to_expiry(
        self,
        expiry_date: date,
        from_date: Optional[date] = None
    ) -> int:
        """
        Calculate number of calendar days to expiry

        Args:
            expiry_date: Expiry date
            from_date: Starting date (default: today)

        Returns:
            Number of days to expiry
        """
        if from_date is None:
            from_date = date.today()

        delta = expiry_date - from_date
        return delta.days

    def get_trading_days_to_expiry(
        self,
        expiry_date: date,
        from_date: Optional[date] = None
    ) -> int:
        """
        Calculate number of trading days to expiry
        More accurate for options pricing

        Args:
            expiry_date: Expiry date
            from_date: Starting date (default: today)

        Returns:
            Number of trading days to expiry
        """
        if from_date is None:
            from_date = date.today()

        trading_days = 0
        current_date = from_date

        while current_date < expiry_date:
            if self.is_trading_day(current_date):
                trading_days += 1
            current_date += timedelta(days=1)

        return trading_days

    def get_next_n_expiries(
        self,
        symbol: str,
        n: int = 4,
        from_date: Optional[date] = None
    ) -> List[date]:
        """
        Get next N weekly expiries for a symbol

        Args:
            symbol: Index symbol
            n: Number of expiries to get
            from_date: Starting date (default: today)

        Returns:
            List of next N expiry dates
        """
        if from_date is None:
            from_date = date.today()

        expiries = []
        current_date = from_date

        for _ in range(n):
            expiry = self.get_weekly_expiry(symbol, current_date)
            expiries.append(expiry)
            current_date = expiry + timedelta(days=1)

        return expiries

    def is_expiry_day(
        self,
        symbol: str,
        check_date: Optional[date] = None
    ) -> bool:
        """
        Check if given date is an expiry day for symbol

        Args:
            symbol: Index symbol
            check_date: Date to check (default: today)

        Returns:
            True if expiry day, False otherwise
        """
        if check_date is None:
            check_date = date.today()

        # Get this week's expiry
        expiry = self.get_weekly_expiry(symbol, check_date - timedelta(days=7))

        return check_date == expiry


# Singleton instance
_nse_calendar_instance = None


def get_nse_calendar() -> NSECalendar:
    """Get singleton NSE Calendar instance"""
    global _nse_calendar_instance

    if _nse_calendar_instance is None:
        _nse_calendar_instance = NSECalendar()

    return _nse_calendar_instance


# Example usage
if __name__ == "__main__":
    calendar = NSECalendar()

    # Check if today is trading day
    today = date.today()
    print(f"Is today ({today}) a trading day? {calendar.is_trading_day(today)}")

    # Get next trading day
    next_trading = calendar.get_next_trading_day()
    print(f"Next trading day: {next_trading}")

    # Get weekly expiries
    for symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
        expiry = calendar.get_weekly_expiry(symbol)
        expiry_str = calendar.format_expiry_for_symbol(expiry)
        dte = calendar.get_days_to_expiry(expiry)

        print(f"\n{symbol}:")
        print(f"  Next Expiry: {expiry} ({expiry_str})")
        print(f"  Days to Expiry: {dte}")
        print(f"  Trading Days to Expiry: {calendar.get_trading_days_to_expiry(expiry)}")

    # Get next 4 BANKNIFTY expiries
    print(f"\nNext 4 BANKNIFTY Expiries:")
    expiries = calendar.get_next_n_expiries('BANKNIFTY', n=4)
    for i, exp in enumerate(expiries, 1):
        print(f"  {i}. {exp} ({calendar.format_expiry_for_symbol(exp)})")
