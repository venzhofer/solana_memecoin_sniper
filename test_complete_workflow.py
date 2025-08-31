#!/usr/bin/env python3
"""
COMPLETE MEMECOIN SNIPER WORKFLOW TEST
=======================================
This test simulates the entire system:
1. New memecoin appears
2. Database storage
3. Price monitoring
4. OHLC creation
5. Technical indicators
6. Strategy evaluation
7. Paper trading execution
"""

import os
import time
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from db import upsert_safe_token, count_tokens, get_tokens_by_risk
from indicators import update_all_for_bar, EMA_LENGTHS, EMA_SOURCE, ATR_LENGTHS
from papertrading import load_strategies, dispatch_new_token, dispatch_bar_1m, shutdown
from papertrading.db import get_watchable_addresses, pos_get, trade_log

def simulate_new_memecoin():
    """Simulate a new memecoin appearing"""
    print("🎯 STEP 1: SIMULATING NEW MEMECOIN")
    print("=" * 50)
    
    # Simulate memecoin data
    memecoin = {
        "address": "TEST123456789abcdefghijklmnopqrstuvwxyz",
        "name": "TestMoonCoin",
        "symbol": "TMC",
        "dex": "pumpswap",
        "risk": 0,
        "signature": "test_signature_123",
        "rc": {"risk": 0, "summary": "Test coin"}
    }
    
    print(f"🆕 New memecoin detected:")
    print(f"   Name: {memecoin['name']} ({memecoin['symbol']})")
    print(f"   Address: {memecoin['address']}")
    print(f"   DEX: {memecoin['dex']}")
    print(f"   Risk: {memecoin['risk']}")
    
    # Store in database
    upsert_safe_token(**memecoin)
    print(f"💾 Stored in database")
    
    # Check database
    total = count_tokens()
    print(f"📊 Database now has {total} tokens")
    
    return memecoin

def simulate_price_data(address, base_price=0.001):
    """Simulate price data for the memecoin"""
    print(f"\n💰 STEP 2: SIMULATING PRICE DATA")
    print("=" * 50)
    
    # Simulate price movement (breakout pattern)
    prices = []
    base_time = int(time.time())
    
    # Create 10 price samples (enough for OHLC + indicators)
    for i in range(10):
        # Simulate price increase with some volatility
        if i < 3:
            # First 3 bars: sideways
            price = base_price * (1 + (i * 0.1))
        elif i < 6:
            # Next 3 bars: breakout
            price = base_price * (1.5 + (i * 0.3))
        else:
            # Last 4 bars: momentum
            price = base_price * (2.5 + (i * 0.2))
        
        # Add some volatility
        price *= (1 + (i * 0.05))
        
        # Create OHLC bar
        high = price * 1.1
        low = price * 0.9
        open_price = price * 0.95
        close_price = price
        
        bar = {
            "address": address,
            "ts_start": base_time + (i * 60),  # 1-minute intervals
            "open": open_price,
            "high": high,
            "low": low,
            "close": close_price,
            "volume": 1000000 + (i * 100000),
            "fdv_usd": 1000000 + (i * 100000),
            "marketcap_usd": 500000 + (i * 50000),
            "samples": 30
        }
        
        prices.append(bar)
        print(f"   Bar {i+1}: O:{open_price:.6f} H:{high:.6f} L:{low:.6f} C:{close_price:.6f}")
    
    return prices

def test_ohlc_and_indicators(address, prices):
    """Test OHLC creation and technical indicators"""
    print(f"\n📊 STEP 3: TESTING OHLC & INDICATORS")
    print("=" * 50)
    
    print(f"📈 Processing {len(prices)} price bars...")
    
    # Process each bar through indicators
    for i, bar in enumerate(prices):
        print(f"\n   Processing bar {i+1}:")
        print(f"     Time: {datetime.fromtimestamp(bar['ts_start']).strftime('%H:%M:%S')}")
        print(f"     Price: ${bar['close']:.6f}")
        
        # Update indicators
        ema_rows, atr_rows = update_all_for_bar(bar)
        
        # Show indicator values
        if ema_rows:
            for ema in ema_rows:
                print(f"     EMA({ema['length']}) {ema['source']}: {ema['value']:.6f}")
        
        if atr_rows:
            for atr in atr_rows:
                print(f"     ATR({atr['length']}): {atr['value']:.6f}")
    
    return prices

