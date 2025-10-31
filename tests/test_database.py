"""
Unit Tests for Database Operations
Tests DatabaseManager functionality
"""

import pytest
import os
import tempfile
from datetime import datetime
from src.database.database_manager import DatabaseManager


class TestDatabaseManager:
    """Test database operations"""

    def setup_method(self):
        """Set up test fixtures with temporary database"""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        config = {
            'database': {
                'type': 'sqlite',
                'path': self.temp_db_path
            }
        }
        self.db = DatabaseManager(config)

    def teardown_method(self):
        """Clean up after tests"""
        self.db.close()
        # Remove temporary database
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_database_initialization(self):
        """Test database initializes with correct tables"""
        # Verify tables exist
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        assert 'positions' in tables
        assert 'trades' in tables
        assert 'daily_summary' in tables
        assert 'risk_events' in tables

    def test_insert_position(self):
        """Test inserting a new position"""
        position = {
            'strategy_name': 'Iron Condor',
            'symbol': 'BANKNIFTY',
            'expiry_date': '2024-12-26',
            'entry_time': datetime.now().isoformat(),
            'legs': '[{"strike": 44000, "type": "PE"}]',
            'entry_price': 250.0,
            'quantity': 25,
            'max_loss': 800,
            'max_profit': 400,
            'target_profit': 200,
            'stop_loss': 800,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)

        assert position_id is not None
        assert position_id > 0

    def test_get_position_by_id(self):
        """Test retrieving position by ID"""
        # Insert position
        position = {
            'strategy_name': 'Bull Call Spread',
            'symbol': 'BANKNIFTY',
            'expiry_date': '2024-12-26',
            'entry_time': datetime.now().isoformat(),
            'legs': '[]',
            'entry_price': 100.0,
            'quantity': 25,
            'max_loss': 500,
            'max_profit': 500,
            'target_profit': 250,
            'stop_loss': 500,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)

        # Retrieve position
        retrieved = self.db.get_position(position_id)

        assert retrieved is not None
        assert retrieved['id'] == position_id
        assert retrieved['strategy_name'] == 'Bull Call Spread'
        assert retrieved['status'] == 'OPEN'

    def test_get_open_positions(self):
        """Test getting all open positions"""
        # Insert multiple positions
        for i in range(3):
            position = {
                'strategy_name': f'Strategy_{i}',
                'symbol': 'BANKNIFTY',
                'expiry_date': '2024-12-26',
                'entry_time': datetime.now().isoformat(),
                'legs': '[]',
                'entry_price': 100.0,
                'quantity': 25,
                'max_loss': 500,
                'max_profit': 500,
                'target_profit': 250,
                'stop_loss': 500,
                'status': 'OPEN'
            }
            self.db.insert_position(position)

        # Get open positions
        open_positions = self.db.get_open_positions()

        assert len(open_positions) == 3
        assert all(pos['status'] == 'OPEN' for pos in open_positions)

    def test_update_position(self):
        """Test updating a position"""
        # Insert position
        position = {
            'strategy_name': 'Iron Condor',
            'symbol': 'BANKNIFTY',
            'expiry_date': '2024-12-26',
            'entry_time': datetime.now().isoformat(),
            'legs': '[]',
            'entry_price': 250.0,
            'quantity': 25,
            'max_loss': 800,
            'max_profit': 400,
            'target_profit': 200,
            'stop_loss': 800,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)

        # Update position
        updates = {
            'current_price': 200.0,
            'current_pnl': 50.0
        }
        self.db.update_position(position_id, updates)

        # Verify update
        updated = self.db.get_position(position_id)
        assert updated['current_price'] == 200.0
        assert updated['current_pnl'] == 50.0

    def test_close_position(self):
        """Test closing a position and moving to trades"""
        # Insert position
        position = {
            'strategy_name': 'Iron Condor',
            'symbol': 'BANKNIFTY',
            'expiry_date': '2024-12-26',
            'entry_time': datetime.now().isoformat(),
            'legs': '[]',
            'entry_price': 250.0,
            'quantity': 25,
            'max_loss': 800,
            'max_profit': 400,
            'target_profit': 200,
            'stop_loss': 800,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)

        # Close position
        exit_data = {
            'exit_time': datetime.now().isoformat(),
            'exit_price': 200.0,
            'realized_pnl': 50.0,
            'exit_reason': 'Target reached'
        }
        self.db.close_position(position_id, exit_data)

        # Verify position is closed
        closed = self.db.get_position(position_id)
        assert closed is None or closed['status'] == 'CLOSED'

        # Verify trade record exists
        trades = self.db.get_trades_history(limit=1)
        assert len(trades) > 0
        assert trades[0]['realized_pnl'] == 50.0

    def test_get_trades_history(self):
        """Test retrieving trade history"""
        # Insert and close multiple positions
        for i in range(5):
            position = {
                'strategy_name': f'Strategy_{i}',
                'symbol': 'BANKNIFTY',
                'expiry_date': '2024-12-26',
                'entry_time': datetime.now().isoformat(),
                'legs': '[]',
                'entry_price': 100.0,
                'quantity': 25,
                'max_loss': 500,
                'max_profit': 500,
                'target_profit': 250,
                'stop_loss': 500,
                'status': 'OPEN'
            }
            position_id = self.db.insert_position(position)

            # Close it
            exit_data = {
                'exit_time': datetime.now().isoformat(),
                'exit_price': 110.0,
                'realized_pnl': 10.0 * i,
                'exit_reason': 'Test'
            }
            self.db.close_position(position_id, exit_data)

        # Get trade history
        trades = self.db.get_trades_history(limit=10)

        assert len(trades) >= 5

    def test_insert_daily_summary(self):
        """Test inserting daily summary"""
        summary = {
            'date': datetime.now().date().isoformat(),
            'total_trades': 5,
            'winning_trades': 3,
            'losing_trades': 2,
            'total_pnl': 500.0,
            'win_rate': 0.60,
            'average_win': 200.0,
            'average_loss': -50.0,
            'largest_win': 300.0,
            'largest_loss': -100.0,
            'sharpe_ratio': 1.5
        }

        self.db.insert_daily_summary(summary)

        # Verify summary was inserted
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM daily_summary WHERE date = ?",
                      (summary['date'],))
        result = cursor.fetchone()

        assert result is not None

    def test_get_daily_summary(self):
        """Test retrieving daily summary"""
        today = datetime.now().date().isoformat()

        summary = {
            'date': today,
            'total_trades': 10,
            'winning_trades': 6,
            'losing_trades': 4,
            'total_pnl': 1000.0,
            'win_rate': 0.60,
            'average_win': 250.0,
            'average_loss': -125.0,
            'largest_win': 500.0,
            'largest_loss': -200.0,
            'sharpe_ratio': 2.0
        }

        self.db.insert_daily_summary(summary)

        # Retrieve summary
        retrieved = self.db.get_daily_summary(today)

        assert retrieved is not None
        assert retrieved['total_trades'] == 10
        assert retrieved['total_pnl'] == 1000.0

    def test_insert_risk_event(self):
        """Test inserting risk event"""
        event = {
            'event_time': datetime.now().isoformat(),
            'event_type': 'CIRCUIT_BREAKER',
            'severity': 'HIGH',
            'description': 'Daily loss limit reached',
            'action_taken': 'All trading halted'
        }

        event_id = self.db.insert_risk_event(event)

        assert event_id is not None
        assert event_id > 0

    def test_get_risk_events(self):
        """Test retrieving risk events"""
        # Insert events
        for i in range(3):
            event = {
                'event_time': datetime.now().isoformat(),
                'event_type': 'CIRCUIT_BREAKER',
                'severity': 'HIGH',
                'description': f'Event {i}',
                'action_taken': 'Halted'
            }
            self.db.insert_risk_event(event)

        # Retrieve events
        events = self.db.get_risk_events(limit=10)

        assert len(events) >= 3

    def test_get_today_stats(self):
        """Test getting today's statistics"""
        # Insert some trades for today
        for i in range(3):
            position = {
                'strategy_name': f'Strategy_{i}',
                'symbol': 'BANKNIFTY',
                'expiry_date': '2024-12-26',
                'entry_time': datetime.now().isoformat(),
                'legs': '[]',
                'entry_price': 100.0,
                'quantity': 25,
                'max_loss': 500,
                'max_profit': 500,
                'target_profit': 250,
                'stop_loss': 500,
                'status': 'OPEN'
            }
            position_id = self.db.insert_position(position)

            exit_data = {
                'exit_time': datetime.now().isoformat(),
                'exit_price': 120.0,
                'realized_pnl': 100.0,
                'exit_reason': 'Test'
            }
            self.db.close_position(position_id, exit_data)

        # Get stats
        stats = self.db.get_today_stats()

        assert 'total_trades' in stats
        assert 'total_pnl' in stats
        assert stats['total_trades'] >= 3

    def test_database_persistence(self):
        """Test that data persists across connections"""
        # Insert position
        position = {
            'strategy_name': 'Test Strategy',
            'symbol': 'BANKNIFTY',
            'expiry_date': '2024-12-26',
            'entry_time': datetime.now().isoformat(),
            'legs': '[]',
            'entry_price': 100.0,
            'quantity': 25,
            'max_loss': 500,
            'max_profit': 500,
            'target_profit': 250,
            'stop_loss': 500,
            'status': 'OPEN'
        }

        position_id = self.db.insert_position(position)

        # Close and reopen database
        self.db.close()

        config = {
            'database': {
                'type': 'sqlite',
                'path': self.temp_db_path
            }
        }
        self.db = DatabaseManager(config)

        # Verify position still exists
        retrieved = self.db.get_position(position_id)
        assert retrieved is not None
        assert retrieved['strategy_name'] == 'Test Strategy'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
