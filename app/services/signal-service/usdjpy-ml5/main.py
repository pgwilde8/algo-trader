#!/usr/bin/env python3
"""
USD/JPY ML5 Ensemble Signal Service
Generates ML signals and saves them to the database
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
import pytz

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from signal_engine import generate_and_save_signal
from sqlalchemy.orm import Session
from sqlalchemy import select

# Database imports
from app.db.db import sync_engine, SyncSessionLocal
from app.models.ml_signal_history import MLSignalHistory

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

UTC = pytz.UTC
log_file = log_dir / f"usdjpy_ml5_signal_service_{datetime.now(UTC).strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration"""
    config_file = Path(__file__).parent / "config.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Default config
        return {
            "instrument": "USD_JPY",
            "cycle_interval_seconds": 3600,  # Check every hour (H1 timeframe)
            "description": "USD/JPY ML5 Ensemble Signal Service - Generates signals using 5-model XGBoost ensemble"
        }


def save_signal_to_database(signal: dict) -> bool:
    """
    Save signal to database (ml_signal_history table)
    Returns True if saved successfully, False otherwise
    """
    try:
        # Create database session
        db: Session = SyncSessionLocal()
        
        try:
            # Parse timestamp and valid_until
            timestamp = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
            valid_until = None
            if signal.get('valid_until'):
                valid_until = datetime.fromisoformat(signal['valid_until'].replace('Z', '+00:00'))
            
            # Create MLSignalHistory record
            signal_record = MLSignalHistory(
                instrument=signal['instrument'],
                direction=signal['direction'],
                confidence=signal['confidence'],
                confidence_score=float(signal.get('confidence_score', 0)),
                ml_probability=float(signal['ml_probability']),
                entry_price=float(signal['entry_price']),
                ensemble_size=int(signal.get('ensemble_size', 0)) if signal.get('ensemble_size') else None,
                individual_models=signal.get('individual_models'),  # JSONB
                indicators=signal.get('indicators'),  # JSONB
                timestamp=timestamp,
                valid_until=valid_until
            )
            
            # Add and commit
            db.add(signal_record)
            db.commit()
            db.refresh(signal_record)
            
            logger.info(f"✅ Signal saved to database (ID: {signal_record.id})")
            logger.info(f"   Direction: {signal['direction']}, Confidence: {signal['confidence']}, Prob: {signal['ml_probability']:.3f}")
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving signal to database: {e}", exc_info=True)
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}", exc_info=True)
        return False


def should_generate_new_signal(db: Session) -> bool:
    """
    Check if we need to generate a new signal
    Returns True if no recent valid signal exists
    """
    try:
        # Check for most recent signal for USD/JPY
        stmt = select(MLSignalHistory).where(
            MLSignalHistory.instrument == "USD_JPY"
        ).order_by(MLSignalHistory.timestamp.desc()).limit(1)
        
        result = db.execute(stmt)
        latest_signal = result.scalar_one_or_none()
        
        if not latest_signal:
            logger.info("No previous signals found, generating new signal")
            return True
        
        # Check if signal is still valid
        now = datetime.now(timezone.utc)
        if latest_signal.valid_until and now < latest_signal.valid_until:
            logger.info(f"Latest signal still valid until {latest_signal.valid_until}, skipping generation")
            return False
        
        logger.info(f"Latest signal expired, generating new signal")
        return True
        
    except Exception as e:
        logger.error(f"Error checking for existing signals: {e}", exc_info=True)
        return True  # Generate signal if check fails


def main():
    """Main signal service loop"""
    logger.info("=" * 70)
    logger.info("📡💵💴 USD/JPY ML5 ENSEMBLE SIGNAL SERVICE STARTING")
    logger.info("=" * 70)
    
    try:
        # Load config
        config = load_config()
        instrument = config.get("instrument", "USD_JPY")
        cycle_interval = config.get("cycle_interval_seconds", 3600)
        
        logger.info(f"Instrument: {instrument}")
        logger.info(f"Cycle interval: {cycle_interval} seconds ({cycle_interval/3600:.1f} hours)")
        logger.info("✅ Signal service initialized successfully")
        logger.info("🔄 Starting signal generation loop...")
        
        # Main loop
        cycle = 0
        
        while True:
            try:
                cycle += 1
                now = datetime.now(UTC)
                
                logger.info("=" * 70)
                logger.info(f"🔄 Cycle #{cycle} - {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                # Check if we need to generate a new signal
                db: Session = SyncSessionLocal()
                try:
                    should_generate = should_generate_new_signal(db)
                finally:
                    db.close()
                
                if should_generate:
                    # Generate signal
                    logger.info("🔄 Generating new ML signal...")
                    signal = generate_and_save_signal()
                    
                    if signal:
                        # Save to database
                        logger.info("💾 Saving signal to database...")
                        saved = save_signal_to_database(signal)
                        
                        if saved:
                            logger.info("✅ Signal generated and saved successfully")
                        else:
                            logger.error("❌ Failed to save signal to database")
                    else:
                        logger.error("❌ Failed to generate signal")
                else:
                    logger.info("⏭️  Skipping signal generation (latest signal still valid)")
                
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
    logger.info("🛑 USD/JPY ML5 ENSEMBLE SIGNAL SERVICE STOPPED")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