def test_strategy_execution(address, prices):
    """Test strategy evaluation and paper trading"""
    print(f"\n🎯 STEP 4: TESTING STRATEGY EXECUTION")
    print("=" * 50)
    
    # Load strategies
    strategies = load_strategies()
    print(f"📋 Loaded {len(strategies)} strategies")
    
    # Process bars through strategy
    for i, bar in enumerate(prices):
        print(f"\n   Strategy evaluating bar {i+1}:")
        
        # Get indicators for this bar
        ema_rows, atr_rows = update_all_for_bar(bar)
        
        # Dispatch to strategy
        dispatch_bar_1m(bar, ema_rows, atr_rows)
        
        # Check if position was opened
        position = pos_get(address)
        if position and position[1] == "long":
            print(f"     🚀 POSITION OPENED!")
            print(f"        Entry: ${position[3]:.6f}")
            print(f"        Stop: ${position[4]:.6f}")
            break
        elif position:
            print(f"     📊 Position status: {position[1]}")
        else:
            print(f"     ⏳ No position yet")
    
    # Check final position
    final_position = pos_get(address)
    if final_position:
        print(f"\n📊 FINAL POSITION STATUS:")
        print(f"   Status: {final_position[1]}")
        print(f"   Entry Price: ${final_position[3]:.6f}")
        print(f"   Stop Price: ${final_position[4]:.6f}")
        print(f"   High Since Entry: ${final_position[6]:.6f}")
    else:
        print(f"\n❌ No position opened")

def test_database_persistence():
    """Test that data persists in the database"""
    print(f"\n💾 STEP 5: TESTING DATABASE PERSISTENCE")
    print("=" * 50)
    
    # Check tokens
    total = count_tokens()
    print(f"📊 Total tokens in database: {total}")
    
    if total > 0:
        tokens = get_tokens_by_risk(20, 10)
        print(f"🔍 Recent tokens:")
        for token in tokens:
            print(f"   {token[1]} ({token[2]}) - {token[4]} risk")
    
    # Check watchable addresses
    watchable = get_watchable_addresses(10)
    print(f"👀 Watchable addresses: {len(watchable)}")
    
    # Check positions
    from papertrading.db import DB
    positions = DB.execute("SELECT COUNT(*) FROM paper_positions").fetchone()[0]
    print(f"📈 Paper positions: {positions}")
    
    trades = DB.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]
    print(f"💰 Paper trades: {trades}")

def main():
    """Run the complete workflow test"""
    print("🚀 COMPLETE MEMECOIN SNIPER WORKFLOW TEST")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 EMA Lengths: {EMA_LENGTHS}")
    print(f"📊 EMA Source: {EMA_SOURCE}")
    print(f"📊 ATR Lengths: {ATR_LENGTHS}")
    print("=" * 60)
    
    try:
        # Step 1: Simulate new memecoin
        memecoin = simulate_new_memecoin()
        
        # Step 2: Simulate price data
        prices = simulate_price_data(memecoin['address'])
        
        # Step 3: Test OHLC and indicators
        test_ohlc_and_indicators(memecoin['address'], prices)
        
        # Step 4: Test strategy execution
        test_strategy_execution(memecoin['address'], prices)
        
        # Step 5: Test database persistence
        test_database_persistence()
        
        print(f"\n🎉 COMPLETE WORKFLOW TEST FINISHED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        shutdown()
        print(f"\n🧹 Cleanup completed")

if __name__ == "__main__":
    main()
