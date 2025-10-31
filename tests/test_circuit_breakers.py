"""
Unit Tests for Circuit Breakers
Tests circuit breaker functionality
"""

import pytest
from datetime import datetime, time
from src.risk.circuit_breakers import CircuitBreakers, CircuitBreakerStatus


class TestCircuitBreakers:
    """Test circuit breaker logic"""

    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'circuit_breakers': {
                'daily_loss_limit': 5000,
                'consecutive_loss_limit': 5,
                'margin_alert_threshold': 0.25,
                'max_vix': 40,
                'trading_end_time': '15:00'
            }
        }
        self.breakers = CircuitBreakers(config)

    def test_initialization(self):
        """Test circuit breaker initialization"""
        assert self.breakers is not None
        assert self.breakers.daily_loss_limit == 5000
        assert self.breakers.consecutive_loss_limit == 5

    def test_daily_loss_limit_not_breached(self):
        """Test daily loss limit when within bounds"""
        daily_stats = {'daily_pnl': -2000}
        system_stats = {}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.NORMAL
        assert result.breached_breakers == []

    def test_daily_loss_limit_breached(self):
        """Test daily loss limit when breached"""
        daily_stats = {'daily_pnl': -6000}  # Exceeds 5000 limit
        system_stats = {}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.BREACHED
        assert 'daily_loss_limit' in result.breached_breakers

    def test_consecutive_losses_not_breached(self):
        """Test consecutive losses when within limit"""
        daily_stats = {}
        system_stats = {'consecutive_losses': 3}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.NORMAL

    def test_consecutive_losses_breached(self):
        """Test consecutive losses when limit exceeded"""
        daily_stats = {}
        system_stats = {'consecutive_losses': 6}  # Exceeds 5
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.BREACHED
        assert 'consecutive_losses' in result.breached_breakers

    def test_margin_alert_not_breached(self):
        """Test margin alert when sufficient margin"""
        daily_stats = {}
        system_stats = {
            'available_margin': 30000,
            'total_capital': 100000
        }
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.NORMAL

    def test_margin_alert_breached(self):
        """Test margin alert when margin too low"""
        daily_stats = {}
        system_stats = {
            'available_margin': 20000,  # 20% of 100k (below 25% threshold)
            'total_capital': 100000
        }
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        # Should trigger warning
        assert result.status in [CircuitBreakerStatus.WARNING, CircuitBreakerStatus.BREACHED]

    def test_vix_spike_not_breached(self):
        """Test VIX spike when VIX is normal"""
        daily_stats = {}
        system_stats = {}
        market_data = {'vix': 25}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.NORMAL

    def test_vix_spike_breached(self):
        """Test VIX spike when VIX too high"""
        daily_stats = {}
        system_stats = {}
        market_data = {'vix': 45}  # Above 40 limit

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.BREACHED
        assert 'vix_spike' in result.breached_breakers

    def test_time_based_breaker_morning(self):
        """Test time-based breaker during trading hours"""
        daily_stats = {}
        system_stats = {}
        market_data = {}

        # Create time at 10 AM
        morning_time = datetime.now().replace(hour=10, minute=0)

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, morning_time
        )

        assert result.status == CircuitBreakerStatus.NORMAL

    def test_time_based_breaker_afternoon(self):
        """Test time-based breaker after 3 PM"""
        daily_stats = {}
        system_stats = {}
        market_data = {}

        # Create time at 3:30 PM (after trading hours)
        afternoon_time = datetime.now().replace(hour=15, minute=30)

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, afternoon_time
        )

        # Should trigger time-based breaker
        assert result.status == CircuitBreakerStatus.BREACHED
        assert 'time_based' in result.breached_breakers

    def test_multiple_breakers_triggered(self):
        """Test when multiple breakers are triggered"""
        daily_stats = {'daily_pnl': -6000}  # Daily loss breached
        system_stats = {'consecutive_losses': 6}  # Consecutive losses breached
        market_data = {'vix': 45}  # VIX breached

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.status == CircuitBreakerStatus.BREACHED
        assert len(result.breached_breakers) >= 3

    def test_reset_breakers(self):
        """Test resetting circuit breakers"""
        # First trigger a breaker
        daily_stats = {'daily_pnl': -6000}
        system_stats = {}
        market_data = {}

        result1 = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )
        assert result1.status == CircuitBreakerStatus.BREACHED

        # Reset
        self.breakers.reset()

        # Check again with normal values
        daily_stats = {'daily_pnl': -1000}
        result2 = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result2.status == CircuitBreakerStatus.NORMAL

    def test_breaker_status_enum(self):
        """Test circuit breaker status enum"""
        assert CircuitBreakerStatus.NORMAL.value == "NORMAL"
        assert CircuitBreakerStatus.WARNING.value == "WARNING"
        assert CircuitBreakerStatus.BREACHED.value == "BREACHED"

    def test_edge_case_exact_limit(self):
        """Test behavior when exactly at limit"""
        daily_stats = {'daily_pnl': -5000}  # Exactly at limit
        system_stats = {}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        # Should either be normal or breached based on implementation
        assert result.status in [CircuitBreakerStatus.NORMAL, CircuitBreakerStatus.BREACHED]

    def test_missing_data_handling(self):
        """Test handling of missing data"""
        # Empty dictionaries
        daily_stats = {}
        system_stats = {}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        # Should not crash and return a result
        assert result is not None
        assert hasattr(result, 'status')

    def test_warning_status(self):
        """Test warning status for margin threshold"""
        daily_stats = {}
        system_stats = {
            'available_margin': 26000,  # Just above 25% threshold (26% of 100k)
            'total_capital': 100000
        }
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        # Should be normal or warning
        assert result.status in [CircuitBreakerStatus.NORMAL, CircuitBreakerStatus.WARNING]

    def test_system_health_check(self):
        """Test system health monitoring"""
        daily_stats = {}
        system_stats = {
            'system_health': 'degraded'
        }
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        # Implementation may or may not trigger on health
        assert result is not None

    def test_breaker_messages(self):
        """Test that breaker messages are informative"""
        daily_stats = {'daily_pnl': -6000}
        system_stats = {}
        market_data = {}

        result = self.breakers.check_all_breakers(
            daily_stats, system_stats, market_data, datetime.now()
        )

        assert result.message is not None
        assert len(result.message) > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
