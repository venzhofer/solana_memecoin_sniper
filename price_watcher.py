import os, math, asyncio, itertools
import time
import httpx
from db import upsert_price, insert_ohlc_1m, insert_ema_1m, insert_atr_1m
from dexscreener_client import fetch_token_batch
from ohlc_agg import add_sample
from indicators import update_all_for_bar
from papertrading import get_watchable_addresses, dispatch_bar_1m

INTERVAL = float(os.getenv("PRICE_POLL_INTERVAL_SEC", "2"))
BATCH_SIZE = int(os.getenv("DEXSCREENER_BATCH_SIZE", "30"))
MAX_REQ_PER_MIN = int(os.getenv("DEXSCREENER_MAX_REQ_PER_MIN", "300"))

def _chunk(lst, size):
    it = iter(lst)
    while True:
        block = list(itertools.islice(it, size))
        if not block:
            return
        yield block

def _batches_per_tick(interval_s: float) -> int:
    # 300 req/min ⇒ 5/sec
    per_sec = MAX_REQ_PER_MIN / 60.0
    return max(1, int((per_sec * interval_s) // 1))

async def _poll_once(client: httpx.AsyncClient, addr_batches):
    async def one(batch):
        try:
            rows = await fetch_token_batch(client, batch)
            now = time.time()
            for r in rows:
                # 1) persist latest point (price/fdv/mc)
                upsert_price(r)
                # 2) feed the OHLC aggregator; write a candle when ready
                bar = add_sample(
                    r["address"],
                    price=r.get("price_usd"),
                    fdv=r.get("fdv_usd"),
                    mc=r.get("marketcap_usd"),
                    ts=now
                )
                if bar:
                    insert_ohlc_1m(bar)
                    ema_rows, atr_rows = update_all_for_bar({
                        "address": bar["address"],
                        "ts_start": bar["ts_start"],
                        "open":  bar["open"],
                        "high":  bar["high"],
                        "low":   bar["low"],
                        "close": bar["close"],
                    })
                    insert_ema_1m(ema_rows)
                    insert_atr_1m(atr_rows)
                    dispatch_bar_1m(bar, ema_rows, atr_rows)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await asyncio.sleep(1.5)  # brief backoff
        except Exception:
            pass

    await asyncio.gather(*(one(b) for b in addr_batches))

async def watch_prices(refresh_addrs_every: float = 10.0):
    limit_per_tick = _batches_per_tick(INTERVAL)
    timeout = httpx.Timeout(10.0, read=10.0, connect=5.0)
    limits = httpx.Limits(max_connections=limit_per_tick * 2, max_keepalive_connections=limit_per_tick * 2)

    async with httpx.AsyncClient(timeout=timeout, limits=limits, http2=True) as client:
        addrs = get_watchable_addresses()
        last_refresh = 0.0
        all_batches = list(_chunk(addrs, BATCH_SIZE))
        idx = 0
        loop = asyncio.get_event_loop()

        while True:
            now = loop.time()
            if (now - last_refresh) >= refresh_addrs_every:
                addrs = get_watchable_addresses()
                all_batches = list(_chunk(addrs, BATCH_SIZE))
                idx = 0 if idx >= len(all_batches) else idx
                last_refresh = now

            if not all_batches:
                await asyncio.sleep(INTERVAL); continue

            end = min(idx + limit_per_tick, len(all_batches))
            cur = all_batches[idx:end]
            if len(cur) < limit_per_tick and idx != 0:
                cur += all_batches[0:max(0, limit_per_tick - len(cur))]
                idx = (idx + limit_per_tick) % len(all_batches)
            else:
                idx = end % len(all_batches)

            await _poll_once(client, cur)
            await asyncio.sleep(INTERVAL)

if __name__ == "__main__":
    print("💰 Starting price watcher...")
    print(f"   Poll interval: {INTERVAL}s")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Max requests/min: {MAX_REQ_PER_MIN}")
    print("-" * 50)
    
    try:
        asyncio.run(watch_prices())
    except KeyboardInterrupt:
        print("\n🛑 Price watcher stopped")
