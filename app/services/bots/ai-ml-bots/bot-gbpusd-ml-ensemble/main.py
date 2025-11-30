#!/usr/bin/env python3
"""
GBP/USD ML Ensemble Auto Trader
Automated trading bot using XGBoost ensemble signals
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, time as dt_time
from pathlib import Path
import pytz

# Add parent directory to path for imports
REPO_ROOT = "/home/myalgo/algo-trader"
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from strategy_ml_ensemble import GBPUSDMLEnsembleStrategy
from oanda_service import OANDAService

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

UTC = pytz.UTC
log_file = log_dir / f"gbpusd_ml_ensemble_{datetime.now(UTC).strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Eastern Timezone (handles EST/EDT automatically)
EST = pytz.timezone('America/New_York')

def is_trading_hours(now_utc: datetime):
    """
    Check if current time is within trading hours.
    
    Trading hours:
    - Monday 01:30 EST to Friday 13:59 EST
    - No trading on Sunday
    
    Args:
        now_utc: Current UTC datetime
        
    Returns:
        (is_trading, reason) tuple
    """
    # Convert UTC to Eastern Time
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=pytz.UTC)
    
    now_est = now_utc.astimezone(EST)
    weekday = now_est.weekday()  # 0=Monday, 6=Sunday
    current_time = now_est.time()
    
    # Sunday (6) - No trading
    if weekday == 6:
        return False, "Sunday - Market closed"
    
    # Monday (0) - Start trading at 01:30 EST
    if weekday == 0:
        if current_time < dt_time(1, 30):
            return False, f"Monday before 01:30 EST (current: {current_time.strftime('%H:%M')} EST)"
        return True, "Monday trading hours"
    
    # Friday (4) - Stop trading at 13:59 EST
    if weekday == 4:
        if current_time >= dt_time(13, 59):
            return False, f"Friday after 13:59 EST (current: {current_time.strftime('%H:%M')} EST)"
        return True, "Friday trading hours"
    
    # Tuesday (1), Wednesday (2), Thursday (3) - Full trading
    if weekday in [1, 2, 3]:
        return True, "Mid-week trading hours"
    
    # Saturday (5) - No trading
    if weekday == 5:
        return False, "Saturday - Market closed"
    
    return False, "Outside trading hours"

def load_config():
    """Load configuration"""
    config_file = Path(__file__).parent / "config.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Default config
        return {
            "risk_percentage": 2.0,
            "stop_loss_multiplier": 2.0,
            "take_profit_multiplier": 3.0,
            "min_confidence": "MEDIUM",
            "max_positions": 1,
            "cycle_interval_seconds": 3600  # Check every hour (H1 timeframe)
        }

def main():
    """Main bot loop"""
    logger.info("=" * 70)
    logger.info("🤖💷💵 GBP/USD ML ENSEMBLE AUTO TRADER STARTING")
    logger.info("=" * 70)
    
    try:
        # Load environment variables from .env.practice
        from dotenv import load_dotenv
        result = load_dotenv("/home/myalgo/algo-trader/.env.practice", override=True)
        logger.info(f"Loaded .env.practice (override=True): {result}")
        
        # Get OANDA credentials - use practice account
        account_id_gbpusd = os.getenv('OANDA_ACCOUNT_ID_GBPUSD')
        account_id_general = os.getenv('OANDA_ACCOUNT_ID')
        
        if account_id_gbpusd:
            logger.info(f"📋 Found OANDA_ACCOUNT_ID_GBPUSD: {account_id_gbpusd}")
            account_id = account_id_gbpusd
        elif account_id_general:
            logger.info(f"📋 Using OANDA_ACCOUNT_ID: {account_id_general}")
            account_id = account_id_general
        else:
            # Fallback to practice account
            account_id = "101-001-26778453-002"
            logger.info(f"📋 Using fallback practice account: {account_id}")
            
        api_key = os.getenv('OANDA_API_TOKEN') or os.getenv('OANDA_API_KEY')
        mode = os.getenv('OANDA_ENV') or os.getenv('OANDA_MODE', 'practice')
        
        if not account_id:
            logger.error("❌ OANDA_ACCOUNT_ID_GBPUSD or OANDA_ACCOUNT_ID must be set in .env.practice")
            sys.exit(1)
        if not api_key:
            logger.error("❌ OANDA_API_TOKEN or OANDA_API_KEY must be set in .env.practice")
            sys.exit(1)
        
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Mode: {mode}")
        
        # Initialize OANDA service
        oanda = OANDAService(account_id, api_key, mode)
        
        # Load config
        config = load_config()
        
        # Initialize strategy with news avoidance
        from app.utils.simple_news_avoidance import simple_news_avoidance
        strategy = GBPUSDMLEnsembleStrategy(config, oanda, news_avoidance=simple_news_avoidance)
        
        logger.info("✅ Bot initialized successfully")
        logger.info("🔄 Starting trading loop...")
        logger.info(f"⏰ Cycle interval: {config.get('cycle_interval_seconds', 3600)} seconds (1 hour)")
        logger.info("📅 Trading hours: Monday 01:30 EST - Friday 13:59 EST (No Sunday trading)")
        
        # Main loop
        cycle = 0
        cycle_interval = config.get('cycle_interval_seconds', 3600)
        
        while True:
            try:
                cycle += 1
                now = datetime.now(UTC)
                now_est = now.astimezone(EST)
                
                logger.info("=" * 70)
                logger.info(f"🔄 Cycle #{cycle} - {now.strftime('%Y-%m-%d %H:%M:%S UTC')} ({now_est.strftime('%Y-%m-%d %H:%M:%S %Z')})")
                
                # Check if we're in trading hours
                is_trading, reason = is_trading_hours(now)
                
                if not is_trading:
                    logger.info(f"⏸️  Outside trading hours: {reason}")
                    logger.info(f"⏳ Sleeping for {cycle_interval} seconds until next cycle...")
                    time.sleep(cycle_interval)
                    continue
                
                logger.info(f"✅ Trading hours active: {reason}")
                
                # Run strategy cycle
                strategy.run_cycle()
                
                # Sleep until next cycle
                logger.info(f"⏳ Sleeping for {cycle_interval} seconds until next cycle...")
                time.sleep(cycle_interval)
                
            except KeyboardInterrupt:
                logger.info("⚠️ Keyboard interrupt - shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}", exc_info=True)
                logger.info(f"⏳ Waiting 60 seconds before retrying...")
                time.sleep(60)
                
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("🛑 GBP/USD ML ENSEMBLE AUTO TRADER STOPPED")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()

