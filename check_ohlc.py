#!/usr/bin/env python3
"""
Simple script to check OHLC data in database
"""

import sys
sys.path.append('.')

from trading_bot.db import get_ohlc_1m, DB

def check_ohlc():
    """Check what OHLC data exists."""
    print("🔍 Checking OHLC data in database...")
    
    # Check for our test token
    test_addr = "test_token_indicators"
    bars = get_ohlc_1m(test_addr, limit=10)
    
    if bars:
        print(f"✅ Found {len(bars)} OHLC bars for {test_addr}")
        for i, bar in enumerate(bars):
            ts_start, o, h, l, c, fdv, mc, samples = bar
            print(f"  Bar {i+1}: {ts_start} O:{o:.3f} H:{h:.3f} L:{l:.3f} C:{c:.3f}")
    else:
        print(f"❌ No OHLC bars found for {test_addr}")
    
    # Check for any other tokens
    print("\n🔍 Checking for any OHLC data...")
    try:
        cursor = DB.execute("SELECT address, COUNT(*) FROM ohlc_1m GROUP BY address")
        results = cursor.fetchall()

        if results:
            print("📊 OHLC data found:")
            for addr, count in results:
                print(f"  {addr}: {count} bars")
        else:
            print("📭 No OHLC data found in database")
    except Exception as e:
        print(f"❌ Error querying database: {e}")

if __name__ == "__main__":
    check_ohlc()
