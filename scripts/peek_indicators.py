import sys
import os
# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators import EMA_LENGTHS, EMA_SOURCE, ATR_LENGTHS
from db import get_ohlc_1m

if len(sys.argv) < 2:
    print("Usage: python scripts/peek_indicators.py <MINT> [N_BARS]"); raise SystemExit(1)
addr = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
bars = get_ohlc_1m(addr, limit)

print(f"Token: {addr}")
print(f"EMA lengths={EMA_LENGTHS} source={EMA_SOURCE} | ATR lengths={ATR_LENGTHS}")
if not bars: print("No 1m bars yet."); raise SystemExit(0)
for ts_start, o,h,l,c, *_ in reversed(bars):
    from time import gmtime, strftime
    t = strftime("%Y-%m-%d %H:%M:%S", gmtime(int(ts_start)))
    print(f"{t}Z  O:{o} H:{h} L:{l} C:{c}")
