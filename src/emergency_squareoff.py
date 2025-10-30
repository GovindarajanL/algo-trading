"""
Emergency Square-Off Script
Closes all open positions immediately
"""

import sys
import argparse
from utils.config_loader import ConfigLoader
from broker.angel_one import AngelOneBroker
from broker.paper_trading import PaperTradingBroker
from database.database_manager import DatabaseManager


def emergency_square_off(mode: str = 'paper', confirm: bool = False):
    """
    Emergency square-off all positions

    Args:
        mode: Trading mode ('paper' or 'live')
        confirm: Confirmation flag
    """
    if not confirm:
        print("\n" + "="*80)
        print("⚠️  EMERGENCY SQUARE-OFF")
        print("="*80)
        print("This will close ALL open positions immediately using MARKET orders.")
        print("This action CANNOT be undone.")
        print("\nAre you sure you want to continue?")
        user_confirm = input("Type 'YES CLOSE ALL' to confirm: ")

        if user_confirm != "YES CLOSE ALL":
            print("Emergency square-off cancelled.")
            return

    print("\n🚨 INITIATING EMERGENCY SQUARE-OFF...\n")

    # Load configuration
    config_loader = ConfigLoader('config')
    config = config_loader.get_config()

    # Initialize broker
    if mode == 'paper':
        broker = PaperTradingBroker()
    else:
        broker = AngelOneBroker(config['credentials'])

    # Connect
    if not broker.connect():
        print("❌ Failed to connect to broker")
        return

    # Initialize database
    db = DatabaseManager(config['database'].get('path', 'data/trading.db'))

    # Get open positions
    positions = db.get_open_positions()

    if not positions:
        print("✅ No open positions found.")
        broker.logout()
        return

    print(f"Found {len(positions)} open position(s):\n")

    for i, pos in enumerate(positions, 1):
        print(f"{i}. {pos['strategy_name']} - {pos['symbol']} "
              f"(Entry: {pos['entry_time']})")

    print(f"\n{'='*80}")
    print("Closing positions with MARKET orders...")
    print(f"{'='*80}\n")

    closed_count = 0

    for position in positions:
        try:
            print(f"Closing {position['strategy_name']}...")

            # Close all legs
            for leg in position['legs']:
                # Reverse the action
                action = 'SELL' if leg['action'] == 'BUY' else 'BUY'

                order = {
                    'symbol': leg['symbol'],
                    'transaction_type': action,
                    'quantity': leg['quantity'],
                    'order_type': 'MARKET',
                    'price': 0
                }

                order_id = broker.place_order(order)

                if order_id:
                    print(f"  ✅ {action} {leg['quantity']} {leg['symbol']} @ Market")
                else:
                    print(f"  ❌ Failed to place order for {leg['symbol']}")

            # Close position in database
            exit_data = {
                'exit_time': sys.modules['datetime'].datetime.now(),
                'exit_premium': 0,
                'pnl': 0,  # Unknown due to market order
                'exit_reason': 'Emergency square-off',
                'holding_time_minutes': 0
            }

            db.close_position(position['id'], exit_data)
            closed_count += 1

            print(f"  ✅ Position closed in database\n")

        except Exception as e:
            print(f"  ❌ Error closing position: {e}\n")

    print(f"{'='*80}")
    print(f"Emergency square-off complete: {closed_count}/{len(positions)} positions closed")
    print(f"{'='*80}\n")

    broker.logout()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Emergency Square-Off Script")
    parser.add_argument(
        '--mode',
        choices=['paper', 'live'],
        default='paper',
        help='Trading mode (default: paper)'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    if args.mode == 'live':
        print("\n" + "="*80)
        print("⚠️⚠️⚠️  LIVE TRADING MODE  ⚠️⚠️⚠️")
        print("="*80)
        print("You are about to close REAL positions with REAL money.")
        print("This will execute MARKET orders that may have significant slippage.")
        final_confirm = input("\nType 'LIVE EMERGENCY' to continue: ")

        if final_confirm != "LIVE EMERGENCY":
            print("Emergency square-off cancelled.")
            sys.exit(0)

    emergency_square_off(args.mode, args.confirm)


if __name__ == "__main__":
    main()
