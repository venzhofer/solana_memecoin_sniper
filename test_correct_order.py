#!/usr/bin/env python3
"""
Correct Order Trading Test - Creates bars in the right order for strategy
"""

import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from indicators import update_all_for_bar, reset_indicators
from db import (
    upsert_safe_token, insert_ohlc_1m, insert_ema_1m, insert_atr_1m,
    count_tokens, get_stats
)

def test_correct_order():
    """Test that creates bars in correct order for strategy."""
    print("🚀 CORRECT ORDER TRADING TEST - SHOULD EXECUTE TRADES!")
    print("=" * 70)
    
    # Load strategies
    print("\n1️⃣ Loading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Create token
    print("\n2️⃣ Creating test token...")
    token = {
        "address": "correct_order_token",
        "name": "Correct Order Token",
        "symbol": "COT",
        "dex": "Raydium",
        "risk": 10,
        "signature": "sig_cot",
        "rc": {"score": 10, "details": "test"}
    }
    
    upsert_safe_token(**token)
    dispatch_new_token(token)
    print(f"   ✅ Token created: {token['name']} ({token['symbol']})")
    
    # Create bars in CORRECT chronological order
    print("\n3️⃣ Creating bars in correct chronological order...")
    base_timestamp = int(time.time()) - 300  # Start 5 minutes ago
    
    # Bar 1: Oldest (baseline)
    print("   📊 Bar 1: Oldest baseline")
    bar1 = {
        "address": token["address"],
        "ts_start": base_timestamp,
        "open": 1.0,
        "high": 1.02,
        "low": 0.98,
        "close": 1.0,
        "fdv_usd": 1000000,
        "marketcap_usd": 500000,
        "samples": 30
    }
    insert_ohlc_1m(bar1)
    ema_rows, atr_rows = update_all_for_bar(bar1)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    dispatch_bar_1m(bar1, ema_rows, atr_rows)
    print(f"      O:1.0000 H:1.0200 L:0.9800 C:1.0000 | EMA(5): {ema_rows[0]['value']:.6f} | ATR(14): {atr_rows[0]['value']:.6f}")
    
    # Bar 2: Second oldest
    print("   📊 Bar 2: Second oldest")
    bar2 = {
        "address": token["address"],
        "ts_start": base_timestamp + 60,
        "open": 1.0,
        "high": 1.03,
        "low": 0.99,
        "close": 1.01,
        "fdv_usd": 1010000,
        "marketcap_usd": 505000,
        "samples": 30
    }
    insert_ohlc_1m(bar2)
    ema_rows, atr_rows = update_all_for_bar(bar2)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    dispatch_bar_1m(bar2, ema_rows, atr_rows)
    print(f"      O:1.0000 H:1.0300 L:0.9900 C:1.0100 | EMA(5): {ema_rows[0]['value']:.6f} | ATR(14): {atr_rows[0]['value']:.6f}")
    
    # Bar 3: Third oldest
    print("   📊 Bar 3: Third oldest")
    bar3 = {
        "address": token["address"],
        "ts_start": base_timestamp + 120,
        "open": 1.01,
        "high": 1.025,
        "low": 0.995,
        "close": 1.005,
        "fdv_usd": 1005000,
        "marketcap_usd": 502500,
        "samples": 30
    }
    insert_ohlc_1m(bar3)
    ema_rows, atr_rows = update_all_for_bar(bar3)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    dispatch_bar_1m(bar3, ema_rows, atr_rows)
    print(f"      O:1.0100 H:1.0250 L:0.9950 C:1.0050 | EMA(5): {ema_rows[0]['value']:.6f} | ATR(14): {atr_rows[0]['value']:.6f}")
    
    # Bar 4: NEWEST (breakout)
    print("   📊 Bar 4: NEWEST BREAKOUT (should trigger trade)")
    bar4 = {
        "address": token["address"],
        "ts_start": base_timestamp + 180,
        "open": 1.005,
        "high": 1.15,  # 15% jump!
        "low": 1.005,
        "close": 1.15,
        "fdv_usd": 1150000,
        "marketcap_usd": 575000,
        "samples": 30
    }
    insert_ohlc_1m(bar4)
    ema_rows, atr_rows = update_all_for_bar(bar4)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    
    print(f"      O:1.0050 H:1.1500 L:1.0050 C:1.1500 | EMA(5): {ema_rows[0]['value']:.6f} | ATR(14): {atr_rows[0]['value']:.6f}")
    
    # Check strategy conditions
    from db import get_ohlc_1m
    bars = get_ohlc_1m(token["address"], 5)
    if bars and len(bars) >= 4:
        # Bars are returned newest first, so we need to reverse for chronological order
        chronological_bars = list(reversed(bars))
        print(f"      📊 Bars in chronological order:")
        for i, b in enumerate(chronological_bars):
            print(f"         Bar {i+1}: O:{b[1]:.4f} H:{b[2]:.4f} L:{b[3]:.4f} C:{b[4]:.4f}")
        
        # Check strategy conditions
        if len(chronological_bars) >= 4:
            prev_bars = chronological_bars[0:3]  # First 3 bars (oldest)
            recent_high = max(b[2] for b in prev_bars)  # high prices
            print(f"      📊 Strategy check: Close(1.15) > EMA(5) on low({ema_rows[0]['value']:.6f})? {'✅ YES' if 1.15 > ema_rows[0]['value'] else '❌ NO'}")
            print(f"      📊 Strategy check: Close(1.15) > Recent high({recent_high:.4f})? {'✅ YES' if 1.15 > recent_high else '❌ NO'}")
            print(f"      📊 Strategy check: Enough bars for LOOKBACK? {'✅ YES' if len(bars) >= 4 else '❌ NO'}")
    
    # Send to strategies
    print("\n   🎯 Dispatching breakout bar to strategies...")
    dispatch_bar_1m(bar4, ema_rows, atr_rows)
    
    # Check for trade execution
    print("\n4️⃣ Checking for executed trades...")
    from papertrading.db import pos_get
    
    pos = pos_get(token["address"])
    if pos:
        print(f"   🎉 TRADE EXECUTED! Position: {pos}")
        print(f"   📊 Status: {pos[1]}")
        print(f"   📊 Entry price: {pos[3]}")
        print(f"   📊 Stop price: {pos[4]}")
        print(f"   📊 Entry market cap: {pos[8] if len(pos) > 8 else 'N/A'}")
    else:
        print(f"   ⚪ No trade executed")
    
    # Check database status
    print("\n5️⃣ Final status...")
    stats = get_stats()
    print(f"   📊 Tokens: {stats['total']}")
    
    print(f"\n✅ Correct order trading test finished!")
    
    # Shutdown
    print(f"\n🔄 Shutting down...")
    shutdown()
    print(f"   ✅ Done")

if __name__ == "__main__":
    try:
        test_correct_order()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown()
