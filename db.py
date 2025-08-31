import os, sqlite3, json

# persistent file-based database (instead of in-memory)
DB_PATH = "memecoin_sniper.db"
DB = sqlite3.connect(DB_PATH, check_same_thread=False)

# fast pragmas for performance
DB.execute("PRAGMA journal_mode=WAL")
DB.execute("PRAGMA synchronous=NORMAL")
DB.execute("PRAGMA temp_store=MEMORY")
DB.execute("PRAGMA cache_size=10000")
DB.execute("PRAGMA mmap_size=268435456")

DB.execute("""
CREATE TABLE IF NOT EXISTS tokens (
  address     TEXT PRIMARY KEY,               -- mint
  chain       TEXT NOT NULL DEFAULT 'solana',
  name        TEXT,
  symbol      TEXT,
  dex         TEXT,
  risk        INTEGER,
  signature   TEXT,
  rc_json     TEXT NOT NULL,
  approved    INTEGER NOT NULL DEFAULT 1,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
DB.execute("CREATE INDEX IF NOT EXISTS idx_tokens_seen ON tokens(last_seen)")
DB.execute("CREATE INDEX IF NOT EXISTS idx_tokens_risk ON tokens(risk)")
DB.commit()

# --- Minimal prices table (only price_usd, fdv_usd, marketcap_usd) ---
DB.execute("""
CREATE TABLE IF NOT EXISTS prices (
  address        TEXT PRIMARY KEY,          -- token mint
  price_usd      REAL,
  fdv_usd        REAL,
  marketcap_usd  REAL,
  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")
DB.commit()

def upsert_safe_token(*, address: str, name: str, symbol: str, dex: str,
                      risk: int, signature: str, rc: dict):
    """Insert or update a safe token in the database."""
    DB.execute("""
      INSERT INTO tokens(address, chain, name, symbol, dex, risk, signature, rc_json, approved)
      VALUES(?, 'solana', ?, ?, ?, ?, ?, ?, 1)
      ON CONFLICT(address) DO UPDATE SET
        name=excluded.name,
        symbol=excluded.symbol,
        dex=excluded.dex,
        risk=excluded.risk,
        signature=excluded.signature,
        rc_json=excluded.rc_json,
        last_seen=CURRENT_TIMESTAMP;
    """, (address, name, symbol, dex, risk, signature, json.dumps(rc or {})))
    DB.commit()

def count_tokens() -> int:
    """Get total number of tokens in database."""
    return DB.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]

def get_tokens_by_risk(max_risk: int = 20, limit: int = 50) -> list:
    """Get tokens filtered by risk level."""
    cursor = DB.execute("""
        SELECT address, name, symbol, dex, risk, signature, created_at, last_seen
        FROM tokens 
        WHERE risk <= ? 
        ORDER BY last_seen DESC 
        LIMIT ?
    """, (max_risk, limit))
    return cursor.fetchall()

def get_token_by_address(address: str) -> dict:
    """Get specific token by address."""
    cursor = DB.execute("""
        SELECT address, name, symbol, dex, risk, signature, rc_json, created_at, last_seen
        FROM tokens 
        WHERE address = ?
    """, (address,))
    row = cursor.fetchone()
    if row:
        return {
            'address': row[0],
            'name': row[1],
            'symbol': row[2],
            'dex': row[3],
            'risk': row[4],
            'signature': row[5],
            'rc_json': json.loads(row[6]) if row[6] else {},
            'created_at': row[7],
            'last_seen': row[8]
        }
    return None

def get_recent_tokens(hours: int = 24, limit: int = 50) -> list:
    """Get tokens seen in the last N hours."""
    cursor = DB.execute("""
        SELECT address, name, symbol, dex, risk, signature, created_at, last_seen
        FROM tokens 
        WHERE last_seen >= datetime('now', '-{} hours')
        ORDER BY last_seen DESC 
        LIMIT ?
    """.format(hours), (limit,))
    return cursor.fetchall()

def clear_old_tokens(days: int = 7):
    """Remove tokens older than N days."""
    DB.execute("DELETE FROM tokens WHERE last_seen < datetime('now', '-{} days')".format(days))
    DB.commit()

def get_stats() -> dict:
    """Get database statistics."""
    total = count_tokens()
    low_risk = DB.execute("SELECT COUNT(*) FROM tokens WHERE risk <= 10").fetchone()[0]
    medium_risk = DB.execute("SELECT COUNT(*) FROM tokens WHERE risk > 10 AND risk <= 20").fetchone()[0]
    high_risk = DB.execute("SELECT COUNT(*) FROM tokens WHERE risk > 20").fetchone()[0]
    
    return {
        'total': total,
        'low_risk_0_10': low_risk,
        'medium_risk_11_20': medium_risk,
        'high_risk_21_plus': high_risk
    }

def list_all_addresses(limit: int = None) -> list[str]:
    """Get all token addresses, optionally limited by count."""
    sql = "SELECT address FROM tokens ORDER BY last_seen DESC"
    cur = DB.execute(sql + (" LIMIT ?" if limit is not None else ""), ((int(limit),) if limit is not None else ()))
    return [r[0] for r in cur.fetchall()]

def upsert_price(row: dict) -> None:
    """Insert or update price data for a token."""
    DB.execute("""
      INSERT INTO prices(address, price_usd, fdv_usd, marketcap_usd, updated_at)
      VALUES(:address, :price_usd, :fdv_usd, :marketcap_usd, CURRENT_TIMESTAMP)
      ON CONFLICT(address) DO UPDATE SET
        price_usd=excluded.price_usd,
        fdv_usd=excluded.fdv_usd,
        marketcap_usd=excluded.marketcap_usd,
        updated_at=CURRENT_TIMESTAMP;
    """, row)
    DB.commit()

def get_price_snapshot(limit: int = 20) -> list[tuple]:
    """Get latest price snapshot with token details. SQLite-safe ordering."""
    # SQLite has no "NULLS LAST" → emulate with CASE
    return DB.execute("""
      SELECT t.address, t.name, t.symbol, p.price_usd, p.fdv_usd, p.marketcap_usd, p.updated_at
      FROM tokens t LEFT JOIN prices p ON t.address = p.address
      ORDER BY (p.updated_at IS NULL) ASC, p.updated_at DESC, t.last_seen DESC
      LIMIT ?
    """, (int(limit),)).fetchall()

# --- 1-minute OHLC storage ---
DB.execute("""
CREATE TABLE IF NOT EXISTS ohlc_1m (
  address        TEXT NOT NULL,
  ts_start       INTEGER NOT NULL,               -- epoch seconds (UTC) for minute start
  open           REAL NOT NULL,
  high           REAL NOT NULL,
  low            REAL NOT NULL,
  close          REAL NOT NULL,
  fdv_usd        REAL,
  marketcap_usd  REAL,
  samples        INTEGER NOT NULL,               -- should be 30
  PRIMARY KEY(address, ts_start)
);
""")
DB.execute("CREATE INDEX IF NOT EXISTS idx_ohlc_1m_addr_time ON ohlc_1m(address, ts_start)")
DB.commit()

def insert_ohlc_1m(bar: dict) -> None:
    """Insert or replace a 1-minute OHLC bar."""
    DB.execute("""
      INSERT OR REPLACE INTO ohlc_1m
        (address, ts_start, open, high, low, close, fdv_usd, marketcap_usd, samples)
      VALUES
        (:address, :ts_start, :open, :high, :low, :close, :fdv_usd, :marketcap_usd, :samples)
    """, bar)
    DB.commit()

def get_ohlc_1m(address: str, limit: int = 120) -> list[tuple]:
    """Get recent 1-minute OHLC bars for a token."""
    return DB.execute("""
      SELECT ts_start, open, high, low, close, fdv_usd, marketcap_usd, samples
      FROM ohlc_1m
      WHERE address = ?
      ORDER BY ts_start DESC
      LIMIT ?
    """, (address, int(limit))).fetchall()

# --- EMA storage ---
DB.execute("""
CREATE TABLE IF NOT EXISTS ema_1m (
  address        TEXT NOT NULL,
  ts_start       INTEGER NOT NULL,               -- epoch seconds (UTC) for minute start
  length         INTEGER NOT NULL,               -- EMA period length
  value          REAL NOT NULL,                  -- EMA value
  PRIMARY KEY(address, ts_start, length)
);
""")
DB.execute("CREATE INDEX IF NOT EXISTS idx_ema_1m_addr_time ON ema_1m(address, ts_start)")
DB.commit()

def insert_ema_1m(ema_rows: list) -> None:
    """Insert EMA values for a token."""
    for row in ema_rows:
        DB.execute("""
          INSERT OR REPLACE INTO ema_1m
            (address, ts_start, length, value)
          VALUES
            (:address, :ts_start, :length, :value)
        """, row)
    DB.commit()

def get_ema_1m(address: str, length: int, limit: int = 120) -> list[tuple]:
    """Get recent EMA values for a token."""
    return DB.execute("""
      SELECT ts_start, value
      FROM ema_1m
      WHERE address = ? AND length = ?
      ORDER BY ts_start DESC
      LIMIT ?
    """, (address, length, int(limit))).fetchall()

# --- ATR storage ---
DB.execute("""
CREATE TABLE IF NOT EXISTS atr_1m (
  address        TEXT NOT NULL,
  ts_start       INTEGER NOT NULL,               -- epoch seconds (UTC) for minute start
  length         INTEGER NOT NULL,               -- ATR period length
  value          REAL NOT NULL,                  -- ATR value
  PRIMARY KEY(address, ts_start, length)
);
""")
DB.execute("CREATE INDEX IF NOT EXISTS idx_atr_1m_addr_time ON atr_1m(address, ts_start)")
DB.commit()

def insert_atr_1m(atr_rows: list) -> None:
    """Insert ATR values for a token."""
    for row in atr_rows:
        DB.execute("""
          INSERT OR REPLACE INTO atr_1m
            (address, ts_start, length, value)
          VALUES
            (:address, :ts_start, :length, :value)
        """, row)
    DB.commit()

def get_atr_1m(address: str, length: int, limit: int = 120) -> list[tuple]:
    """Get recent ATR values for a token."""
    return DB.execute("""
      SELECT ts_start, value
      FROM atr_1m
      WHERE address = ? AND length = ?
      ORDER BY ts_start DESC
      LIMIT ?
    """, (address, length, int(limit))).fetchall()
