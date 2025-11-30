# Check if service exists
sudo systemctl status gbpusd-ml5-signal-service.service

# Check if it's enabled (auto-start on boot)
sudo systemctl is-enabled gbpusd-ml5-signal-service.service

# If not enabled, enable it
sudo systemctl enable gbpusd-ml5-signal-service.service

# Start the service
sudo systemctl start gbpusd-ml5-signal-service.service

# Check logs to see if it's working
sudo journalctl -u gbpusd-ml5-signal-service.service -f

# 1. Copy the service file to systemd directory
sudo cp /home/myalgo/algo-trader/infra/gbpusd-ml5-signal-service.service /etc/systemd/system/

# 2. Reload systemd to recognize the new service
sudo systemctl daemon-reload

# 3. Enable the service (auto-start on boot)
sudo systemctl enable gbpusd-ml5-signal-service.service

# 4. Start the service
sudo systemctl start gbpusd-ml5-signal-service.service

# 5. Check the status
sudo systemctl status gbpusd-ml5-signal-service.service

# 6. View logs to see if it's working
sudo journalctl -u gbpusd-ml5-signal-service.service -f