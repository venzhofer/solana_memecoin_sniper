from dataclasses import dataclass
from typing import Optional

def _src_value(bar: dict, source: str) -> float:
    o,h,l,c = bar["open"], bar["high"], bar["low"], bar["close"]
    if source == "open":  return o
    if source == "high":  return h
    if source == "low":   return l
    if source == "hl2":   return (h + l) / 2.0
    if source == "hlc3":  return (h + l + c) / 3.0
    if source == "ohlc4": return (o + h + l + c) / 4.0
    return c  # default close

@dataclass
class StreamingEMA:
    length: int
    source: str = "close"
    prev: Optional[float] = None

    def __post_init__(self):
        self.alpha = 2.0 / (self.length + 1.0)

    def update(self, bar: dict) -> float:
        x = float(_src_value(bar, self.source))
        if self.prev is None:
            self.prev = x
        else:
            self.prev = self.prev + self.alpha * (x - self.prev)
        return float(self.prev)
