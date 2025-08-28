# View recent 1-minute candles for a token.
import sys, time
sys.path.append('.')
from db import get_ohlc_1m

if len(sys.argv) < 2:
    print("Usage: python scripts/peek_ohlc.py <TOKEN_MINT> [LIMIT]")
    sys.exit(1)

addr = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

rows = get_ohlc_1m(addr, limit)
if not rows:
    print("No 1m candles yet.")
    sys.exit(0)

for ts_start, o, h, l, c, fdv, mc, n in rows:
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts_start))
    print(f"{t}Z  O:{o} H:{h} L:{l} C:{c}  FDV:{fdv}  MC:{mc}  n={n}")
