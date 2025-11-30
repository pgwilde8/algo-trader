# Copy service file
sudo cp /home/myalgo/algo-trader/infra/bot-gbpusd-ml-ensemble.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable bot-gbpusd-ml-ensemble.service

# Start service
sudo systemctl start bot-gbpusd-ml-ensemble.service

# Check status
sudo systemctl status bot-gbpusd-ml-ensemble.service

# Watch logs
sudo journalctl -u bot-gbpusd-ml-ensemble.service -f