#!/usr/bin/env python3
"""
Complete test script that tests OHLC, indicators, and database in one run
"""

import sys
sys.path.append('.')

from trading_bot.indicators import update_all_for_bar, EMA_LENGTHS, EMA_SOURCE, ATR_LENGTHS
from trading_bot.db import insert_ohlc_1m, insert_ema_1m, insert_atr_1m, get_ohlc_1m, get_ema_1m, get_atr_1m

def test_complete():
    """Test the complete system in one run."""
    print("🧪 Testing Complete System (OHLC + Indicators + Database)")
    print("=" * 70)
    
    # Show configuration
    print(f"📊 Configuration:")
    print(f"   EMA lengths: {EMA_LENGTHS}")
    print(f"   EMA source: {EMA_SOURCE}")
    print(f"   ATR lengths: {ATR_LENGTHS}")
    print()
    
    # Test token
    test_addr = "test_token_complete"
    
    # Simulate OHLC bars
    bars = [
        {"address": test_addr, "ts_start": 1000, "open": 1.0, "high": 1.1, "low": 0.95, "close": 1.05, "fdv_usd": 1000000, "marketcap_usd": 500000, "samples": 30},
        {"address": test_addr, "ts_start": 1060, "open": 1.05, "high": 1.15, "low": 1.0, "close": 1.1, "fdv_usd": 1100000, "marketcap_usd": 550000, "samples": 30},
        {"address": test_addr, "ts_start": 1120, "open": 1.1, "high": 1.2, "low": 1.05, "close": 1.15, "fdv_usd": 1200000, "marketcap_usd": 600000, "samples": 30},
    ]
    
    print(f"📈 Processing {len(bars)} OHLC bars...")
    
    for i, bar in enumerate(bars):
        print(f"\n🔄 Processing bar {i+1}: O:{bar['open']:.3f} H:{bar['high']:.3f} L:{bar['low']:.3f} C:{bar['close']:.3f}")
        
        # Store OHLC
        insert_ohlc_1m(bar)
        print(f"   💾 OHLC stored")
        
        # Calculate indicators
        ema_rows, atr_rows = update_all_for_bar(bar)
        print(f"   📊 EMAs calculated: {len(ema_rows)}")
        print(f"   📊 ATRs calculated: {len(atr_rows)}")
        
        # Store indicators
        insert_ema_1m(ema_rows)
        insert_atr_1m(atr_rows)
        print(f"   💾 Indicators stored")
        
        # Show current values
        for ema_row in ema_rows:
            print(f"      EMA({ema_row['length']}): {ema_row['value']:.6f}")
        for atr_row in atr_rows:
            print(f"      ATR({atr_row['length']}): {atr_row['value']:.6f}")
    
    # Verify database storage
    print(f"\n🔍 Verifying database storage...")
    
    # Check OHLC
    ohlc_data = get_ohlc_1m(test_addr, limit=10)
    print(f"   OHLC: {len(ohlc_data)} bars stored")
    if ohlc_data:
        for i, bar in enumerate(ohlc_data):
            ts_start, o, h, l, c, fdv, mc, samples = bar
            print(f"      Bar {i+1}: {ts_start} O:{o:.3f} H:{h:.3f} L:{l:.3f} C:{c:.3f}")
    
    # Check EMAs
    for length in EMA_LENGTHS:
        ema_data = get_ema_1m(test_addr, length, limit=10)
        print(f"   EMA({length}): {len(ema_data)} values stored")
        if ema_data:
            latest = ema_data[0]
            print(f"      Latest: {latest[1]:.6f}")
    
    # Check ATRs
    for length in ATR_LENGTHS:
        atr_data = get_atr_1m(test_addr, length, limit=10)
        print(f"   ATR({length}): {len(atr_data)} values stored")
        if atr_data:
            latest = atr_data[0]
            print(f"      Latest: {latest[1]:.6f}")
    
    print(f"\n✅ Complete system test completed!")
    
    # Test the peek script functionality
    print(f"\n🔍 Testing peek functionality...")
    print(f"Token: {test_addr}")
    print(f"EMA lengths={EMA_LENGTHS} source={EMA_SOURCE} | ATR lengths={ATR_LENGTHS}")
    
    if ohlc_data:
        print(f"Found {len(ohlc_data)} OHLC bars:")
        for ts_start, o, h, l, c, *_ in reversed(ohlc_data):
            from time import gmtime, strftime
            t = strftime("%Y-%m-%d %H:%M:%S", gmtime(int(ts_start)))
            print(f"{t}Z  O:{o:.3f} H:{h:.3f} L:{l:.3f} C:{c:.3f}")
    else:
        print("No 1m bars yet.")

if __name__ == "__main__":
    test_complete()
