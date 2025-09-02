#!/usr/bin/env python3
"""
Live Paper Trading Test - Simulates the complete system without internet
"""

import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from trading_bot.papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from trading_bot.indicators import update_all_for_bar, reset_indicators
from trading_bot.db import insert_ohlc_1m, insert_ema_1m, insert_atr_1m, upsert_safe_token

def simulate_live_trading():
    """Simulate live paper trading with fake data."""
    print("🚀 LIVE PAPER TRADING SIMULATION")
    print("=" * 60)
    
    # Load strategies
    print("🔄 Loading paper trading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Simulate new token discovery
    test_addr = "simulated_token_live"
    print(f"\n🆕 Simulating new token discovery: {test_addr}")
    
    token_data = {
        "address": test_addr,
        "name": "Live Test Token",
        "symbol": "LIVE",
        "dex": "Raydium",
        "risk": 12,
        "signature": "sim_sig_live_123"
    }
    
    # Store token and notify strategies
    upsert_safe_token(**token_data)
    dispatch_new_token(token_data)
    print(f"   ✅ Token stored and strategies notified")
    
    # Simulate live price updates
    print(f"\n📈 Simulating live price updates...")
    base_price = 1.0
    timestamp = int(time.time())
    
    for i in range(10):  # Simulate 10 price updates
        # Generate realistic price movement
        change = random.uniform(-0.05, 0.08)  # -5% to +8%
        base_price *= (1 + change)
        
        # Create OHLC bar
        high = base_price * random.uniform(1.0, 1.1)
        low = base_price * random.uniform(0.9, 1.0)
        open_price = base_price
        close_price = base_price * (1 + random.uniform(-0.02, 0.03))
        
        bar = {
            "address": test_addr,
            "ts_start": timestamp + (i * 60),  # 1 minute intervals
            "open": open_price,
            "high": high,
            "low": low,
            "close": close_price,
            "fdv_usd": 1000000 * (1 + i * 0.1),
            "marketcap_usd": 500000 * (1 + i * 0.1),
            "samples": 30
        }
        
        print(f"\n🔄 Update {i+1}: O:{open_price:.4f} H:{high:.4f} L:{low:.4f} C:{close_price:.4f}")
        
        # Process OHLC and indicators
        insert_ohlc_1m(bar)
        ema_rows, atr_rows = update_all_for_bar(bar)
        insert_ema_1m(ema_rows)
        insert_atr_1m(atr_rows)
        
        # Notify strategies
        bar_for_strat = {
            "address": bar["address"],
            "ts_start": bar["ts_start"],
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "marketcap_usd": bar.get("marketcap_usd"),
        }
        dispatch_bar_1m(bar_for_strat, ema_rows, atr_rows)
        
        print(f"   📊 Indicators: {len(ema_rows)} EMAs, {len(atr_rows)} ATRs")
        
        # Show current values
        for ema_row in ema_rows:
            print(f"      EMA({ema_row['length']}): {ema_row['value']:.6f}")
        for atr_row in atr_rows:
            print(f"      ATR({atr_row['length']}): {atr_row['value']:.6f}")
        
        time.sleep(1)  # Simulate real-time updates
    
    print(f"\n✅ Live trading simulation completed!")
    
    # Shutdown strategies
    print(f"\n🔄 Shutting down strategies...")
    shutdown()
    print(f"   ✅ Strategies shut down")

if __name__ == "__main__":
    try:
        simulate_live_trading()
    except KeyboardInterrupt:
        print("\n\n🛑 Simulation interrupted by user")
        shutdown()
        print("👋 Goodbye!")
