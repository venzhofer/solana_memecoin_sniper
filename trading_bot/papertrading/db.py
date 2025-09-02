# Paper-only tables & helpers, built on top of the main in-RAM SQLite connection.
from typing import Any, Optional
from ..db import DB, get_ohlc_1m  # reuse core DB + candles

# --- Paper schema ---
DB.execute("""
CREATE TABLE IF NOT EXISTS paper_blacklist (
  address TEXT PRIMARY KEY,
  reason  TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
DB.execute("""
CREATE TABLE IF NOT EXISTS paper_positions (
  address              TEXT PRIMARY KEY,
  status               TEXT NOT NULL,                 -- 'flat'|'long'|'ended'|'dropped'
  entry_ts             INTEGER,
  entry_price          REAL,
  stop_price           REAL,
  breakeven_price      REAL,
  high_since_entry     REAL,
  half_sold            INTEGER DEFAULT 0,
  entry_marketcap_usd  REAL,                          -- <- NEW: MC at entry
  updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
DB.execute("""
CREATE TABLE IF NOT EXISTS paper_trades (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  address   TEXT NOT NULL,
  side      TEXT NOT NULL,                        -- 'buy'|'sell'
  qty       REAL,
  price     REAL,
  ts_start  INTEGER,
  note      TEXT
);
""")
DB.execute("CREATE INDEX IF NOT EXISTS idx_paper_positions_status ON paper_positions(status)")
DB.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_addr ON paper_trades(address)")
DB.commit()

# --- Paper helpers ---
def blacklist_add(address: str, reason: str = ""):
    DB.execute("INSERT OR REPLACE INTO paper_blacklist(address, reason) VALUES(?, ?)", (address, reason))
    DB.commit()

def is_blacklisted(address: str) -> bool:
    return bool(DB.execute("SELECT 1 FROM paper_blacklist WHERE address=?", (address,)).fetchone())

def purge_token_data(address: str):
    # remove all runtime data for this token (paper scope + core)
    DB.execute("DELETE FROM prices      WHERE address=?", (address,))
    DB.execute("DELETE FROM ohlc_1m     WHERE address=?", (address,))
    DB.execute("DELETE FROM ema_1m      WHERE address=?", (address,))
    DB.execute("DELETE FROM atr_1m      WHERE address=?", (address,))
    DB.execute("DELETE FROM paper_positions WHERE address=?", (address,))
    DB.execute("DELETE FROM paper_trades    WHERE address=?", (address,))
    DB.execute("DELETE FROM tokens      WHERE address=?", (address,))
    DB.commit()

def get_watchable_addresses(limit: Optional[int] = None) -> list[str]:
    if limit is None:
        rows = DB.execute("""
          SELECT address FROM tokens
          WHERE address NOT IN (SELECT address FROM paper_blacklist)
          ORDER BY last_seen DESC
        """).fetchall()
    else:
        rows = DB.execute("""
          SELECT address FROM tokens
          WHERE address NOT IN (SELECT address FROM paper_blacklist)
          ORDER BY last_seen DESC
          LIMIT ?
        """, (int(limit),)).fetchall()
    return [r[0] for r in rows]

def pos_get(address: str):
    return DB.execute("""
      SELECT address,status,entry_ts,entry_price,stop_price,breakeven_price,high_since_entry,half_sold,entry_marketcap_usd
      FROM paper_positions WHERE address=?""", (address,)).fetchone()

def pos_upsert(address: str, **kw: Any):
    cols = ["status","entry_ts","entry_price","stop_price","breakeven_price","high_since_entry","half_sold","entry_marketcap_usd"]
    vals = [kw.get(c) for c in cols]
    DB.execute(f"""
      INSERT INTO paper_positions(address,{','.join(cols)},updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
      ON CONFLICT(address) DO UPDATE SET
        {', '.join([f"{c}=excluded.{c}" for c in cols])},
        updated_at=CURRENT_TIMESTAMP
    """, (address, *vals))
    DB.commit()

def trade_log(address: str, side: str, qty: Optional[float], price: float, ts_start: int, note: str = ""):
    DB.execute("""
      INSERT INTO paper_trades(address, side, qty, price, ts_start, note)
      VALUES(?,?,?,?,?,?)
    """, (address, side, qty, price, ts_start, note))
    DB.commit()

def pos_set_entry_marketcap(address: str, mc_usd: Optional[float]):
    DB.execute("UPDATE paper_positions SET entry_marketcap_usd=? WHERE address=?", (mc_usd, address))
    DB.commit()

def get_token_meta(address: str) -> tuple[Optional[str], Optional[str]]:
    row = DB.execute("SELECT name, symbol FROM tokens WHERE address=?", (address,)).fetchone()
    return (row[0], row[1]) if row else (None, None)

def get_entry_marketcap(address: str) -> Optional[float]:
    row = DB.execute("SELECT entry_marketcap_usd FROM paper_positions WHERE address=?", (address,)).fetchone()
    return float(row[0]) if row and row[0] is not None else None
