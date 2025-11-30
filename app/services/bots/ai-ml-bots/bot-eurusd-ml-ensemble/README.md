# EUR/USD ML Ensemble Auto Trader

Automated trading bot that uses XGBoost ensemble ML signals to place trades on EUR/USD.

## 🎯 Features

- **ML-Powered Signals**: Uses 5-model XGBoost ensemble for predictions
- **Risk Management**: Configurable risk percentage per trade (default 2%)
- **ATR-Based Stops**: Stop loss and take profit based on ATR (Average True Range)
- **Confidence Filtering**: Only trades MEDIUM+ confidence signals
- **Position Management**: Maximum 1 position at a time
- **H1 Timeframe**: Checks signals every hour (H1 timeframe)

## 📁 Files

- `main.py` - Main bot runner
- `strategy_ml_ensemble.py` - Trading strategy using ML signals
- `oanda_service.py` - OANDA API service
- `config.json` - Configuration file
- `README.md` - This file

## ⚙️ Configuration

Edit `config.json`:

```json
{
  "risk_percentage": 2.0,           // Risk 2% of account per trade
  "stop_loss_multiplier": 2.0,      // Stop loss = 2x ATR
  "take_profit_multiplier": 3.0,    // Take profit = 3x ATR
  "min_confidence": "MEDIUM",       // Only trade MEDIUM+ confidence
  "max_positions": 1,               // Maximum 1 position at a time
  "cycle_interval_seconds": 3600    // Check every hour
}
```

## 🚀 Setup

1. **Environment Variables** (in `.env.live`):
   ```bash
   OANDA_ACCOUNT_ID_EURUSD=your_account_id
   OANDA_API_TOKEN=your_api_token
   OANDA_ENV=live  # or 'practice'
   ```

2. **Run Bot**:
   ```bash
   cd /home/admintrader/tradermain/bots/bot-eurusd-ml-ensemble
   python3 main.py
   ```

## 📊 How It Works

1. **Signal Generation**: Bot gets ML ensemble signal from `eurusd_signal_engine.py`
2. **Signal Validation**: Checks confidence level (MEDIUM+ required)
3. **Position Check**: Verifies no existing positions
4. **Risk Calculation**: Calculates position size based on risk percentage
5. **Stop/Target**: Sets stop loss (2x ATR) and take profit (3x ATR)
6. **Trade Execution**: Places market order via OANDA API

## 🎯 Trading Logic

- **BUY Signal**: When ML probability > 0.6 (60%+ chance price goes UP)
- **SELL Signal**: When ML probability < 0.4 (60%+ chance price goes DOWN)
- **NEUTRAL**: When ML probability 0.4-0.6 (uncertain, no trade)

**Confidence Levels:**
- **HIGH**: All 5 models agree strongly (>0.75 or <0.25 probability)
- **MEDIUM**: Models mostly agree (0.6-0.75 or 0.25-0.4 probability)
- **LOW**: Models uncertain (0.4-0.6 probability) - **NOT TRADED**

## 📈 Risk Management

- **Position Sizing**: Based on account balance and risk percentage
- **Stop Loss**: 2x ATR from entry price
- **Take Profit**: 3x ATR from entry price
- **Risk/Reward**: 1:1.5 ratio (risk $2 to make $3)

## ⚠️ Important Notes

- **Backtest First**: Test on practice account before live trading
- **Monitor Performance**: Check logs regularly
- **Signal Quality**: Current ML model accuracy ~52.5% - monitor closely
- **Market Conditions**: Bot trades every hour, may miss intraday opportunities

## 📝 Logs

Logs are saved to: `logs/eurusd_ml_ensemble_YYYYMMDD.log`

## 🔧 Troubleshooting

- **No trades**: Check signal confidence, may be LOW
- **API errors**: Verify OANDA credentials in `.env.live`
- **Import errors**: Ensure Python path includes parent directories

# Copy service file to systemd
sudo cp /home/myalgo/algo-trader/infra/bot-eurusd-ml-ensemble.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable bot-eurusd-ml-ensemble.service

# Start the service
sudo systemctl start bot-eurusd-ml-ensemble.service

# Check status
sudo systemctl status bot-eurusd-ml-ensemble.service

# Watch logs in real-time
sudo journalctl -u bot-eurusd-ml-ensemble.service -f

# View recent logs (last 50 lines)
sudo journalctl -u bot-eurusd-ml-ensemble.service -n 50

# View logs since today
sudo journalctl -u bot-eurusd-ml-ensemble.service --since today

# View log files directly
tail -f /home/myalgo/algo-trader/app/services/bots/ai-ml-bots/bot-eurusd-ml-ensemble/logs/eurusd_ml_ensemble_*.log

# Stop the service
sudo systemctl stop bot-eurusd-ml-ensemble.service

# Restart the service
sudo systemctl restart bot-eurusd-ml-ensemble.service

# Disable from starting on boot
sudo systemctl disable bot-eurusd-ml-ensemble.service

sudo journalctl -u bot-eurusd-ml-ensemble.service -f
sudo systemctl status bot-eurusd-ml-ensemble.service