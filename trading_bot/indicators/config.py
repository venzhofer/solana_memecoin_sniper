import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _parse_lengths(val: str, default: str) -> list[int]:
    raw = (val or default).replace(";", ",")
    out = []
    for p in raw.split(","):
        p = p.strip()
        if not p: continue
        try:
            n = int(p)
            if n > 0: out.append(n)
        except: pass
    return out

EMA_LENGTHS = _parse_lengths(os.getenv("EMA_1M_LENGTHS"), "20")
EMA_SOURCE  = (os.getenv("EMA_1M_SOURCE") or "close").lower()
ATR_LENGTHS = _parse_lengths(os.getenv("ATR_1M_LENGTHS"), "14")
