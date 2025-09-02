import os, importlib
from typing import List, Type
from .base import Strategy, StrategyContext

_CTX = StrategyContext()
_STRATS: List[Strategy] = []

def load_strategies():
    if _STRATS: return _STRATS
    raw = os.getenv("PAPER_STRATEGIES", "").strip()
    if not raw: return []
    for path in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            mod_path, cls_name = path.rsplit(".", 1)
            mod = importlib.import_module(mod_path)
            cls: Type[Strategy] = getattr(mod, cls_name)
        except Exception as e:
            print(f"[paper] failed to load strategy '{path}': {e}")
            continue
        _STRATS.append(cls())
    for s in _STRATS:
        try: s.on_start(_CTX)
        except Exception as e: print(f"[paper] on_start error: {e}")
    return _STRATS

def dispatch_new_token(token: dict):
    for s in _STRATS:
        try: s.on_new_token(_CTX, token)
        except Exception as e: print(f"[paper] on_new_token error: {e}")

def dispatch_bar_1m(bar: dict, ema_rows: list[dict], atr_rows: list[dict]):
    for s in _STRATS:
        try: s.on_bar_1m(_CTX, bar, ema_rows, atr_rows)
        except Exception as e: print(f"[paper] on_bar_1m error: {e}")

def shutdown():
    for s in _STRATS:
        try: s.on_shutdown(_CTX)
        except Exception as e: print(f"[paper] on_shutdown error: {e}")
