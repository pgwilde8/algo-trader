#!/bin/bash
# Setup script for MyAlgo Trader

set -e

echo "🚀 Setting up MyAlgo Trader..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration!"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your settings"
echo "2. Set up systemd service: sudo cp infra/myalgo-trader.service /etc/systemd/system/"
echo "3. Set up nginx: sudo cp infra/myalgo-trader.nginx.conf /etc/nginx/sites-available/"
echo "4. Start the service: sudo systemctl start myalgo-trader.service"

