#!/usr/bin/env python3
"""
Real-time OHLC Monitoring Script
"""

import time
import sys
import os
sys.path.append('.')

from ohlc_agg import _buffers
from db import get_ohlc_1m, list_all_addresses

def show_buffer_status():
    if not _buffers:
        print("📭 No active OHLC buffers")
        return
    
    for address, buf in _buffers.items():
        current_samples = len(buf.samples)
        progress = (current_samples / 30) * 100
        remaining = 30 - current_samples
        
        bar_length = 20
        filled = int((progress / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(f"📍 {address}")
        print(f"   📊 [{bar}] {progress:.1f}% ({current_samples}/30)")
        print(f"   ⏳ Remaining: {remaining} samples")
        if buf.samples:
            latest_price = buf.samples[-1][1] if buf.samples[-1][1] else "N/A"
            print(f"   💰 Latest Price: ${latest_price}")
        print()

def main():
    print("🔍 REAL-TIME OHLC MONITORING")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            os.system('clear')
            print("🔍 REAL-TIME OHLC MONITORING")
            print("=" * 60)
            print(f"⏰ Last Update: {time.strftime('%H:%M:%S')}")
            print()
            
            print("🔄 ACTIVE OHLC BUFFERS:")
            print("-" * 40)
            show_buffer_status()
            
            print("📈 MONITORING INFO:")
            print("-" * 40)
            print("• OHLC bars created every 30 price samples")
            print("• Progress shown every 5 samples")
            print("• Database updated automatically")
            print()
            print("🔄 Refreshing in 2 seconds...")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped")
        show_buffer_status()

if __name__ == "__main__":
    main()
