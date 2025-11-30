# USD/JPY ML Ensemble Auto Trader

Automated trading bot that uses signal engine to place trades on USD/JPY. Currently uses rule-based signals (RSI, MACD, EMA), but structure is ready for ML ensemble when models are trained.

## 🎯 Features

- **Signal-Based Trading**: Uses USD/JPY signal engine (rule-based for now, ML-ready)
- **Risk Management**: Configurable risk percentage per trade (default 0.2%)
- **ATR-Based Stops**: Stop loss and take profit based on ATR (Average True Range)
- **Confidence Filtering**: Only trades MEDIUM+ confidence signals
- **Position Management**: Maximum 1 position at a time
- **H1 Timeframe**: Checks signals every hour (H1 timeframe)
- **Same-Direction Cooldown**: Prevents re-entering same direction too quickly

## 📁 Files

- `main.py` - Main bot runner
- `strategy_ml_ensemble.py` - Trading strategy using signals
- `oanda_service.py` - OANDA API service (adapted for USD/JPY)
- `config.json` - Configuration file
- `README.md` - This file

## ⚙️ Configuration

Edit `config.json`:

```json
{
  "risk_percentage": 0.2,           // Risk 0.2% of account per trade
  "stop_loss_multiplier": 2.0,      // Stop loss = 2x ATR
  "take_profit_multiplier": 3.0,   // Take profit = 3x ATR
  "min_confidence": "MEDIUM",       // Only trade MEDIUM+ confidence
  "max_positions": 1,               // Maximum 1 position at a time
  "cycle_interval_seconds": 3600,   // Check every hour
  "same_direction_cooldown": 1800  // 30 minutes cooldown
}
```

## 🔧 USD/JPY Specific Adaptations

### Pip Value
- **USD/JPY**: 1 pip = 0.01 (2 decimal places)
- **EUR/USD**: 1 pip = 0.0001 (4 decimal places)

### Price Formatting
- **USD/JPY**: 3 decimal places (e.g., 150.123)
- **EUR/USD**: 5 decimal places (e.g., 1.12345)

### ATR Values
- **USD/JPY**: Typically 0.5-2.0 (higher absolute values)
- **EUR/USD**: Typically 0.0005-0.0020 (lower absolute values)

### Position Sizing
- USD/JPY uses same pip value calculation ($10 per 100k units per pip)
- But pip = 0.01 instead of 0.0001

## 🚀 Setup

1. **Environment Variables** (in `.env.live`):
   ```bash
   OANDA_ACCOUNT_ID_USDJPY=your_account_id
   OANDA_API_TOKEN=your_api_token
   OANDA_ENV=live  # or 'practice'
   ```

2. **Run Bot**:
   ```bash
   cd /home/admintrader/tradermain/bots/bot-usdjpy-ml-ensemble
   python3 main.py
   ```

## 📊 How It Works

1. **Signal Generation**: Bot gets signal from `usdjpy_signal_engine.py` (rule-based: RSI, MACD, EMA)
2. **Signal Validation**: Checks confidence level (MEDIUM+ required)
3. **Position Check**: Verifies no existing positions
4. **Risk Calculation**: Calculates position size based on risk percentage
5. **Stop/Target**: Sets stop loss (2x ATR) and take profit (3x ATR)
6. **Trade Execution**: Places market order via OANDA API

## 🎯 Trading Logic

**Current (Rule-Based):**
- **BUY Signal**: RSI < 30 AND EMA50 > EMA200 AND MACD histogram > 0
- **SELL Signal**: RSI > 70 AND EMA50 < EMA200 AND MACD histogram < 0
- **NEUTRAL**: Otherwise

**Confidence Levels:**
- **HIGH**: All 3 conditions agree
- **MEDIUM**: 2 out of 3 agree
- **LOW**: Otherwise - **NOT TRADED**

**Future (ML Ensemble):**
- When ML models are trained, will use 5-model XGBoost ensemble
- Similar to EUR/USD ML ensemble approach

## 📈 Risk Management

- **Position Sizing**: Based on account balance and risk percentage
- **Stop Loss**: 2x ATR from entry price
- **Take Profit**: 3x ATR from entry price
- **Risk/Reward**: 1:1.5 ratio (risk $2 to make $3)
- **Cooldown**: 30 minutes between same-direction trades

## ⚠️ Important Notes

- **Backtest First**: Test on practice account before live trading
- **Monitor Performance**: Check logs regularly
- **Signal Engine**: Currently uses rule-based signals (RSI, MACD, EMA)
- **ML Ready**: Structure is ready for ML ensemble when models are trained
- **Market Conditions**: Bot trades every hour, may miss intraday opportunities

## 📝 Logs

Logs are saved to: `logs/usdjpy_ml_ensemble_YYYYMMDD.log`

## 🔧 Troubleshooting

- **No trades**: Check signal confidence, may be LOW
- **API errors**: Verify OANDA credentials in `.env.live`
- **Import errors**: Ensure Python path includes parent directories

## 🔄 Future: ML Ensemble

When ML models are trained for USD/JPY:
1. Train XGBoost models using `/home/admintrader/tradermain/ml_models/train_usdjpy_model.py` (to be created)
2. Update `strategy_ml_ensemble.py` to use ML signal engine
3. Bot will automatically use ML ensemble predictions

## 📊 Systemd Service

```bash
# View bot logs
# Copy service file
sudo cp /home/myalgo/algo-trader/infra/bot-usdjpy-ml-ensemble.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable bot-usdjpy-ml-ensemble.service

# Start service
sudo systemctl start bot-usdjpy-ml-ensemble.service

# Check status
sudo systemctl status bot-usdjpy-ml-ensemble.service

# Watch logs
sudo journalctl -u bot-usdjpy-ml-ensemble.service -f
```

