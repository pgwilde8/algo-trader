# EUR/USD ML5 Ensemble Signal Service

Signal generation service that creates ML trading signals using a 5-model XGBoost ensemble and saves them to the database.

## Overview

This service:
- ✅ Generates ML signals using 5-model XGBoost ensemble
- ✅ Saves signals to database (`ml_signal_history` table)
- ✅ Runs on a schedule (default: every hour)
- ✅ Skips generation if latest signal is still valid

## Files

- `signal_engine.py` - ML signal generation logic (loads models, calculates indicators, generates predictions)
- `main.py` - Service runner (generates signals, saves to database, runs on schedule)
- `config.json` - Configuration file
- `README.md` - This file

## Configuration

Edit `config.json`:

```json
{
  "instrument": "EUR_USD",
  "cycle_interval_seconds": 3600,
  "description": "EUR/USD ML5 Ensemble Signal Service"
}
```

## Setup

1. **Ensure models exist:**
   Models should be at:
   ```
   /home/myalgo/algo-trader/ml_models/signal_generator/eurusd-models/
   ├── EUR_USD_xgboost_seed43.json
   ├── EUR_USD_xgboost_seed44.json
   ├── EUR_USD_xgboost_seed45.json
   ├── EUR_USD_xgboost_seed46.json
   └── EUR_USD_xgboost_seed47.json
   ```

2. **Ensure data file exists:**
   Historical data should be at:
   ```
   /home/myalgo/algo-trader/data/h1_data/EUR_USD_H1_20051202_to_20251127.csv
   ```

3. **Run the service:**
   ```bash
   cd /home/myalgo/algo-trader/app/services/signal-service/eurusd-ml5
   python3 main.py
   ```

## How It Works

1. **Signal Generation Cycle:**
   - Checks if latest signal in database is still valid
   - If expired/missing, generates new signal using ML ensemble
   - Saves signal to `ml_signal_history` table
   - Waits for next cycle interval

2. **Signal Generation Process:**
   - Loads 5-model ensemble (seeds 43-47)
   - Loads most recent 250 H1 candles
   - Calculates technical indicators (RSI, MACD, ATR, EMAs, momentum, etc.)
   - Runs ensemble prediction (averages 5 model predictions)
   - Determines direction (BUY/SELL/NEUTRAL) and confidence (HIGH/MEDIUM/LOW)
   - Creates signal record with all indicators and model predictions

3. **Database Storage:**
   - Saves to `ml_signal_history` table
   - Stores all indicators as JSONB
   - Stores individual model predictions as JSONB
   - Links signals to trades via `ml_trade_executions` (when bots use signals)

## Signal Output Format

Each signal includes:
- `instrument`: "EUR_USD"
- `direction`: "BUY" | "SELL" | "NEUTRAL"
- `confidence`: "HIGH" | "MEDIUM" | "LOW"
- `ml_probability`: 0.0-1.0 (probability price goes UP)
- `entry_price`: Current price
- `ensemble_size`: 5 (number of models)
- `individual_models`: Array of each model's prediction
- `indicators`: All technical indicators (RSI, MACD, ATR, EMAs, etc.)
- `timestamp`: When signal was generated
- `valid_until`: When signal expires (next H1 candle)

## Logs

Logs are saved to: `logs/eurusd_ml5_signal_service_YYYYMMDD.log`

## Differences from Bot

**Signal Service (this):**
- ✅ Generates signals
- ✅ Saves to database
- ✅ No trading logic
- ✅ No OANDA API calls

**Bot (separate):**
- Reads signals from database
- Places trades via OANDA API
- Manages positions and risk
- Executes trading strategy

## Integration with Bots

Bots can query the database for the latest valid signal:

```python
from app.db.db import get_db
from app.models.ml_signal_history import MLSignalHistory

async def get_latest_signal(instrument: str = "EUR_USD"):
    async for db in get_db():
        signal = db.query(MLSignalHistory).filter(
            MLSignalHistory.instrument == instrument,
            MLSignalHistory.valid_until > datetime.now(timezone.utc)
        ).order_by(MLSignalHistory.timestamp.desc()).first()
        return signal
```

## Next Steps

1. Set up systemd service (similar to bot)
2. Schedule to run continuously
3. Monitor logs for errors
4. Build bots that read signals from database

