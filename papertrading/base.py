from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class StrategyContext:
    def emit_alert(self, title: str, data: Optional[Dict[str, Any]] = None):
        print(f"[PAPER][ALERT] {title} | {data or {}}")

class Strategy:
    def on_start(self, ctx: StrategyContext): ...
    def on_new_token(self, ctx: StrategyContext, token: Dict[str, Any]): ...
    def on_bar_1m(self, ctx: StrategyContext, bar: Dict[str, Any],
                  ema_rows: list[Dict[str,Any]], atr_rows: list[Dict[str,Any]]): ...
    def on_shutdown(self, ctx: StrategyContext): ...
