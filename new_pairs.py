import asyncio, json, os, sys
from dotenv import load_dotenv
import websockets
from rugcheck_client import get_risk_level

load_dotenv()
API_KEY = os.getenv("SOLANASTREAM_API_KEY")
if not API_KEY:
    print("Missing SOLANASTREAM_API_KEY in .env")
    sys.exit(1)

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
                
                # Add heartbeat to show we're receiving data
                if msg.get("method") == "ping":
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": "pong"}))
                    continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                continue

            # Process new pair messages
            if msg.get("method") == "newPairNotification" and msg.get("params"):
                params = msg["params"]
                signature = params.get("signature", "")
                
                # Extract token info from the notification
                pair = params.get("pair", {})
                dex = pair.get("sourceExchange", "unknown")
                
                # Skip PumpFun tokens
                if dex.lower() == "pumpfun":
                    continue
                
                base = pair.get("baseToken", {})
                meta = (base.get("info") or {}).get("metadata") or {}
                name = meta.get("name", "Unknown")
                symbol = meta.get("symbol", "")
                mint = base.get("account", "")
                
                # Get risk assessment from RugCheck
                MIN_RISK = int(os.getenv("RUGCHECK_MIN_RISK", "20"))
                risk, rc = get_risk_level("solana", mint)
                
                # Skip coins with risk > 20 or no risk data
                if risk is None:
                    continue  # Skip coins without risk data
                elif risk > MIN_RISK:
                    continue  # Skip high-risk coins
                
                # Only show safe coins (risk <= 20)
                print(f"✅ SAFE COIN: {name} ({symbol}) | mint={mint} | DEX={dex} | risk={risk} | tx=https://solscan.io/tx/{signature}")
                
            elif msg.get("pair") and msg.get("signature"):
                # Keep the old format handling as fallback
                pair = msg["pair"]
                dex = pair.get("sourceExchange", "unknown")
                
                base = pair.get("baseToken", {})
                meta = (base.get("info") or {}).get("metadata") or {}
                name = meta.get("name", "Unknown")
                symbol = meta.get("symbol", "")
                mint = pair.get("account", "")
                sig = msg.get("signature")

                print(f"🆕 NEW COIN: {name} ({symbol}) | mint={mint} | DEX={dex} | tx=https://solscan.io/tx/{sig}")
            elif msg.get("result") and msg.get("result", {}).get("message"):
                # Handle subscription confirmation messages
                print(f"[INFO] {msg['result']['message']} (ID: {msg['result'].get('subscription_id', 'unknown')})")

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
    while True:
        try:
            await listen()
        except Exception as e:
            print(f"[ws] error: {e}, reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
