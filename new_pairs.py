import asyncio, json, os, sys, signal
from dotenv import load_dotenv
import websockets
from rugcheck_client import get_risk_level
from db import (
    upsert_safe_token, count_tokens, get_stats,
    get_recent_tokens, get_tokens_by_risk, clear_old_tokens
)
from price_watcher import watch_prices
from papertrading import load_strategies, dispatch_new_token, is_blacklisted

load_dotenv()
API_KEY = os.getenv("SOLANASTREAM_API_KEY")
if not API_KEY:
    print("Missing SOLANASTREAM_API_KEY in .env")
    sys.exit(1)

SKIP_RISK_CHECK = os.getenv("SKIP_RISK_CHECK", "0") == "1"

# Signal handler for database queries
def signal_handler(signum, frame):
    """Handle SIGUSR1 to show database summary."""
    if signum == signal.SIGUSR1:
        show_database_summary()

# Register signal handler
signal.signal(signal.SIGUSR1, signal_handler)

URL = "wss://api.solanastreaming.com"
MSG = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "newPairSubscribe",
    "params": {"include_pumpfun": True, "api_key": API_KEY}
}

async def send_heartbeat(ws):
    """Optional app-level heartbeat (JSON message)."""
    while True:
        try:
            await asyncio.sleep(30)
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 999, "method": "heartbeat"}))
        except Exception as e:
            print(f"[heartbeat] Error: {e}")
            break

