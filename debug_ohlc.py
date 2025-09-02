#!/usr/bin/env python3
"""
OHLC Debugging and Monitoring Script
Shows real-time OHLC creation progress and detailed analytics
"""

import time
import sys
sys.path.append('.')

from trading_bot.ohlc_agg import add_sample, _buffers
from trading_bot.db import insert_ohlc_1m, get_ohlc_1m, list_all_addresses

def show_buffer_status():
    """Show current status of all OHLC buffers."""
    print("\n🔍 CURRENT OHLC BUFFER STATUS:")
    print("=" * 60)
    
    if not _buffers:
        print("📭 No active OHLC buffers")
        return
    
    for address, buf in _buffers.items():
        current_samples = len(buf.samples)
        progress = (current_samples / 30) * 100
        remaining = 30 - current_samples
        
        print(f"📍 {address}:")
        print(f"   📊 Progress: {current_samples}/30 samples ({progress:.1f}%)")
        print(f"   ⏳ Remaining: {remaining} samples")
        if buf.samples:
            latest_price = buf.samples[-1][1] if buf.samples[-1][1] else "N/A"
            print(f"   💰 Latest Price: {latest_price}")
        print()

def simulate_price_data(token_address: str, num_samples: int = 35):
    """Simulate price data to test OHLC creation."""
    print(f"🧪 SIMULATING {num_samples} PRICE SAMPLES FOR {token_address}")
    print("=" * 60)
    
    base_price = 1.0
    bars_created = 0
    
    for i in range(num_samples):
        # Vary the price with some volatility
        volatility = 0.02  # 2% volatility
        price = base_price * (1 + (i * 0.01) + (volatility if i % 3 == 0 else 0))
        fdv = 1000000 + (i * 10000)
        mc = 500000 + (i * 5000)
        ts = time.time() + i
        
        print(f"📈 Sample {i+1:2d}: Price=${price:.6f}, FDV=${fdv:,.0f}, MC=${mc:,.0f}")
        
        # Add sample to OHLC aggregator
        bar = add_sample(
            token_address,
            price=price,
            fdv=fdv,
            mc=mc,
            ts=ts
        )
        
        if bar:
            bars_created += 1
            print(f"🎉 OHLC BAR #{bars_created} CREATED!")
            
            # Store in database
            insert_ohlc_1m(bar)
            print(f"💾 Stored in database")
        
        # Show buffer status every 10 samples
        if (i + 1) % 10 == 0:
            show_buffer_status()
        
        time.sleep(0.1)  # Small delay to see progress
    
    return bars_created

def show_database_ohlc(token_address: str):
    """Show OHLC data stored in database."""
    print(f"\n📊 DATABASE OHLC DATA FOR {token_address}:")
    print("=" * 60)
    
    bars = get_ohlc_1m(token_address, limit=10)
    if bars:
        print(f"Found {len(bars)} OHLC bars:")
        print(f"{'Time':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'FDV':<15} {'MC':<15} {'Samples':<8}")
        print("-" * 100)
        
        for ts_start, o, h, l, c, fdv, mc, n in bars:
            t = time.strftime("%H:%M:%S", time.gmtime(ts_start))
            fdv_str = f"${fdv:,.0f}" if fdv else "N/A"
            mc_str = f"${mc:,.0f}" if mc else "N/A"
            print(f"{t:<12} {o:<10.6f} {h:<10.6f} {l:<10.6f} {c:<10.6f} {fdv_str:<15} {mc_str:<15} {n:<8}")
    else:
        print("❌ No OHLC bars found in database")

def main():
    """Main debugging interface."""
    print("🔍 OHLC DEBUGGING AND MONITORING TOOL")
    print("=" * 60)
    
    # Show current database status
    addresses = list_all_addresses()
    print(f"📊 Database has {len(addresses)} token addresses")
    
    if addresses:
        print("Available tokens:")
        for addr in addresses[:5]:  # Show first 5
            print(f"  • {addr}")
        if len(addresses) > 5:
            print(f"  ... and {len(addresses) - 5} more")
    else:
        print("📭 No tokens in database - using test token")
    
    # Use first available token or test token
    test_token = addresses[0] if addresses else "test_token_debug"
    
    print(f"\n🎯 Testing with token: {test_token}")
    
    # Show initial buffer status
    show_buffer_status()
    
    # Simulate price data
    bars_created = simulate_price_data(test_token, 35)
    
    # Show final results
    print(f"\n✅ SIMULATION COMPLETE!")
    print(f"📊 Created {bars_created} OHLC bars")
    
    # Show final buffer status
    show_buffer_status()
    
    # Show database contents
    show_database_ohlc(test_token)
    
    print("\n🎉 OHLC debugging session completed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Debugging interrupted by user")
        show_buffer_status()
