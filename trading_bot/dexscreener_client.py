import httpx, asyncio, typing

DEX_API = "https://api.dexscreener.com/latest/dex"

def _to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def _safe(d: dict, path: str, default=None):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

async def fetch_token_batch(client: httpx.AsyncClient, token_addrs: list[str]) -> list[dict]:
    """
    GET /latest/dex/tokens/{addr1,addr2,...}
    Returns a list of 'pairs'. Choose best pair per token by highest liquidity.
    Output fields (per token):
      - address
      - price_usd
      - fdv_usd
      - marketcap_usd
    """
    url = f"{DEX_API}/tokens/{','.join(token_addrs)}"
    r = await client.get(url, timeout=10)
    r.raise_for_status()
    data = r.json() or {}
    pairs: list[dict] = data.get("pairs") or []

    # Pick best (highest-liquidity) pair per base token address
    best: dict[str, dict] = {}
    for p in pairs:
        base = _safe(p, "baseToken.address") or _safe(p, "baseToken")  # fallback for some chains
        if not base:
            continue
        liq = _to_float(_safe(p, "liquidity.usd"), 0.0)
        cur_best = best.get(base)
        if not cur_best or _to_float(_safe(cur_best, "liquidity.usd"), 0.0) < liq:
            best[base] = p

    out = []
    for addr, p in best.items():
        out.append({
            "address": addr,
            "price_usd": _to_float(p.get("priceUsd")),
            "fdv_usd": _to_float(p.get("fdv")),
            "marketcap_usd": _to_float(p.get("marketCap")),
        })
    return out
