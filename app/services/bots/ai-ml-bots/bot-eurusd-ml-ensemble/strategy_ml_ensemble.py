"""
EUR/USD ML Ensemble Trading Strategy
Uses XGBoost ensemble signals to place trades
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict
import json

# Add parent directories to path
REPO_ROOT = "/home/myalgo/algo-trader"
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "app" / "services"))

from oanda_service import OANDAService
from eurusd_signal_engine import get_current_signal
from app.utils.simple_news_avoidance import simple_news_avoidance

logger = logging.getLogger(__name__)

class EURUSDMLEnsembleStrategy:
    """Trading strategy using ML ensemble signals"""
    
    def __init__(self, config: dict, oanda: OANDAService, news_avoidance=None):
        self.config = config
        self.oanda = oanda
        self.news_avoidance = news_avoidance or simple_news_avoidance
        self.instrument = "EUR_USD"
        self.last_signal_direction = None
        self.last_trade_time = None
        
        # Risk management
        self.risk_percentage = config.get("risk_percentage", 2.0)  # Risk 2% per trade
        self.stop_loss_multiplier = config.get("stop_loss_multiplier", 2.0)  # 2x ATR for stop loss
        self.take_profit_multiplier = config.get("take_profit_multiplier", 3.0)  # 3x ATR for take profit
        self.min_confidence = config.get("min_confidence", "MEDIUM")  # Only trade MEDIUM+ confidence
        
        # Position management
        self.max_positions = config.get("max_positions", 1)  # Only 1 position at a time
        
        logger.info(f"Strategy initialized:")
        logger.info(f"  Risk per trade: {self.risk_percentage}%")
        logger.info(f"  Stop loss: {self.stop_loss_multiplier}x ATR")
        logger.info(f"  Take profit: {self.take_profit_multiplier}x ATR")
        logger.info(f"  Min confidence: {self.min_confidence}+")
        logger.info(f"  News avoidance: {'Enabled' if self.news_avoidance else 'Disabled'}")
    
    def get_ml_signal(self) -> Optional[Dict]:
        """Get current ML ensemble signal"""
        try:
            signal = get_current_signal()
            return signal
        except Exception as e:
            logger.error(f"Error getting ML signal: {e}", exc_info=True)
            return None
    
    def should_trade(self, signal: Dict) -> bool:
        """Determine if we should trade based on signal"""
        if not signal:
            return False
        
        direction = signal.get("direction")
        confidence = signal.get("confidence", "LOW")
        
        # Don't trade NEUTRAL signals
        if direction == "NEUTRAL":
            logger.debug("Signal is NEUTRAL, skipping trade")
            return False
        
        # Check news avoidance - stop new trades before news
        if self.news_avoidance:
            try:
                avoid_check = self.news_avoidance.should_avoid_trading(self.instrument)
                if avoid_check.get("avoid_trading", False):
                    logger.info(f"⏸️ Avoiding trade due to news: {avoid_check.get('reason')}")
                    return False
            except Exception as e:
                logger.warning(f"News avoidance check failed: {e}")
        
        # Check confidence level
        confidence_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        min_level = confidence_levels.get(self.min_confidence, 2)
        signal_level = confidence_levels.get(confidence, 0)
        
        if signal_level < min_level:
            logger.debug(f"Signal confidence {confidence} below minimum {self.min_confidence}")
            return False
        
        # Check if we already have a position
        open_trades = self.oanda.get_open_trades(self.instrument)
        if open_trades and len(open_trades) >= self.max_positions:
            logger.debug(f"Already have {len(open_trades)} position(s), max is {self.max_positions}")
            return False
        
        # Check same-direction cooldown
        if self.last_signal_direction == direction:
            if self.last_trade_time:
                time_since_last = (datetime.now(timezone.utc) - self.last_trade_time).total_seconds()
                cooldown = self.config.get("same_direction_cooldown", 1800)  # 30 mins default
                if time_since_last < cooldown:
                    logger.info(f"Skipping same-direction re-entry due to cooldown. Time since last: {time_since_last:.0f}s < {cooldown}s")
                    return False
        
        return True
    
    def calculate_stop_loss_take_profit(self, entry_price: float, direction: str, atr: float) -> tuple:
        """Calculate stop loss and take profit based on ATR"""
        stop_distance = atr * self.stop_loss_multiplier
        profit_distance = atr * self.take_profit_multiplier
        
        if direction == "BUY":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + profit_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - profit_distance
        
        return stop_loss, take_profit
    
    def calculate_stop_loss_pips(self, entry_price: float, stop_loss: float) -> float:
        """Calculate stop loss in pips for EUR/USD"""
        # EUR/USD: 1 pip = 0.0001
        pips = abs(entry_price - stop_loss) / 0.0001
        return pips
    
    def place_trade(self, signal: Dict) -> bool:
        """Place a trade based on ML signal"""
        try:
            direction = signal.get("direction")
            entry_price = signal.get("entry_price")
            confidence = signal.get("confidence")
            ml_prob = signal.get("ml_probability", 0.5)
            indicators = signal.get("indicators", {})
            atr = indicators.get("atr")
            
            if not entry_price:
                logger.error("No entry price in signal")
                return False
            
            if not atr:
                logger.warning("No ATR in signal, using default 0.0010")
                atr = 0.0010  # Default ATR for EUR/USD
            
            # Get current market price
            price_data = self.oanda.get_current_price(self.instrument)
            if not price_data:
                logger.error("Could not get current price")
                return False
            
            # Use ask for BUY, bid for SELL
            if direction == "BUY":
                current_price = float(price_data.get("asks", [{}])[0].get("price", entry_price))
            else:
                current_price = float(price_data.get("bids", [{}])[0].get("price", entry_price))
            
            # Calculate stop loss and take profit
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(
                current_price, direction, atr
            )
            
            # Calculate position size
            account = self.oanda.get_account_summary()
            if not account:
                logger.error("Could not get account summary")
                return False
            
            balance = float(account.get("balance", 0))
            stop_loss_pips = self.calculate_stop_loss_pips(current_price, stop_loss)
            units = self.oanda.calculate_position_size(balance, self.risk_percentage, stop_loss_pips)
            
            if units < 1000:
                logger.warning(f"Position size too small: {units} units")
                return False
            
            # Determine units sign (positive for BUY, negative for SELL)
            units_signed = units if direction == "BUY" else -units
            
            logger.info(f"📊 Trade Setup:")
            logger.info(f"  Direction: {direction}")
            logger.info(f"  Entry: {current_price:.5f}")
            logger.info(f"  Stop Loss: {stop_loss:.5f} ({stop_loss_pips:.1f} pips)")
            logger.info(f"  Take Profit: {take_profit:.5f}")
            logger.info(f"  Units: {units_signed}")
            logger.info(f"  Confidence: {confidence} (ML prob: {ml_prob:.3f})")
            logger.info(f"  Risk: ${balance * (self.risk_percentage / 100):.2f} ({self.risk_percentage}%)")
            
            # Place order
            result = self.oanda.place_market_order(
                instrument=self.instrument,
                units=units_signed,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_tag=f"ML-Ensemble-{direction}-{confidence}"
            )
            
            if result:
                logger.info(f"✅ Trade placed successfully!")
                self.last_trade_time = datetime.now(timezone.utc)
                self.last_signal_direction = direction
                return True
            else:
                logger.error("❌ Failed to place trade")
                return False
                
        except Exception as e:
            logger.error(f"Error placing trade: {e}", exc_info=True)
            return False
    
    def run_cycle(self):
        """Run one trading cycle"""
        try:
            logger.info("-" * 60)
            logger.info("🔄 Running ML Ensemble Strategy Cycle")
            
            # Check if positions should be closed before news
            if self.news_avoidance:
                try:
                    close_check = self.news_avoidance.should_close_positions(self.instrument)
                    if close_check.get("close_positions", False):
                        logger.warning(f"🚨 Closing positions due to news: {close_check.get('reason')}")
                        open_trades = self.oanda.get_open_trades(self.instrument)
                        if open_trades:
                            for trade in open_trades:
                                self.oanda.close_trade(trade["id"])
                                logger.info(f"✅ Closed trade {trade['id']} before news event")
                except Exception as e:
                    logger.warning(f"Position close check failed: {e}")
            
            # Get ML signal
            signal = self.get_ml_signal()
            if not signal:
                logger.warning("⚠️  Could not get ML signal")
                return
            
            direction = signal.get("direction", "NEUTRAL")
            confidence = signal.get("confidence", "LOW")
            ml_prob = signal.get("ml_probability", 0.5)
            ensemble_size = signal.get("ensemble_size", 0)
            
            logger.info(f"📡 ML Signal: {direction} ({confidence}, prob={ml_prob:.3f}, ensemble={ensemble_size})")
            
            # Check if we should trade
            if not self.should_trade(signal):
                logger.info("⏭️  Skipping trade (conditions not met)")
                return
            
            # Place trade
            logger.info(f"🚀 Attempting to place {direction} trade...")
            self.place_trade(signal)
            
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}", exc_info=True)