async def periodic_maintenance():
    """Perform periodic database maintenance and show stats."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # Clean old tokens (older than 7 days)
            old_count = count_tokens()
            clear_old_tokens(days=7)
            new_count = count_tokens()
            
            if old_count != new_count:
                print(f"🧹 Cleaned {old_count - new_count} old tokens from database")
            
            # Show periodic stats
            stats = get_stats()
            print(f"📊 Periodic Stats - Total: {stats['total']} | Low: {stats['low_risk_0_10']} | Med: {stats['medium_risk_11_20']} | High: {stats['high_risk_21_plus']}")
            
        except Exception as e:
            print(f"[maintenance] Error: {e}")
            continue

def show_database_summary():
    """Show a comprehensive database summary."""
    stats = get_stats()
    print(f"\n📊 DATABASE SUMMARY")
    print("=" * 50)
    print(f"Total tokens stored: {stats['total']}")
    print(f"🟢 Low risk (0-10): {stats['low_risk_0_10']}")
    print(f"🟡 Medium risk (11-20): {stats['medium_risk_11_20']}")
    print(f"🔴 High risk (21+): {stats['high_risk_21_plus']}")
    
    if stats['total'] > 0:
        print(f"\n🕐 Recent tokens (last 24h):")
        recent = get_recent_tokens(hours=24, limit=5)
        for i, token in enumerate(recent, 1):
            risk_emoji = "🟢" if token[4] <= 10 else "🟡" if token[4] <= 20 else "🔴"
            print(f"  {i}. {risk_emoji} {token[1]} ({token[2]}) - Risk: {token[4]} - DEX: {token[3]}")
    
    print("=" * 50)

def show_recent_tokens():
    """Display recent tokens from database."""
    recent = get_recent_tokens(hours=24, limit=10)
    if recent:
        print(f"\n🕐 RECENT TOKENS (Last 24h):")
        print("-" * 80)
        print(f"{'Name':<20} {'Symbol':<10} {'Risk':<6} {'DEX':<12} {'Mint':<15}")
        print("-" * 80)
        for token in recent:
            name = token[1][:19] if token[1] else "Unknown"
            symbol = token[2][:9] if token[2] else ""
            risk = str(token[4]) if token[4] else "N/A"
            dex = token[3][:11] if token[3] else ""
            mint = token[0][:14] if token[0] else ""
            print(f"{name:<20} {symbol:<10} {risk:<6} {dex:<12} {mint:<15}")
    else:
        print("📭 No recent tokens found in database")

async def handle_connection(ws):
    """Handle the websocket connection and message processing."""
    print("[ws] connected")
    await ws.send(json.dumps(MSG))
    print("[ws] subscribed to new pairs")

    heartbeat_task = asyncio.create_task(send_heartbeat(ws))

    try:
        message_count = 0
        async for raw in ws:
            message_count += 1

            try:
                msg = json.loads(raw)

                if msg.get("method") == "ping":
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": "pong"}))
                    continue
            except json.JSONDecodeError as e:
                print(f"[ws] JSON decode error: {e} -> {raw[:200]!r}")
                continue
            except Exception as e:
                print(f"[ws] error parsing message: {e} -> {raw[:200]!r}")
                continue

            try:
                if msg.get("method") == "newPairNotification" and msg.get("params"):
                    params = msg["params"]
                    signature = params.get("signature", "")

                    pair = params.get("pair", {})
                    dex = pair.get("sourceExchange", "unknown")
                    if dex.lower() == "pumpfun":
                        continue

                    base = pair.get("baseToken", {})
                    meta = (base.get("info") or {}).get("metadata") or {}
                    name = meta.get("name", "Unknown")
                    symbol = meta.get("symbol", "")
                    mint = base.get("account", "")

                    MIN_RISK = int(os.getenv("RUGCHECK_MIN_RISK", "20"))
                    if SKIP_RISK_CHECK:
                        risk = 0
                        rc = {"risk": 0, "summary": "Risk check skipped"}
                    else:
                        risk, rc = get_risk_level(mint)
                        if risk is None or risk > MIN_RISK:
                            continue

                    print(
                        f"✅ SAFE COIN: {name} ({symbol}) | mint={mint} | DEX={dex} | risk={risk} | tx=https://solscan.io/tx/{signature}"
                    )

                    try:
                        upsert_safe_token(
                            address=mint,
                            name=name,
                            symbol=symbol,
                            dex=dex,
                            risk=risk,
                            signature=signature,
                            rc=rc,
                        )

                        current_count = count_tokens()
                        print(f"💾 Stored in database (Total: {current_count})")

                        if not is_blacklisted(mint):
                            dispatch_new_token(
                                {
                                    "address": mint,
                                    "name": name,
                                    "symbol": symbol,
                                    "dex": dex,
                                    "risk": risk,
                                    "signature": signature,
                                }
                            )

                        if risk <= 10:
                            risk_cat = "🟢 LOW RISK"
                        elif risk <= 15:
                            risk_cat = "🟡 MEDIUM-LOW"
                        else:
                            risk_cat = "🟠 MEDIUM"

                        print(f"   {risk_cat} | {name} ({symbol}) | DEX: {dex}")
                    except Exception as e:
                        print(f"❌ Database error: {e}")

                elif msg.get("pair") and msg.get("signature"):
                    pair = msg["pair"]
                    dex = pair.get("sourceExchange", "unknown")

                    base = pair.get("baseToken", {})
                    meta = (base.get("info") or {}).get("metadata") or {}
                    name = meta.get("name", "Unknown")
                    symbol = meta.get("symbol", "")
                    mint = pair.get("account", "")
                    sig = msg.get("signature")

                    print(
                        f"🆕 NEW COIN: {name} ({symbol}) | mint={mint} | DEX={dex} | tx=https://solscan.io/tx/{sig}"
                    )

                    try:
                        if SKIP_RISK_CHECK:
                            risk = 0
                            rc = {"risk": 0, "summary": "Risk check skipped"}
                        else:
                            risk, rc = get_risk_level(mint)
                            if risk is None or risk > int(os.getenv("RUGCHECK_MIN_RISK", "20")):
                                continue

                        upsert_safe_token(
                            address=mint,
                            name=name,
                            symbol=symbol,
                            dex=dex,
                            risk=risk,
                            signature=sig,
                            rc=rc,
                        )
                        print(f"💾 Stored old format token in database")

                        if not is_blacklisted(mint):
                            dispatch_new_token(
                                {
                                    "address": mint,
                                    "name": name,
                                    "symbol": symbol,
                                    "dex": dex,
                                    "risk": risk,
                                    "signature": sig,
                                }
                            )
                    except Exception as e:
                        print(f"❌ Database error for old format: {e}")
                elif msg.get("result") and msg.get("result", {}).get("message"):
                    print(
                        f"[INFO] {msg['result']['message']} (ID: {msg['result'].get('subscription_id', 'unknown')})"
                    )
            except Exception as e:
                print(f"[ws] error handling message: {e} -> {msg!r}")
                continue
                

    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

async def listen():
    # Use minimal connection options to avoid ping/pong issues
    connect_kwargs = {
        "ping_interval": None,  # Disable automatic ping/pong
        "ping_timeout": None,   # Disable ping timeout
        "close_timeout": 10,    # Wait 10 seconds for close
        "max_size": None        # No message size limit
    }

    print(f"[debug] Connecting to {URL} with API key: {API_KEY[:10]}...")
    
    # Try different header parameter names for different websockets versions
    try:
        # Try extra_headers first
        async with websockets.connect(URL, extra_headers={"X-API-KEY": API_KEY}, **connect_kwargs) as ws:
            await handle_connection(ws)
    except TypeError:
        try:
            # Try additional_headers
            async with websockets.connect(URL, additional_headers={"X-API-KEY": API_KEY}, **connect_kwargs) as ws:
                await handle_connection(ws)
        except TypeError:
            try:
                # Try headers
                async with websockets.connect(URL, headers={"X-API-KEY": API_KEY}, **connect_kwargs) as ws:
                    await handle_connection(ws)
            except TypeError:
                # Last resort: try without headers and send API key in the subscription message
                print("[ws] Trying connection without custom headers...")
                async with websockets.connect(URL, **connect_kwargs) as ws:
                    await handle_connection(ws)

async def main():
    # Show comprehensive startup information
    print("🚀 SOLANA MEMECOIN SNIPER - NEW PAIRS MONITOR")
    print("=" * 60)
    
    # Database statistics
    stats = get_stats()
    print(f"📊 DATABASE STATUS:")
    print(f"   Total tokens: {stats['total']}")
    print(f"   Low risk (0-10): {stats['low_risk_0_10']}")
    print(f"   Medium risk (11-20): {stats['medium_risk_11_20']}")
    print(f"   High risk (21+): {stats['high_risk_21_plus']}")
    
    # Configuration
    print(f"\n⚙️  CONFIGURATION:")
    print(f"   Risk threshold: {os.getenv('RUGCHECK_MIN_RISK', '20')}")
    print(f"   PumpFun tokens: FILTERED OUT")
    print(f"   Chain: Solana")
    
    # Recent activity
    recent = get_recent_tokens(hours=24, limit=5)
    if recent:
        print(f"\n🕐 RECENT ACTIVITY (Last 24h):")
        for token in recent:
            print(f"   {token[1]} ({token[2]}) - Risk: {token[4]} - DEX: {token[3]}")
    
    print("\n" + "=" * 60)
    print("🔍 Monitoring for new safe memecoins...")
    print("-" * 60)
    
    # Load paper trading strategies
    load_strategies()
    
    # Start periodic maintenance and price watching tasks
    maintenance_task = asyncio.create_task(periodic_maintenance())
    prices_task = asyncio.create_task(watch_prices())

    try:
        while True:
            try:
                await listen()
            except websockets.ConnectionClosed as e:
                print(f"[ws] closed: close_code={e.code} close_reason={e.reason}")
            except Exception as e:
                print(f"[ws] error: {e}")
            print("[ws] reconnecting in 5s...")
            await asyncio.sleep(5)
    finally:
        for t in (maintenance_task, prices_task):
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        
        # Shutdown paper trading strategies
        from papertrading import shutdown
        shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        print("=" * 60)
        
        # Show final database status
        try:
            stats = get_stats()
            print(f"📊 FINAL DATABASE STATUS:")
            print(f"   Total tokens: {stats['total']}")
            print(f"   Low risk (0-10): {stats['low_risk_0_10']}")
            print(f"   Medium risk (11-20): {stats['medium_risk_11_20']}")
            print(f"   High risk (21+): {stats['high_risk_21_plus']}")
            
            # Show recent tokens
            show_recent_tokens()
            
        except Exception as e:
            print(f"❌ Error getting final stats: {e}")
        
        # Shutdown paper trading strategies
        from papertrading import shutdown
        shutdown()
        
        print("=" * 60)
        print("👋 Goodbye!")
