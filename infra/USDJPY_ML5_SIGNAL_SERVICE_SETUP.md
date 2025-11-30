# USD/JPY ML5 Signal Service - Systemd Setup

## Service File

**Location:** `/home/myalgo/algo-trader/infra/usdjpy-ml5-signal-service.service`

## Installation

1. **Copy service file to systemd:**
   ```bash
   sudo cp /home/myalgo/algo-trader/infra/usdjpy-ml5-signal-service.service /etc/systemd/system/
   ```

2. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable service to start on boot:**
   ```bash
   sudo systemctl enable usdjpy-ml5-signal-service.service
   ```

4. **Start the service:**
   ```bash
   sudo systemctl start usdjpy-ml5-signal-service.service
   ```

## Management Commands

### Check Status
```bash
sudo systemctl status usdjpy-ml5-signal-service.service
```

### View Logs
```bash
# View all logs
sudo journalctl -u usdjpy-ml5-signal-service.service

# Follow logs in real-time
sudo journalctl -u usdjpy-ml5-signal-service.service -f

# View last 100 lines
sudo journalctl -u usdjpy-ml5-signal-service.service -n 100

# View logs since today
sudo journalctl -u usdjpy-ml5-signal-service.service --since today
```

### Control Service
```bash
# Start
sudo systemctl start usdjpy-ml5-signal-service.service

# Stop
sudo systemctl stop usdjpy-ml5-signal-service.service

# Restart
sudo systemctl restart usdjpy-ml5-signal-service.service

# Reload (graceful restart)
sudo systemctl reload usdjpy-ml5-signal-service.service
```

### Disable/Enable
```bash
# Disable from starting on boot
sudo systemctl disable usdjpy-ml5-signal-service.service

# Enable to start on boot
sudo systemctl enable usdjpy-ml5-signal-service.service
```

## Service Details

- **Service Name:** `usdjpy-ml5-signal-service`
- **Working Directory:** `/home/myalgo/algo-trader/app/services/signal-service/usdjpy-ml5`
- **Executable:** `/home/myalgo/algo-trader/venv/bin/python3 main.py`
- **Restart Policy:** Always restart on failure (10 second delay)
- **Logs:** Systemd journal (view with `journalctl`)

## Dependencies

The service depends on:
- PostgreSQL (database connection)
- Network (for database connectivity)

Service will wait for PostgreSQL to be ready before starting.

## Troubleshooting

### Service won't start
```bash
# Check status for errors
sudo systemctl status usdjpy-ml5-signal-service.service

# Check logs for errors
sudo journalctl -u usdjpy-ml5-signal-service.service -n 50
```

### Service keeps restarting
```bash
# Check logs for crash reasons
sudo journalctl -u usdjpy-ml5-signal-service.service -n 100 | grep -i error
```

### Database connection issues
```bash
# Verify database is running
sudo systemctl status postgresql

# Test database connection manually
psql -U admintrader -d algo_trader -c "SELECT 1;"
```

### Model file issues
```bash
# Verify models exist
ls -la /home/myalgo/algo-trader/ml_models/signal_generator/usdjpy-models/USD_JPY_xgboost_seed*.json

# Should see 5 files: seed43, seed44, seed45, seed46, seed47
```

### Data file issues
```bash
# Verify data file exists
ls -la /home/myalgo/algo-trader/data/h1_data/USD_JPY_H1_20051202_to_20251127.csv
```

## Notes

- The service runs continuously and generates signals every hour
- Logs are also saved to: `/home/myalgo/algo-trader/app/services/signal-service/usdjpy-ml5/logs/`
- Service automatically restarts on failure
- No manual intervention needed once started
- Signals are saved to `ml_signal_history` table with instrument `USD_JPY`

