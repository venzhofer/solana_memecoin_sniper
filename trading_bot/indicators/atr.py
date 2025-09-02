from dataclasses import dataclass
from typing import Optional

@dataclass
class StreamingATR:
    length: int
    prev_atr: Optional[float] = None
    prev_close: Optional[float] = None

    def update(self, bar: dict) -> float:
        h, l, c = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if self.prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - self.prev_close), abs(l - self.prev_close))
        if self.prev_atr is None:
            atr = tr  # seed with first TR
        else:
            atr = ((self.prev_atr * (self.length - 1)) + tr) / self.length  # Wilder
        self.prev_atr = atr
        self.prev_close = c
        return float(atr)
