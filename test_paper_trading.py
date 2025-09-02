#!/usr/bin/env python3
"""
Test script to verify the complete paper trading system
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append('.')

from trading_bot.papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from trading_bot.indicators import update_all_for_bar, EMA_LENGTHS, EMA_SOURCE, ATR_LENGTHS
from trading_bot.db import insert_ohlc_1m, insert_ema_1m, insert_atr_1m, upsert_safe_token

def test_paper_trading():
    """Test the complete paper trading system."""
    print("🧪 Testing Complete Paper Trading System")
    print("=" * 70)
    
    # Show configuration
    print(f"📊 Configuration:")
    print(f"   EMA lengths: {EMA_LENGTHS}")
    print(f"   EMA source: {EMA_SOURCE}")
    print(f"   ATR lengths: {ATR_LENGTHS}")
    print(f"   Paper strategies: {os.getenv('PAPER_STRATEGIES')}")
    print(f"   Lookback bars: {os.getenv('LOOKBACK_BREAKOUT_BARS')}")
    print(f"   ATR stop mult: {os.getenv('ATR_STOP_MULT')}")
    print(f"   Trail percent: {os.getenv('TRAIL_PCT')}")
    print()
    
    # Test token
    test_addr = "test_token_paper"
    
    # Load strategies
    print("🔄 Loading paper trading strategies...")
    strategies = load_strategies()
    print(f"   Loaded {len(strategies)} strategies")
    
    # Simulate new token
    print(f"\n🆕 Simulating new token: {test_addr}")
    token_data = {
        "address": test_addr,
        "name": "Test Token",
        "symbol": "TEST",
        "dex": "Raydium",
        "risk": 15,
        "signature": "test_sig_123"
    }
    
    # Store token in database
    upsert_safe_token(**token_data)
    print(f"   💾 Token stored in database")
    
    # Notify strategies
    dispatch_new_token(token_data)
    print(f"   📢 Strategies notified of new token")
    
    # Simulate OHLC bars
    bars = [
        {"address": test_addr, "ts_start": 1000, "open": 1.0, "high": 1.1, "low": 0.95, "close": 1.05, "fdv_usd": 1000000, "marketcap_usd": 500000, "samples": 30},
        {"address": test_addr, "ts_start": 1060, "open": 1.05, "high": 1.15, "low": 1.0, "close": 1.1, "fdv_usd": 1100000, "marketcap_usd": 550000, "samples": 30},
        {"address": test_addr, "ts_start": 1120, "open": 1.1, "high": 1.2, "low": 1.05, "close": 1.15, "fdv_usd": 1200000, "marketcap_usd": 600000, "samples": 30},
    ]
    
    print(f"\n📈 Processing {len(bars)} OHLC bars...")
    
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
        
        # Notify strategies
        dispatch_bar_1m(bar, ema_rows, atr_rows)
        print(f"   📢 Strategies notified of new bar")
        
        # Show current values
        for ema_row in ema_rows:
            print(f"      EMA({ema_row['length']}): {ema_row['value']:.6f}")
        for atr_row in atr_rows:
            print(f"      ATR({atr_row['length']}): {atr_row['value']:.6f}")
    
    print(f"\n✅ Paper trading system test completed!")
    
    # Shutdown strategies
    print(f"\n🔄 Shutting down strategies...")
    shutdown()
    print(f"   ✅ Strategies shut down")

if __name__ == "__main__":
    test_paper_trading()
