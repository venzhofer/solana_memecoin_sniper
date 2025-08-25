import asyncio, json, os, sys
from dotenv import load_dotenv
import websockets

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
    "params": {"include_pumpfun": True}
}

async def send_heartbeat(ws):
    """Send periodic heartbeat to keep connection alive"""
    while True:
        try:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 999, "method": "heartbeat"}))
        except Exception as e:
            print(f"[heartbeat] Error: {e}")
            break

async def listen():
    # Use minimal connection options to avoid ping/pong issues
    connect_kwargs = {
        "extra_headers": {"X-API-KEY": API_KEY},
        "ping_interval": None,  # Disable automatic ping/pong
        "ping_timeout": None,   # Disable ping timeout
        "close_timeout": 10,    # Wait 10 seconds for close
        "max_size": None        # No message size limit
    }
    
    async with websockets.connect(URL, **connect_kwargs) as ws:
        print("[ws] connected")
        await ws.send(json.dumps(MSG))
        print("[ws] subscribed to new pairs")

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat(ws))
        
        try:
            message_count = 0
            async for raw in ws:
                message_count += 1
                print(f"[DEBUG] Message #{message_count} received: {raw[:200]}...")  # Show raw messages
                
                try:
                    msg = json.loads(raw)
                    print(f"[DEBUG] Message #{message_count} keys: {list(msg.keys())}")  # Show message structure
                    
                    # Add heartbeat to show we're receiving data
                    if msg.get("method") == "ping":
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": "pong"}))
                        continue
                except json.JSONDecodeError:
                    print(f"[ws] Invalid JSON received: {raw[:100]}...")
                    continue
                except Exception as e:
                    print(f"[ws] Error processing message: {e}")
                    continue

                # Process new pair messages
                if msg.get("pair") and msg.get("signature"):
                    pair = msg["pair"]
                    dex = pair.get("sourceExchange", "unknown")
                    
                    # Debug: Show all DEX names to see what we're receiving
                    print(f"[DEBUG] Received pair from DEX: {dex}")
                    
                    # Filter for only PumpSwap and Raydium
                    if dex.lower() not in ["pumpswap", "raydium"]:
                        continue
                    
                    base = pair.get("baseToken", {})
                    meta = (base.get("info") or {}).get("metadata") or {}
                    name = meta.get("name", "Unknown")
                    symbol = meta.get("symbol", "")
                    mint = base.get("account", "")
                    sig = msg.get("signature")

                    print(f"🆕 NEW COIN: {name} ({symbol}) | mint={mint} | DEX={dex} | tx=https://solscan.io/tx/{sig}")
                elif msg.get("result") and msg.get("result", {}).get("message"):
                    # Handle subscription confirmation messages
                    print(f"[INFO] {msg['result']['message']} (ID: {msg['result'].get('subscription_id', 'unknown')})")
        finally:
            heartbeat_task.cancel()

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
