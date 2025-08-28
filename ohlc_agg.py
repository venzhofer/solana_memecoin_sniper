# In-memory rolling aggregator: every 30 price samples → 1m OHLC bar.
# Non-overlapping windows (exactly 30 samples each).
import time
from collections import defaultdict, deque

SAMPLES_PER_BAR = 30  # 30 samples × 2s interval ≈ 60s

class _Buf:
    __slots__ = ("samples", "first_ts")
    def __init__(self):
        self.samples = deque()  # each item: (ts, price, fdv, mc)
        self.first_ts = None

_buffers: dict[str, _Buf] = defaultdict(_Buf)

def add_sample(address: str, *, price: float = None, fdv: float = None, mc: float = None, ts: float = None):
    """
    Add one sample for a token. Returns a dict bar when 30 samples are collected, else None.
    Bar fields: address, ts_start (epoch sec, floored to minute), open, high, low, close, fdv_usd, marketcap_usd, samples.
    """
    if price is None:
        return None  # don't count missing price

    ts = ts or time.time()
    buf = _buffers[address]
    if buf.first_ts is None:
        buf.first_ts = ts

    buf.samples.append((ts, price, fdv, mc))

    if len(buf.samples) < SAMPLES_PER_BAR:
        return None

    # Build bar from exactly 30 most-recent samples
    items = [buf.samples.popleft() for _ in range(SAMPLES_PER_BAR)]
    # Reset first_ts for next window
    buf.first_ts = None if not buf.samples else buf.samples[0][0]

    prices = [p for (_, p, _, _) in items]
    fdvs = [f for (_, _, f, _) in items if f is not None]
    mcs  = [m for (_, _, _, m) in items if m is not None]

    open_ = prices[0]
    high_ = max(prices)
    low_  = min(prices)
    close_= prices[-1]

    # Use last observed FDV/MC in the window (common convention for candles)
    fdv_last = fdvs[-1] if fdvs else None
    mc_last  = mcs[-1] if mcs else None

    # Floor to the minute of the first sample in the window
    first_ts = items[0][0]
    ts_start = int(first_ts // 60 * 60)

    return {
        "address": address,
        "ts_start": ts_start,
        "open": open_,
        "high": high_,
        "low":  low_,
        "close": close_,
        "fdv_usd": fdv_last,
        "marketcap_usd": mc_last,
        "samples": SAMPLES_PER_BAR,
    }
