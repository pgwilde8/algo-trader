"""
EUR/USD Signal Engine Helper
Gets the latest signal from the database for the trading bot
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict
import logging

# Add repo root to path
REPO_ROOT = "/home/myalgo/algo-trader"
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.db import SyncSessionLocal
from app.models.ml_signal_history import MLSignalHistory

logger = logging.getLogger(__name__)


def get_current_signal(instrument: str = "EUR_USD") -> Optional[Dict]:
    """
    Get the latest valid signal from the database
    
    Args:
        instrument: Trading instrument (default: "EUR_USD")
        
    Returns:
        Signal dict with direction, confidence, entry_price, etc. or None
    """
    try:
        db: Session = SyncSessionLocal()
        try:
            # Get latest signal for instrument
            stmt = select(MLSignalHistory).where(
                MLSignalHistory.instrument == instrument
            ).order_by(MLSignalHistory.timestamp.desc()).limit(1)
            
            result = db.execute(stmt)
            latest_signal = result.scalar_one_or_none()
            
            if not latest_signal:
                logger.warning(f"No signal found for {instrument}")
                return None
            
            # Check if signal is still valid
            now = datetime.now(timezone.utc)
            if latest_signal.valid_until and now > latest_signal.valid_until:
                logger.warning(f"Latest signal expired at {latest_signal.valid_until}")
                return None
            
            # Convert to dict format expected by bot
            signal = {
                "direction": latest_signal.direction,
                "confidence": latest_signal.confidence,
                "ml_probability": float(latest_signal.ml_probability),
                "entry_price": float(latest_signal.entry_price),
                "timestamp": latest_signal.timestamp.isoformat() if latest_signal.timestamp else None,
                "valid_until": latest_signal.valid_until.isoformat() if latest_signal.valid_until else None,
                "ensemble_size": int(latest_signal.ensemble_size) if latest_signal.ensemble_size else 5,
            }
            
            # Add indicators if available
            if latest_signal.indicators:
                signal["indicators"] = latest_signal.indicators
            
            # Add individual model predictions if available
            if latest_signal.individual_models:
                signal["individual_models"] = latest_signal.individual_models
            
            logger.debug(f"Retrieved signal: {signal['direction']} ({signal['confidence']}, prob={signal['ml_probability']:.3f})")
            return signal
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting current signal: {e}", exc_info=True)
        return None

