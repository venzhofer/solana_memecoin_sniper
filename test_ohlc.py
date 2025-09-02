#!/usr/bin/env python3
"""
Test script to verify OHLC aggregation system
"""

import time
import sys
sys.path.append('.')

from trading_bot.ohlc_agg import add_sample
from trading_bot.db import insert_ohlc_1m, get_ohlc_1m

def test_ohlc_aggregation():
    """Test the OHLC aggregation system with sample data."""
    print("🧪 Testing OHLC Aggregation System")
    print("=" * 50)
    
    # Test token address
    test_addr = "test_token_123"
    
    # Simulate 35 price samples (should create 1 complete bar)
    print(f"📊 Adding 35 price samples for {test_addr}...")
    
    base_price = 1.0
    for i in range(35):
        # Vary the price slightly
        price = base_price + (i * 0.01) + (0.1 if i % 5 == 0 else 0)
        fdv = 1000000 + (i * 10000)
        mc = 500000 + (i * 5000)
        ts = time.time() + i
        
        # Add sample
        bar = add_sample(
            test_addr,
            price=price,
            fdv=fdv,
            mc=mc,
            ts=ts
        )
        
        if bar:
            print(f"✅ Created OHLC bar at {time.strftime('%H:%M:%S', time.gmtime(bar['ts_start']))}")
            print(f"   O:{bar['open']:.4f} H:{bar['high']:.4f} L:{bar['low']:.4f} C:{bar['close']:.4f}")
            print(f"   FDV: ${bar['fdv_usd']:,.0f} | MC: ${bar['marketcap_usd']:,.0f}")
            print(f"   Samples: {bar['samples']}")
            print("-" * 30)
            
            # Store in database
            insert_ohlc_1m(bar)
    
    # Check database
    print(f"\n📊 Checking database for {test_addr}...")
    bars = get_ohlc_1m(test_addr, limit=5)
    
    if bars:
        print(f"Found {len(bars)} OHLC bars in database:")
        for ts_start, o, h, l, c, fdv, mc, n in bars:
            t = time.strftime("%H:%M:%S", time.gmtime(ts_start))
            print(f"  {t}Z  O:{o:.4f} H:{h:.4f} L:{l:.4f} C:{c:.4f}  FDV:${fdv:,.0f}  MC:${mc:,.0f}  n={n}")
    else:
        print("❌ No OHLC bars found in database")
    
    print("\n✅ OHLC test completed!")

if __name__ == "__main__":
    test_ohlc_aggregation()
