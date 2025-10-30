"""
Database Manager
Handles all database operations
REQ-DATA-016 to REQ-DATA-020
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
import logging
import json


class DatabaseManager:
    """
    Database manager for trade and position storage
    REQ-DATA-016 to REQ-DATA-020
    """

    def __init__(self, db_path: str = "data/trading.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.connection = None

        # Initialize database
        self._create_tables()

        self.logger.info(f"Database initialized: {db_path}")

    def connect(self):
        """Create database connection"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Access columns by name
        return self.connection

    def _create_tables(self):
        """
        Create database tables
        REQ-DATA-017: Store trade logs permanently
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                entry_premium REAL NOT NULL,
                exit_premium REAL,
                pnl REAL,
                max_loss REAL NOT NULL,
                max_profit REAL NOT NULL,
                status TEXT NOT NULL,
                exit_reason TEXT,
                legs TEXT NOT NULL,
                entry_greeks TEXT,
                exit_greeks TEXT,
                adjustments_count INTEGER DEFAULT 0,
                holding_time_minutes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Positions table (active)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_time TIMESTAMP NOT NULL,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                legs TEXT NOT NULL,
                entry_premium REAL NOT NULL,
                current_value REAL,
                unrealized_pnl REAL,
                max_loss REAL NOT NULL,
                max_profit REAL NOT NULL,
                current_greeks TEXT,
                adjustments_count INTEGER DEFAULT 0,
                last_adjustment_time TIMESTAMP,
                target_profit_pct REAL,
                stop_loss_pct REAL,
                status TEXT DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                strategies_used TEXT,
                circuit_breakers_triggered INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Risk events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TIMESTAMP NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                action_taken TEXT,
                positions_affected INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indices for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_date
            ON trades(trade_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_strategy
            ON trades(strategy_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_status
            ON positions(status)
        """)

        conn.commit()
        conn.close()

    def insert_trade(self, trade: Dict) -> int:
        """
        Insert completed trade
        REQ-DATA-017: Store trade logs

        Args:
            trade: Trade dictionary with all details

        Returns:
            Trade ID
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                trade_date, strategy_name, symbol, expiry_date,
                entry_time, exit_time, entry_premium, exit_premium,
                pnl, max_loss, max_profit, status, exit_reason,
                legs, entry_greeks, exit_greeks, adjustments_count,
                holding_time_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.get('trade_date', datetime.now().date()),
            trade['strategy_name'],
            trade['symbol'],
            trade['expiry_date'],
            trade['entry_time'],
            trade.get('exit_time'),
            trade['entry_premium'],
            trade.get('exit_premium'),
            trade.get('pnl'),
            trade['max_loss'],
            trade['max_profit'],
            trade.get('status', 'COMPLETED'),
            trade.get('exit_reason'),
            json.dumps(trade.get('legs', [])),
            json.dumps(trade.get('entry_greeks', {})),
            json.dumps(trade.get('exit_greeks', {})),
            trade.get('adjustments_count', 0),
            trade.get('holding_time_minutes')
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.logger.debug(f"Trade inserted: ID={trade_id}")
        return trade_id

    def insert_position(self, position: Dict) -> int:
        """
        Insert new position
        REQ-POS-002: Store position entry details

        Args:
            position: Position dictionary

        Returns:
            Position ID
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO positions (
                entry_time, strategy_name, symbol, expiry_date,
                legs, entry_premium, max_loss, max_profit,
                current_greeks, target_profit_pct, stop_loss_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position['entry_time'],
            position['strategy_name'],
            position['symbol'],
            position['expiry_date'],
            json.dumps(position['legs']),
            position['entry_premium'],
            position['max_loss'],
            position['max_profit'],
            json.dumps(position.get('current_greeks', {})),
            position.get('target_profit_pct'),
            position.get('stop_loss_pct')
        ))

        position_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.logger.debug(f"Position inserted: ID={position_id}")
        return position_id

    def update_position(self, position_id: int, updates: Dict):
        """
        Update position
        REQ-POS-003: Calculate position P&L continuously

        Args:
            position_id: Position ID
            updates: Dictionary with fields to update
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Build update query dynamically
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(position_id)

        cursor.execute(f"""
            UPDATE positions
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)

        conn.commit()
        conn.close()

    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions
        REQ-POS-001: Track all open positions

        Returns:
            List of position dictionaries
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM positions
            WHERE status = 'OPEN'
            ORDER BY entry_time DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        positions = []
        for row in rows:
            pos = dict(row)
            pos['legs'] = json.loads(pos['legs'])
            pos['current_greeks'] = json.loads(pos.get('current_greeks', '{}'))
            positions.append(pos)

        return positions

    def close_position(self, position_id: int, exit_data: Dict):
        """
        Close position and move to trades

        Args:
            position_id: Position ID
            exit_data: Exit details (time, premium, pnl, etc.)
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Get position data
        cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        position = dict(cursor.fetchone())

        # Insert into trades
        trade_data = {
            'trade_date': datetime.now().date(),
            'strategy_name': position['strategy_name'],
            'symbol': position['symbol'],
            'expiry_date': position['expiry_date'],
            'entry_time': position['entry_time'],
            'exit_time': exit_data['exit_time'],
            'entry_premium': position['entry_premium'],
            'exit_premium': exit_data['exit_premium'],
            'pnl': exit_data['pnl'],
            'max_loss': position['max_loss'],
            'max_profit': position['max_profit'],
            'status': 'COMPLETED',
            'exit_reason': exit_data.get('exit_reason'),
            'legs': position['legs'],
            'entry_greeks': position.get('current_greeks', '{}'),
            'exit_greeks': json.dumps(exit_data.get('exit_greeks', {})),
            'adjustments_count': position.get('adjustments_count', 0),
            'holding_time_minutes': exit_data.get('holding_time_minutes')
        }

        self.insert_trade(trade_data)

        # Delete from positions
        cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))

        conn.commit()
        conn.close()

        self.logger.info(f"Position {position_id} closed and moved to trades")

    def get_daily_stats(self, date: str = None) -> Dict:
        """
        Get daily statistics
        REQ-DATA-017: Daily statistics

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Dictionary with daily stats
        """
        if date is None:
            date = datetime.now().date()

        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as daily_pnl,
                MAX(pnl) as largest_win,
                MIN(pnl) as largest_loss
            FROM trades
            WHERE trade_date = ?
        """, (date,))

        row = cursor.fetchone()
        conn.close()

        return {
            'total_trades': row['total_trades'] or 0,
            'winning_trades': row['winning_trades'] or 0,
            'losing_trades': row['losing_trades'] or 0,
            'daily_pnl': row['daily_pnl'] or 0,
            'largest_win': row['largest_win'] or 0,
            'largest_loss': row['largest_loss'] or 0
        }

    def get_trades(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get historical trades
        REQ-DATA-006: Historical data access

        Args:
            limit: Number of trades to return
            offset: Offset for pagination

        Returns:
            List of trade dictionaries
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM trades
            ORDER BY exit_time DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        trades = []
        for row in rows:
            trade = dict(row)
            trade['legs'] = json.loads(trade['legs'])
            trade['entry_greeks'] = json.loads(trade.get('entry_greeks', '{}'))
            trade['exit_greeks'] = json.loads(trade.get('exit_greeks', '{}'))
            trades.append(trade)

        return trades

    def log_risk_event(self, event: Dict):
        """
        Log risk event
        REQ-DATA-017: Comprehensive audit trail

        Args:
            event: Risk event dictionary
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO risk_events (
                event_time, event_type, description, action_taken, positions_affected
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            event.get('event_time', datetime.now()),
            event['event_type'],
            event['description'],
            event.get('action_taken'),
            event.get('positions_affected', 0)
        ))

        conn.commit()
        conn.close()

    def backup_database(self, backup_path: str):
        """
        Create database backup
        REQ-DATA-019: Implement backup procedures

        Args:
            backup_path: Path for backup file
        """
        import shutil

        try:
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
