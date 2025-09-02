# Show latest prices with just the required fields.
from trading_bot.db import get_price_snapshot

rows = get_price_snapshot(20)
if not rows:
    print("No prices yet.")
else:
    for addr, name, sym, price, fdv, mc, ts in rows:
        print(f"{name or 'Unknown'} ({sym or ''}) {addr[:6]}.. | "
              f"price=${price} | fdv=${fdv} | mc=${mc} | {ts}")
