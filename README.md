# 🚀 Solana Memecoin Sniper

A real-time monitoring system for detecting and tracking safe Solana memecoins with integrated risk assessment and database storage.

## ✨ Features

- **🔍 Real-time monitoring** of new Solana memecoin pairs
- **🛡️ Risk assessment** using RugCheck API integration
- **💾 Database storage** with SQLite for token tracking
- **🚫 Smart filtering** (PumpFun tokens, high-risk coins)
- **📊 Live statistics** and periodic maintenance
- **⚡ In-memory database** for fast performance

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Set Environment Variables
Create a `.env` file:
```bash
SOLANASTREAM_API_KEY=your_api_key_here
RUGCHECK_API_KEY=your_rugcheck_key_here  # Optional
RUGCHECK_MIN_RISK=20  # Risk threshold (0-100, lower = safer)
```

### 3. Start Monitoring
```bash
python3 new_pairs.py
```

## 📊 Database Integration

The system automatically stores all detected safe tokens in an in-memory SQLite database:

- **Token details**: Name, symbol, mint address, DEX source
- **Risk assessment**: RugCheck risk score and full report
- **Transaction info**: Signature and creation timestamp
- **Auto-updates**: Duplicate tokens are updated, not duplicated

## 🎯 Risk Categories

- **🟢 LOW RISK (0-10)**: Very safe, recommended
- **🟡 MEDIUM-LOW (11-15)**: Moderately safe
- **🟠 MEDIUM (16-20)**: Acceptable risk
- **🔴 HIGH RISK (21+)**: Filtered out automatically

## 🛠️ Usage

### Start Monitoring
```bash
python3 new_pairs.py
```

### Query Database (Without Stopping Monitor)
```bash
python3 query_db.py
```

### Show Database Summary While Running
```bash
# Find the process ID first
ps aux | grep new_pairs

# Send signal to show summary (replace <PID> with actual process ID)
kill -USR1 <PID>
```

## 📁 File Structure

```
solana_memecoin_sniper/
├── new_pairs.py          # Main monitoring script
├── db.py                 # Database operations
├── rugcheck_client.py    # Risk assessment client
├── query_db.py           # Database query tool
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
└── README.md            # This file
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SOLANASTREAM_API_KEY` | SolanaStream API key | Required |
| `RUGCHECK_API_KEY` | RugCheck API key | Optional |
| `RUGCHECK_MIN_RISK` | Maximum risk threshold | 20 |

### Risk Thresholds

- **Conservative**: Set `RUGCHECK_MIN_RISK=15` (only very safe coins)
- **Moderate**: Set `RUGCHECK_MIN_RISK=20` (default, balanced)
- **Aggressive**: Set `RUGCHECK_MIN_RISK=25` (more coins, higher risk)

## 🔍 Sample Output

```
🚀 SOLANA MEMECOIN SNIPER - NEW PAIRS MONITOR
============================================================
📊 DATABASE STATUS:
   Total tokens: 3
   Low risk (0-10): 2
   Medium risk (11-20): 1
   High risk (21+): 0

⚙️  CONFIGURATION:
   Risk threshold: 20
   PumpFun tokens: FILTERED OUT
   Chain: Solana

============================================================
🔍 Monitoring for new safe memecoins...
------------------------------------------------------------

✅ SAFE COIN: fomo coin (fomo) | mint=H2EdeRzBWG8g2K6zPCRCyDyvudvqDXPNbgigW1p8pump | DEX=pumpswap | risk=1
💾 Stored in database (Total: 1)
   🟢 LOW RISK | fomo coin (fomo) | DEX: pumpswap
```

## 🚨 Troubleshooting

### Connection Issues
- Verify your `SOLANASTREAM_API_KEY` is correct
- Check internet connection
- The script will automatically reconnect on errors

### Database Issues
- Database is in-memory and resets when script stops
- Use `query_db.py` to check database status
- Ensure all dependencies are installed

### Risk Assessment Issues
- RugCheck API may be rate-limited
- Some new tokens may not have risk data yet
- Adjust `RUGCHECK_MIN_RISK` if needed

## 🔧 Advanced Usage

### Custom Risk Thresholds
```bash
# More conservative
export RUGCHECK_MIN_RISK=15
python3 new_pairs.py

# More aggressive
export RUGCHECK_MIN_RISK=25
python3 new_pairs.py
```

### Database Queries
```python
from db import get_stats, get_recent_tokens

# Get statistics
stats = get_stats()
print(f"Total tokens: {stats['total']}")

# Get recent tokens
recent = get_recent_tokens(hours=24, limit=10)
for token in recent:
    print(f"{token[1]} ({token[2]}) - Risk: {token[4]}")
```

## 📈 Performance

- **Memory usage**: ~1-5MB for typical usage
- **CPU usage**: Minimal, mostly idle when no new tokens
- **Network**: WebSocket connection to SolanaStream
- **Database**: In-memory SQLite for instant queries

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is for educational and research purposes. Use at your own risk.

---

**⚠️ Disclaimer**: This tool is for monitoring and research purposes only. Always do your own research before investing in any cryptocurrency. The risk assessment is provided by third-party services and should not be considered financial advice.
