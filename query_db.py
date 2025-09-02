#!/usr/bin/env python3
"""
Database Query Tool for Solana Memecoin Sniper
Use this to query stored tokens without stopping the main monitor
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot.db import get_stats, get_recent_tokens, get_tokens_by_risk, get_token_by_address

def main():
    print("🔍 SOLANA MEMECOIN SNIPER - DATABASE QUERY TOOL")
    print("=" * 60)
    
    # Show overall stats
    stats = get_stats()
    print(f"📊 DATABASE OVERVIEW:")
    print(f"   Total tokens: {stats['total']}")
    print(f"   🟢 Low risk (0-10): {stats['low_risk_0_10']}")
    print(f"   🟡 Medium risk (11-20): {stats['medium_risk_11_20']}")
    print(f"   🔴 High risk (21+): {stats['high_risk_21_plus']}")
    
    if stats['total'] == 0:
        print("\n📭 No tokens found in database")
        return
    
    print(f"\n🕐 RECENT TOKENS (Last 24h):")
    print("-" * 80)
    print(f"{'Name':<25} {'Symbol':<12} {'Risk':<6} {'DEX':<15} {'Mint':<20}")
    print("-" * 80)
    
    recent = get_recent_tokens(hours=24, limit=20)
    for token in recent:
        name = token[1][:24] if token[1] else "Unknown"
        symbol = token[2][:11] if token[2] else ""
        risk = str(token[4]) if token[4] else "N/A"
        dex = token[3][:14] if token[3] else ""
        mint = token[0][:19] if token[0] else ""
        
        # Add risk emoji
        risk_emoji = "🟢" if token[4] <= 10 else "🟡" if token[4] <= 20 else "🔴"
        print(f"{risk_emoji} {name:<25} {symbol:<12} {risk:<6} {dex:<15} {mint:<20}")
    
    print(f"\n💡 TIP: Use 'kill -USR1 <PID>' to show database summary while monitoring")
    print(f"   Replace <PID> with the process ID of your running new_pairs.py script")

if __name__ == "__main__":
    main()
