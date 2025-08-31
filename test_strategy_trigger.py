#!/usr/bin/env python3
"""
Strategy Trigger Test - Creates proper conditions for the EarlyMomentum strategy
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

def test_strategy_trigger():
    """Test that creates proper conditions for strategy entry."""
    print("🚀 STRATEGY TRIGGER TEST - SHOULD EXECUTE TRADES!")
    print("=" * 70)
    
    # Load strategies
    print("\n1️⃣ Loading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Create token
    print("\n2️⃣ Creating test token...")
    token = {
        "address": "strategy_test_token",
        "name": "Strategy Test Token",
        "symbol": "STT",
        "dex": "Raydium",
        "risk": 10,
        "signature": "sig_stt",
        "rc": {"score": 10, "details": "test"}
    }
    
    upsert_safe_token(**token)
    dispatch_new_token(token)
    print(f"   ✅ Token created: {token['name']} ({token['symbol']})")
    
    # Create bars that should trigger the strategy
    print("\n3️⃣ Creating bars for strategy analysis...")
    timestamp = int(time.time())
    
    # Bar 1: Baseline
    print("   📊 Bar 1: Baseline")
    bar1 = {
        "address": token["address"],
        "ts_start": timestamp,
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
    
    # Bar 2: Slight increase
    print("   📊 Bar 2: Slight increase")
    bar2 = {
        "address": token["address"],
        "ts_start": timestamp + 60,
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
    
    # Bar 3: Breakout above EMA and recent high
    print("   📊 Bar 3: BREAKOUT (should trigger trade)")
    bar3 = {
        "address": token["address"],
        "ts_start": timestamp + 120,
        "open": 1.01,
        "high": 1.15,  # 15% jump!
        "low": 1.01,
        "close": 1.15,
        "fdv_usd": 1150000,
        "marketcap_usd": 575000,
        "samples": 30
    }
    insert_ohlc_1m(bar3)
    ema_rows, atr_rows = update_all_for_bar(bar3)
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    
    print(f"      O:1.0100 H:1.1500 L:1.0100 C:1.1500 | EMA(5): {ema_rows[0]['value']:.6f} | ATR(14): {atr_rows[0]['value']:.6f}")
    print(f"      📊 Strategy check: Close(1.15) > EMA(5) on low({ema_rows[0]['value']:.6f})? {'✅ YES' if 1.15 > ema_rows[0]['value'] else '❌ NO'}")
    print(f"      📊 Strategy check: Close(1.15) > Recent high(1.03)? {'✅ YES' if 1.15 > 1.03 else '❌ NO'}")
    
    # Send to strategies
    print("\n   🎯 Dispatching breakout bar to strategies...")
    dispatch_bar_1m(bar3, ema_rows, atr_rows)
    
    # Check for trade execution
    print("\n4️⃣ Checking for executed trades...")
    from papertrading.db import pos_get
    
    pos = pos_get(token["address"])
    if pos:
        print(f"   🎉 TRADE EXECUTED! Position: {pos}")
        print(f"   📊 Status: {pos[1]}")
        print(f"   📊 Entry price: {pos[3]}")
        print(f"   📊 Stop price: {pos[4]}")
    else:
        print(f"   ⚪ No trade executed")
        print(f"   🔍 Checking strategy conditions...")
        
        # Debug strategy conditions
        from db import get_ohlc_1m
        bars = get_ohlc_1m(token["address"], 5)
        if bars:
            recent_high = max(b[2] for b in bars)  # high prices
            print(f"      Recent high: {recent_high}")
            print(f"      Current close: {bar3['close']}")
            print(f"      EMA(5) on low: {ema_rows[0]['value']}")
    
    # Check database status
    print("\n5️⃣ Final status...")
    stats = get_stats()
    print(f"   📊 Tokens: {stats['total']}")
    
    print(f"\n✅ Strategy trigger test finished!")
    
    # Shutdown
    print(f"\n🔄 Shutting down...")
    shutdown()
    print(f"   ✅ Done")

if __name__ == "__main__":
    try:
        test_strategy_trigger()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown()
