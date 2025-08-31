import os
from typing import Dict, Any, List
from papertrading.base import Strategy, StrategyContext
from papertrading.db import (
    pos_get, pos_upsert, purge_token_data, blacklist_add, is_blacklisted
)
from db import get_ohlc_1m  # reuse candles

def _find_ema(rows: List[Dict[str, Any]], length: int, source: str = "low"):
    return next((r["value"] for r in rows if r.get("len")==length and r.get("source")==source), None)

def _find_atr(rows: List[Dict[str, Any]], length: int):
    return next((r["value"] for r in rows if r.get("len")==length), None)

LOOKBACK = int(os.getenv("LOOKBACK_BREAKOUT_BARS", "3"))
ATR_K    = float(os.getenv("ATR_STOP_MULT", "2"))
TRAIL_P  = float(os.getenv("TRAIL_PCT", "0.20"))

class EarlyMomentum(Strategy):
    def __init__(self):
        self._state: Dict[str, Dict[str, Any]] = {}

    def on_new_token(self, ctx: StrategyContext, token: Dict[str, Any]):
        addr = token["address"]
        if is_blacklisted(addr): return
        self._state[addr] = {"first_open": None, "first_ts": None, "bars_seen": 0, "dropped": False}

    def on_bar_1m(self, ctx: StrategyContext, bar: Dict[str, Any],
                  ema_rows: List[Dict[str, Any]], atr_rows: List[Dict[str, Any]]):
        addr = bar["address"]; ts = bar["ts_start"]
        if is_blacklisted(addr): return

        o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
        st = self._state.setdefault(addr, {"first_open": None, "first_ts": None, "bars_seen": 0, "dropped": False})

        if st["first_open"] is None:
            st["first_open"] = o; st["first_ts"] = ts; st["bars_seen"] = 0

        # 80% dump in first 10 bars → blacklist & purge
        if not st["dropped"] and st["bars_seen"] < 10 and c <= 0.2 * float(st["first_open"]):
            st["dropped"] = True
            blacklist_add(addr, "dump>=80%_first10m")
            purge_token_data(addr)
            ctx.emit_alert("DROP & PURGE (>=80% in first 10m)", {"addr": addr})
            return
        st["bars_seen"] += 1
        if st["dropped"]: return

        row = pos_get(addr)
        status = row[1] if row else "flat"

        ema5_low = _find_ema(ema_rows, 5, "low")
        atr14 = _find_atr(atr_rows, 14)

        # Entry
        if status in (None, "flat", "ended") and ema5_low is not None and atr14 is not None:
            prev = get_ohlc_1m(addr, LOOKBACK + 1)
            if prev and len(prev) >= 2:
                prev_only = prev[1:LOOKBACK+1]
                recent_high = max(p[2] for p in prev_only) if prev_only else o
            else:
                recent_high = o
            if c > float(ema5_low) and c > float(recent_high):
                entry = c
                stop  = entry - float(ATR_K) * float(atr14)
                pos_upsert(addr, status="long", entry_ts=ts, entry_price=entry,
                           stop_price=stop, breakeven_price=None, high_since_entry=h, half_sold=0)
                ctx.emit_alert("ENTRY", {"addr": addr, "ts": ts, "entry": entry, "stop": stop})
                return

        # Manage position
        if row and row[1] == "long":
            _, _, entry_ts, entry_price, stop_price, breakeven_price, high_since_entry, half_sold = row
            entry_price = float(entry_price); stop_price = float(stop_price) if stop_price is not None else None
            high_since_entry = max(float(high_since_entry or -1e9), h)
            half_sold = int(half_sold or 0)

            # Capital protection at 2x
            if not half_sold and c >= 2.0 * entry_price:
                half_sold = 1
                breakeven_price = entry_price
                stop_price = max(stop_price or 0.0, entry_price)
                ctx.emit_alert("TAKE 50% & MOVE TO BE", {"addr": addr, "ts": ts})

            # Hybrid trailing stop
            atr_stop = (c - float(ATR_K) * float(atr14)) if atr14 is not None else -1e9
            pct_stop = high_since_entry * (1.0 - float(TRAIL_P))
            be_stop  = breakeven_price if breakeven_price is not None else -1e9
            final_stop = max(atr_stop, pct_stop, be_stop)
            if stop_price is None or final_stop > stop_price:
                stop_price = final_stop

            # Exit
            if c <= stop_price:
                pos_upsert(addr, status="ended", entry_ts=entry_ts, entry_price=entry_price,
                           stop_price=stop_price, breakeven_price=breakeven_price,
                           high_since_entry=high_since_entry, half_sold=half_sold)
                ctx.emit_alert("EXIT (stop hit)", {"addr": addr, "ts": ts, "exit": c, "stop": stop_price})
            else:
                pos_upsert(addr, status="long", entry_ts=entry_ts, entry_price=entry_price,
                           stop_price=stop_price, breakeven_price=breakeven_price,
                           high_since_entry=breakeven_price, half_sold=half_sold)
