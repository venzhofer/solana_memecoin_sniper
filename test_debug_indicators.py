#!/usr/bin/env python3
"""
Debug Indicators Test - See what's being passed to strategies
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

def test_debug_indicators():
    """Test to debug indicator passing."""
    print("🔍 DEBUG INDICATORS TEST")
    print("=" * 50)
    
    # Load strategies
    print("\n1️⃣ Loading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Create token
    print("\n2️⃣ Creating test token...")
    token = {
        "address": "debug_token",
        "name": "Debug Token",
        "symbol": "DEBUG",
        "dex": "Raydium",
        "risk": 10,
        "signature": "sig_debug",
        "rc": {"score": 10, "details": "test"}
    }
    
    upsert_safe_token(**token)
    dispatch_new_token(token)
    print(f"   ✅ Token created: {token['name']} ({token['symbol']})")
    
    # Create one bar and check indicators
    print("\n3️⃣ Creating bar and checking indicators...")
    timestamp = int(time.time())
    
    bar = {
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
    
    print(f"   📊 Bar: O:{bar['open']} H:{bar['high']} L:{bar['low']} C:{bar['close']}")
    
    # Calculate indicators
    print("\n4️⃣ Calculating indicators...")
    ema_rows, atr_rows = update_all_for_bar(bar)
    
    print(f"   📊 EMA rows: {len(ema_rows)}")
    for i, ema in enumerate(ema_rows):
        print(f"      EMA[{i}]: {ema}")
    
    print(f"   📊 ATR rows: {len(atr_rows)}")
    for i, atr in enumerate(atr_rows):
        print(f"      ATR[{i}]: {atr}")
    
    # Store indicators
    insert_ema_1m(ema_rows)
    insert_atr_1m(atr_rows)
    
    # Check what's in database
    print("\n5️⃣ Checking database...")
    from db import get_ema_1m, get_atr_1m
    
    db_emas = get_ema_1m(token["address"], 10)
    print(f"   📊 EMAs in DB: {len(db_emas)}")
    for ema in db_emas:
        print(f"      DB EMA: {ema}")
    
    db_atrs = get_atr_1m(token["address"], 10)
    print(f"   📊 ATRs in DB: {len(db_atrs)}")
    for atr in db_atrs:
        print(f"      DB ATR: {atr}")
    
    # Test strategy dispatch
    print("\n6️⃣ Testing strategy dispatch...")
    dispatch_bar_1m(bar, ema_rows, atr_rows)
    
    print(f"\n✅ Debug indicators test finished!")
    
    # Shutdown
    print(f"\n🔄 Shutting down...")
    shutdown()
    print(f"   ✅ Done")

if __name__ == "__main__":
    try:
        test_debug_indicators()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        shutdown()
