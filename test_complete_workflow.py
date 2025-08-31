#!/usr/bin/env python3
"""
Complete Paper Trading Workflow Test
Tests the entire system from token discovery to trade execution
"""

import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from indicators import update_all_for_bar, reset_indicators
from db import (
    upsert_safe_token, insert_ohlc_1m, insert_ema_1m, insert_atr_1m,
    count_tokens, get_stats
)

def test_complete_workflow():
    """Test the complete paper trading workflow."""
    print("🚀 COMPLETE PAPER TRADING WORKFLOW TEST")
    print("=" * 70)
    
    # Step 1: Load strategies
    print("\n1️⃣ Loading paper trading strategies...")
    strategies = load_strategies()
    print(f"   ✅ Loaded {len(strategies)} strategies")
    
    # Step 2: Simulate token discovery
    print("\n2️⃣ Simulating token discovery...")
    test_tokens = [
        {
            "address": "token_001",
            "name": "Test Token Alpha",
            "symbol": "ALPHA",
            "dex": "Raydium",
            "risk": 12,
            "signature": "sig_001",
            "rc": {"score": 12, "details": "test"}
        },
        {
            "address": "token_002", 
            "name": "Test Token Beta",
            "symbol": "BETA",
            "dex": "Raydium",
            "risk": 8,
            "signature": "sig_002",
            "rc": {"score": 8, "details": "test"}
        }
    ]
    
    for token in test_tokens:
        print(f"   🆕 Discovering: {token['name']} ({token['symbol']}) - Risk: {token['risk']}")
        upsert_safe_token(**token)
        dispatch_new_token(token)
        print(f"   ✅ Token stored and strategies notified")
    
    # Step 3: Check database status
    print("\n3️⃣ Checking database status...")
    stats = get_stats()
    print(f"   📊 Total tokens: {stats['total']}")
    print(f"   📊 Low risk (0-10): {stats['low_risk_0_10']}")
    print(f"   📊 Medium risk (11-20): {stats['medium_risk_11_20']}")
    
    # Step 4: Simulate price data and OHLC creation
    print("\n4️⃣ Simulating price data and OHLC creation...")
    
    for token in test_tokens:
        addr = token["address"]
        print(f"\n   📈 Processing {token['name']} ({token['symbol']})...")
        
        # Generate realistic price movement
        base_price = 1.0
        timestamp = int(time.time())
        
        for i in range(5):  # 5 OHLC bars
            # Price movement
            change = random.uniform(-0.03, 0.05)  # -3% to +5%
            base_price *= (1 + change)
            
            # Create OHLC bar
            high = base_price * random.uniform(1.0, 1.08)
            low = base_price * random.uniform(0.92, 1.0)
            open_price = base_price
            close_price = base_price * (1 + random.uniform(-0.02, 0.03))
            
            bar = {
                "address": addr,
                "ts_start": timestamp + (i * 60),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "fdv_usd": 1000000 * (1 + i * 0.1),
                "marketcap_usd": 500000 * (1 + i * 0.1),
                "samples": 30
            }
            
            print(f"      Bar {i+1}: O:{open_price:.4f} H:{high:.4f} L:{low:.4f} C:{close_price:.4f}")
            
            # Store OHLC
            insert_ohlc_1m(bar)
            
            # Calculate indicators
            ema_rows, atr_rows = update_all_for_bar(bar)
            insert_ema_1m(ema_rows)
            insert_atr_1m(atr_rows)
            
            # Notify strategies with market cap
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
            
            print(f"      📊 Indicators: {len(ema_rows)} EMAs, {len(atr_rows)} ATRs")
            
            # Show current values
            for ema_row in ema_rows:
                print(f"         EMA({ema_row['length']}): {ema_row['value']:.6f}")
            for atr_row in atr_rows:
                print(f"         ATR({atr_row['length']}): {atr_row['value']:.6f}")
            
            time.sleep(0.1)  # Small delay for readability
    
    # Step 5: Check paper trading positions
    print("\n5️⃣ Checking paper trading positions...")
    from papertrading.db import get_watchable_addresses, pos_get
    
    watchable = get_watchable_addresses()
    print(f"   📊 Watchable addresses: {len(watchable)}")
    
    for addr in watchable:
        pos = pos_get(addr)
        if pos:
            print(f"   📈 Position for {addr}: {pos}")
        else:
            print(f"   ⚪ No position for {addr}")
    
    # Step 6: Final status
    print("\n6️⃣ Final system status...")
    final_stats = get_stats()
    print(f"   📊 Final tokens: {final_stats['total']}")
    print(f"   📊 Low risk: {final_stats['low_risk_0_10']}")
    print(f"   📊 Medium risk: {final_stats['medium_risk_11_20']}")
    
    print(f"\n✅ Complete workflow test finished!")
    
    # Shutdown strategies
    print(f"\n🔄 Shutting down strategies...")
    shutdown()
    print(f"   ✅ Strategies shut down")

if __name__ == "__main__":
    try:
        test_complete_workflow()
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        shutdown()
