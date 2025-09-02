from collections import defaultdict
from typing import Optional
from .config import EMA_LENGTHS, EMA_SOURCE, ATR_LENGTHS
from .ema import StreamingEMA
from .atr import StreamingATR

# Global registry of indicators per token
_indicators: dict[str, dict] = defaultdict(dict)

def _ensure_indicators(address: str):
    """Ensure all required indicators exist for a token."""
    if address not in _indicators:
        _indicators[address] = {}
    
    token_indicators = _indicators[address]
    
    # Create EMA indicators
    for length in EMA_LENGTHS:
        ema_key = f"ema_{length}"
        if ema_key not in token_indicators:
            token_indicators[ema_key] = StreamingEMA(length, EMA_SOURCE)
    
    # Create ATR indicators
    for length in ATR_LENGTHS:
        atr_key = f"atr_{length}"
        if atr_key not in token_indicators:
            token_indicators[atr_key] = StreamingATR(length)

def update_all_for_bar(bar: dict) -> tuple[list, list]:
    """
    Update all indicators for a completed OHLC bar.
    Returns (ema_rows, atr_rows) for database insertion.
    """
    address = bar["address"]
    _ensure_indicators(address)
    
    token_indicators = _indicators[address]
    ema_rows = []
    atr_rows = []
    
    # Update EMAs
    for length in EMA_LENGTHS:
        ema_key = f"ema_{length}"
        ema = token_indicators[ema_key]
        value = ema.update(bar)
        
        ema_rows.append({
            "address": address,
            "ts_start": bar["ts_start"],
            "length": length,
            "source": ema.source,
            "value": value
        })
    
    # Update ATRs
    for length in ATR_LENGTHS:
        atr_key = f"atr_{length}"
        atr = token_indicators[atr_key]
        value = atr.update(bar)
        
        atr_rows.append({
            "address": address,
            "ts_start": bar["ts_start"],
            "length": length,
            "value": value
        })
    
    return ema_rows, atr_rows

def reset_indicators(address: str = None):
    """Reset indicators for a specific token or all tokens."""
    if address:
        if address in _indicators:
            del _indicators[address]
    else:
        _indicators.clear()

def get_indicator_value(address: str, indicator_type: str, length: int) -> Optional[float]:
    """Get current value of a specific indicator."""
    if address not in _indicators:
        return None
    
    key = f"{indicator_type}_{length}"
    if key not in _indicators[address]:
        return None
    
    indicator = _indicators[address][key]
    if indicator_type == "ema":
        return indicator.prev
    elif indicator_type == "atr":
        return indicator.prev_atr
    
    return None
