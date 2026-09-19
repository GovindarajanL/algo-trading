#!/usr/bin/env python3
"""
Optimize configuration for swing trading on f1-micro
Run this after deployment to adjust settings for low-resource environment
"""

import yaml
import os

def optimize_config_for_swing():
    """Update config.yaml for swing trading optimization"""
    
    config_path = '/opt/algo-trading/config/config.yaml'
    
    # Check if config exists
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        print("Please run this script on the GCP VM after deployment")
        return
    
    # Read current config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Optimize for swing trading / f1-micro
    optimizations = {
        'data': {
            'enable_cache': True,
            'cache_ttl_seconds': 300,  # 5 minutes
            'use_websocket': False,    # REST API only
            'polling_interval': 300,    # Check every 5 minutes
        },
        'monitoring': {
            'check_interval': 300,      # 5 minutes
            'update_greeks': True,
            'greeks_interval': 900,     # 15 minutes
        },
        'strategies': {
            'iron_condor': {
                'enabled': True,
                'check_interval': 600,  # 10 minutes
                'max_positions': 2,
            }
        },
        'risk_limits': {
            'max_positions': 3,
            'position_size_pct': 0.05,
        },
        'execution': {
            'order_type': 'LIMIT',
            'max_retry': 3,
            'retry_delay': 30,
        },
        'performance': {
            'batch_size': 10,
            'max_workers': 1,          # Single thread
            'db_connection_pool': 1,   # Single connection
        }
    }
    
    # Merge optimizations
    for key, value in optimizations.items():
        if key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    # Backup original
    backup_path = config_path + '.backup'
    os.rename(config_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    # Write optimized config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Config optimized for swing trading on f1-micro")
    print(f"   - Position checks: Every 5 minutes (vs real-time)")
    print(f"   - WebSocket: Disabled (REST API polling)")
    print(f"   - Greeks updates: Every 15 minutes")
    print(f"   - Max positions: 3 concurrent")
    print(f"   - Single thread execution (low CPU)")
    print("")
    print("Restart the trading system:")
    print("  sudo systemctl restart algo-trading.service")

if __name__ == '__main__':
    optimize_config_for_swing()
