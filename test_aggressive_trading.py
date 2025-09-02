#!/usr/bin/env python3
"""
Aggressive Trading Test - Simulates price movements that should trigger trades
"""

import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from trading_bot.papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from trading_bot.indicators import update_all_for_bar, reset_indicators
from trading_bot.db import (
    upsert_safe_token, insert_ohlc_1m, insert_ema_1m, insert_atr_1m,
    count_tokens, get_stats
)

def test_aggressive_trading():
    """Test with aggressive price movements to trigger trades."""
    print("🚀 AGGRESSIVE TRADING TEST - SHOULD TRIGGER TRADES!")
    print("=" * 70)
    
    # Load strategies
    print("\n1️⃣ Loading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Create a token with aggressive price movement
    print("\n2️⃣ Creating test token with aggressive movement...")
    token = {
        "address": "aggressive_token",
        "name": "Aggressive Test Token",
        "symbol": "AGGR",
        "dex": "Raydium",
        "risk": 10,
        "signature": "sig_aggr",
        "rc": {"score": 10, "details": "test"}
    }
    
    upsert_safe_token(**token)
    dispatch_new_token(token)
    print(f"   ✅ Token created: {token['name']} ({token['symbol']})")
    
    # Generate aggressive price movement
    print("\n3️⃣ Generating aggressive price movement...")
    base_price = 1.0
    timestamp = int(time.time())
    
    # First: Create some baseline bars
    print("   📊 Creating baseline bars...")
    for i in range(3):
        bar = {
            "address": token["address"],
            "ts_start": timestamp + (i * 60),
            "open": base_price,
            "high": base_price * 1.02,
            "low": base_price * 0.98,
            "close": base_price,
            "fdv_usd": 1000000,
            "marketcap_usd": 500000,
            "samples": 30
        }
        
        insert_ohlc_1m(bar)
        ema_rows, atr_rows = update_all_for_bar(bar)
        insert_ema_1m(ema_rows)
        insert_atr_1m(atr_rows)
        
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
        
        print(f"      Baseline {i+1}: O:{bar['open']:.4f} H:{bar['high']:.4f} L:{bar['low']:.4f} C:{bar['close']:.4f}")
        time.sleep(0.1)
    
    # Now: Create breakout bar
    print("\n   🚀 Creating BREAKOUT bar...")
    breakout_price = base_price * 1.15  # 15% jump!
    breakout_bar = {
        "address": token["address"],
        "ts_start": timestamp + (3 * 60),
        "open": base_price,
        "high": breakout_price * 1.05,
        "low": base_price,
        "close": breakout_price,
        "fdv_usd": 1150000,
        "marketcap_usd": 575000,
        "samples": 30
    }
    
    insert_ohlc_1m(breakout_bar)
    ema_rows, atr_rows = update_all_for_bar(breakout_bar)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    
    bar_for_strat = {
        "address": breakout_bar["address"],
        "ts_start": breakout_bar["ts_start"],
        "open": breakout_bar["open"],
        "high": breakout_bar["high"],
        "low": breakout_bar["low"],
        "close": breakout_bar["close"],
        "marketcap_usd": breakout_bar.get("marketcap_usd"),
    }
    
    print(f"      BREAKOUT: O:{breakout_bar['open']:.4f} H:{breakout_bar['high']:.4f} L:{breakout_bar['low']:.4f} C:{breakout_bar['close']:.4f}")
    print(f"      📊 Indicators: {len(ema_rows)} EMAs, {len(atr_rows)} ATRs")
    
    # Show indicator values
    for ema_row in ema_rows:
        print(f"         EMA({ema_row['length']}): {ema_row['value']:.6f}")
    for atr_row in atr_rows:
        print(f"         ATR({atr_row['length']}): {atr_row['value']:.6f}")
    
    # Send to strategies - THIS SHOULD TRIGGER A TRADE!
    print("\n   🎯 Dispatching breakout bar to strategies...")
    dispatch_bar_1m(bar_for_strat, ema_rows, atr_rows)
    
    # Check if trade was executed
    print("\n4️⃣ Checking for executed trades...")
    from trading_bot.papertrading.db import pos_get
    
    pos = pos_get(token["address"])
    if pos:
        print(f"   🎉 TRADE EXECUTED! Position: {pos}")
    else:
        print(f"   ⚪ No trade executed yet")
    
    # Check database status
    print("\n5️⃣ Final status...")
    stats = get_stats()
    print(f"   📊 Tokens: {stats['total']}")
    print(f"   📊 Low risk: {stats['low_risk_0_10']}")
    
    print(f"\n✅ Aggressive trading test finished!")
    
    # Shutdown
    print(f"\n🔄 Shutting down...")
    shutdown()
    print(f"   ✅ Done")

if __name__ == "__main__":
    try:
        test_aggressive_trading()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown()
