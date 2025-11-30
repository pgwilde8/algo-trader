import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import pytz

logger = logging.getLogger(__name__)

class SimpleNewsAvoidanceService:
    """
    Simple file-based news avoidance service.
    Stores news events in a JSON file instead of database.
    """
    
    def __init__(self, 
                 data_file: str = "/home/myalgo/algo-trader/data/news_events.json",
                 minutes_before: int = 30,
                 minutes_after: int = 60,
                 minutes_before_close: int = 3):
        """
        Initialize the simple news avoidance service.
        
        Args:
            data_file: Path to JSON file storing news events
            minutes_before: Minutes before news to stop NEW trades (default: 30)
            minutes_after: Minutes after news to resume trading (default: 60)
            minutes_before_close: Minutes before news to CLOSE all positions (default: 3)
        """
        self.data_file = Path(data_file)
        self.minutes_before = minutes_before
        self.minutes_after = minutes_after
        self.minutes_before_close = minutes_before_close
        
        # Ensure data directory exists (handle gracefully)
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize file if it doesn't exist
            if not self.data_file.exists():
                self._initialize_file()
            else:
                # Load settings from file to override defaults
                try:
                    data = self._load_data()
                    if "settings" in data:
                        settings = data["settings"]
                        if "minutes_before" in settings:
                            self.minutes_before = settings["minutes_before"]
                        if "minutes_after" in settings:
                            self.minutes_after = settings["minutes_after"]
                        if "minutes_before_close" in settings:
                            self.minutes_before_close = settings["minutes_before_close"]
                except Exception as e:
                    logger.warning(f"Could not load settings from file: {e}, using defaults")
        except Exception as e:
            logger.warning(f"Could not create data directory {self.data_file.parent}: {e}")
            # Continue without file-based news avoidance
            
        # Set timezone for EST/EDT
        self.eastern_tz = pytz.timezone('America/New_York')
            
        logger.info(f"Simple news avoidance service initialized with file: {self.data_file}")
        logger.info(f"Settings: {self.minutes_before} min before, {self.minutes_after} min after, {self.minutes_before_close} min before close")
    
    def _initialize_file(self):
        """Initialize the JSON file with default structure."""
        default_data = {
            "events": [],
            "settings": {
                "minutes_before": self.minutes_before,
                "minutes_after": self.minutes_after,
                "minutes_before_close": self.minutes_before_close,
                "enabled": True
            }
        }
        
        with open(self.data_file, 'w') as f:
            json.dump(default_data, f, indent=2, default=str)
        
        logger.info(f"Initialized news events file: {self.data_file}")
    
    def _load_data(self) -> Dict[str, Any]:
        """Load news events from JSON file."""
        try:
            if not self.data_file.exists():
                return {"events": [], "settings": {"minutes_before": 30, "minutes_after": 60, "minutes_before_close": 3, "enabled": True}}
                
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Convert string timestamps back to datetime objects
            for event in data.get("events", []):
                if isinstance(event.get("event_time"), str):
                    # Handle timezone conversion
                    event_time_str = event["event_time"]
                    if event_time_str.endswith('Z'):
                        # UTC time (explicit)
                        event["event_time"] = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                    elif '+' in event_time_str or (event_time_str.count('-') > 2):
                        # Timezone-aware time (e.g., 2025-11-20T13:30:00+00:00 or -05:00)
                        event["event_time"] = datetime.fromisoformat(event_time_str)
                    else:
                        # Timezone-naive time - assume UTC (since we store UTC times as timezone-naive)
                        naive_dt = datetime.fromisoformat(event_time_str)
                        if naive_dt.tzinfo is None:
                            # Treat as UTC since that's how we store them from the admin form
                            event["event_time"] = naive_dt.replace(tzinfo=timezone.utc)
                        else:
                            event["event_time"] = naive_dt
                        
                if isinstance(event.get("created_at"), str):
                    event["created_at"] = datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
            
            # Load settings from file and update instance variables
            if "settings" in data:
                settings = data["settings"]
                if "minutes_before" in settings:
                    self.minutes_before = settings["minutes_before"]
                if "minutes_after" in settings:
                    self.minutes_after = settings["minutes_after"]
                if "minutes_before_close" in settings:
                    self.minutes_before_close = settings["minutes_before_close"]
            
            return data
        except Exception as e:
            logger.error(f"Error loading news data: {e}")
            return {"events": [], "settings": {"minutes_before": 30, "minutes_after": 60, "minutes_before_close": 3, "enabled": True}}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save news events to JSON file."""
        try:
            # Ensure directory exists before saving
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
            logger.debug("News data saved successfully")
        except Exception as e:
            logger.error(f"Error saving news data: {e}")
            # Don't raise - just log the error
    
    def add_news_event(self, 
                      title: str, 
                      currency: str, 
                      event_time: datetime, 
                      impact: str = "high") -> Dict[str, Any]:
        """
        Add a new news event.
        
        Args:
            title: Event title (e.g., "Non-Farm Payrolls")
            currency: Currency affected (e.g., "USD")
            event_time: When the event occurs
            impact: Impact level ("high", "medium", "low")
            
        Returns:
            Created event dictionary
        """
        try:
            data = self._load_data()
            
            # Generate new ID
            new_id = max([event.get("id", 0) for event in data.get("events", [])], default=0) + 1
            
            # Create new event
            new_event = {
                "id": new_id,
                "title": title,
                "currency": currency.upper(),
                "event_time": event_time,
                "impact": impact,
                "created_at": datetime.utcnow()
            }
            
            # Add to events list
            data["events"].append(new_event)
            
            # Save back to file
            self._save_data(data)
            
            logger.info(f"Added news event: {title} at {event_time} for {currency}")
            return new_event
            
        except Exception as e:
            logger.error(f"Error adding news event: {e}")
            raise
    
    def get_upcoming_news(self, 
                         hours_ahead: int = 24, 
                         currency: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get upcoming high-impact news events.
        
        Args:
            hours_ahead: How many hours ahead to check
            currency: Specific currency to filter by (optional)
            
        Returns:
            List of upcoming news events
        """
        try:
            data = self._load_data()
            now = datetime.now(timezone.utc)
            end_time = now + timedelta(hours=hours_ahead)
            
            upcoming_events = []
            
            for event in data.get("events", []):
                # Ensure event_time is timezone-aware UTC for comparison
                event_time = event["event_time"]
                if isinstance(event_time, datetime):
                    if event_time.tzinfo is None:
                        # Timezone-naive - assume UTC
                        event_time = event_time.replace(tzinfo=timezone.utc)
                    else:
                        # Convert to UTC if it has timezone info
                        event_time = event_time.astimezone(timezone.utc)
                else:
                    # Skip if not a datetime
                    continue
                
                # Check if event is in the future and within time range
                if (event_time >= now and 
                    event_time <= end_time and
                    event["impact"] == "high"):
                    
                    # Filter by currency if specified
                    if currency and event["currency"] != currency.upper():
                        continue
                    
                    # Add minutes until event
                    event_copy = event.copy()
                    event_copy["event_time"] = event_time
                    event_copy["minutes_until"] = int((event_time - now).total_seconds() / 60)
                    upcoming_events.append(event_copy)
            
            # Sort by event time
            upcoming_events.sort(key=lambda x: x["event_time"])
            
            logger.info(f"Found {len(upcoming_events)} upcoming high-impact news events")
            return upcoming_events
            
        except Exception as e:
            logger.error(f"Error getting upcoming news: {e}")
            return []
    
    def should_close_positions(self, currency_pair: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if existing positions should be CLOSED due to imminent news.
        
        This is called BEFORE should_avoid_trading to close positions early
        and lock in profits before news volatility.
        
        Args:
            currency_pair: Trading pair being considered (e.g., "USD_JPY")
            
        Returns:
            Dictionary with close decision and details
        """
        try:
            data = self._load_data()
            
            # Check if news avoidance is enabled
            if not data.get("settings", {}).get("enabled", True):
                return {
                    "close_positions": False,
                    "reason": "News avoidance disabled",
                    "next_event": None
                }
            
            now = datetime.now(timezone.utc)
            # Check only for upcoming events within the close window
            end_check = now + timedelta(minutes=self.minutes_before_close)
            
            # Get relevant currencies from trading pair
            relevant_currencies = self._extract_currencies_from_pair(currency_pair)
            
            # Check for imminent events
            imminent_event = None
            
            for event in data.get("events", []):
                # Ensure event_time is timezone-aware UTC for comparison
                event_time = event["event_time"]
                if isinstance(event_time, datetime):
                    if event_time.tzinfo is None:
                        # Timezone-naive - assume UTC
                        event_time = event_time.replace(tzinfo=timezone.utc)
                    else:
                        # Convert to UTC if it has timezone info
                        event_time = event_time.astimezone(timezone.utc)
                else:
                    # Skip if not a datetime
                    continue
                
                # Only check future events within the close window
                if (event_time > now and 
                    event_time <= end_check and
                    event["impact"] == "high"):
                    
                    # Check if event affects the trading pair
                    if relevant_currencies and event["currency"] not in relevant_currencies:
                        continue
                    
                    # Get the closest imminent event
                    event_copy = event.copy()
                    event_copy["event_time"] = event_time
                    if not imminent_event or event_time < imminent_event["event_time"]:
                        imminent_event = event_copy
            
            # If imminent event found, signal to close positions
            if imminent_event:
                minutes_until = int((imminent_event["event_time"] - now).total_seconds() / 60)
                return {
                    "close_positions": True,
                    "reason": f"Close positions before {imminent_event['title']} in {minutes_until} min",
                    "next_event": {
                        "title": imminent_event["title"],
                        "currency": imminent_event["currency"],
                        "event_time": imminent_event["event_time"],
                        "minutes_until": minutes_until
                    }
                }
            
            return {
                "close_positions": False,
                "reason": "No imminent news events",
                "next_event": None
            }
            
        except Exception as e:
            logger.error(f"Error checking position close: {e}")
            # Don't force close on errors
            return {
                "close_positions": False,
                "reason": f"Error checking news events: {e}",
                "next_event": None
            }
    
    def should_avoid_trading(self, currency_pair: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if trading should be avoided right now.
        
        Args:
            currency_pair: Trading pair being considered (e.g., "USD_JPY")
            
        Returns:
            Dictionary with avoidance decision and details
        """
        try:
            data = self._load_data()
            
            # Check if news avoidance is enabled
            if not data.get("settings", {}).get("enabled", True):
                return {
                    "avoid_trading": False,
                    "reason": "News avoidance disabled",
                    "next_event": None,
                    "safe_to_trade_at": None
                }
            
            now = datetime.now(timezone.utc)
            start_check = now - timedelta(minutes=self.minutes_after)
            end_check = now + timedelta(minutes=self.minutes_before)
            
            # Get relevant currencies from trading pair
            relevant_currencies = self._extract_currencies_from_pair(currency_pair)
            
            # Check for events in the avoidance window
            current_event = None
            next_event = None
            
            for event in data.get("events", []):
                # Ensure event_time is timezone-aware UTC for comparison
                event_time = event["event_time"]
                if isinstance(event_time, datetime):
                    if event_time.tzinfo is None:
                        # Timezone-naive - assume UTC
                        event_time = event_time.replace(tzinfo=timezone.utc)
                    else:
                        # Convert to UTC if it has timezone info
                        event_time = event_time.astimezone(timezone.utc)
                else:
                    # Skip if not a datetime
                    continue
                
                # Now compare with UTC-aware datetimes
                if (event_time >= start_check and 
                    event_time <= end_check and
                    event["impact"] == "high"):
                    
                    # Check if event affects the trading pair
                    if relevant_currencies and event["currency"] not in relevant_currencies:
                        continue
                    
                    # Use the normalized event_time for comparisons
                    if event_time <= now:
                        # Past event, check if still in post-news waiting period
                        time_since = (now - event_time).total_seconds() / 60
                        if time_since <= self.minutes_after:
                            # Create a copy of event with normalized time for consistency
                            event_copy = event.copy()
                            event_copy["event_time"] = event_time
                            current_event = event_copy
                    else:
                        # Future event, check if in pre-news avoidance period
                        time_until = (event_time - now).total_seconds() / 60
                        if time_until <= self.minutes_before:
                            # Create a copy of event with normalized time for consistency
                            event_copy = event.copy()
                            event_copy["event_time"] = event_time
                            if not next_event or event_time < next_event["event_time"]:
                                next_event = event_copy
            
            # Determine avoidance decision
            if current_event:
                safe_time = current_event["event_time"] + timedelta(minutes=self.minutes_after)
                logger.info(f"🚫 News avoidance ACTIVE (post-news): {current_event['title']} - {current_event['currency']}")
                return {
                    "avoid_trading": True,
                    "reason": f"Post-news waiting period for {current_event['title']}",
                    "current_event": {
                        "title": current_event["title"],
                        "currency": current_event["currency"],
                        "event_time": current_event["event_time"],
                        "minutes_ago": int((now - current_event["event_time"]).total_seconds() / 60)
                    },
                    "safe_to_trade_at": safe_time
                }
            elif next_event:
                safe_time = next_event["event_time"] + timedelta(minutes=self.minutes_after)
                minutes_until = int((next_event["event_time"] - now).total_seconds() / 60)
                logger.info(f"🚫 News avoidance ACTIVE (pre-news): {next_event['title']} - {next_event['currency']} in {minutes_until} min")
                return {
                    "avoid_trading": True,
                    "reason": f"Pre-news avoidance for {next_event['title']}",
                    "next_event": {
                        "title": next_event["title"],
                        "currency": next_event["currency"],
                        "event_time": next_event["event_time"],
                        "minutes_until": minutes_until
                    },
                    "safe_to_trade_at": safe_time
                }
            
            return {
                "avoid_trading": False,
                "reason": "No active news avoidance periods",
                "next_event": None,
                "safe_to_trade_at": None
            }
            
        except Exception as e:
            logger.error(f"Error checking trading avoidance: {e}")
            # Err on the side of caution
            return {
                "avoid_trading": True,
                "reason": f"Error checking news events: {e}",
                "next_event": None,
                "safe_to_trade_at": None
            }
    
    def _extract_currencies_from_pair(self, currency_pair: Optional[str]) -> List[str]:
        """Extract currencies from a trading pair."""
        if not currency_pair:
            return []
        
        pair = currency_pair.upper().replace("/", "").replace("-", "").replace("_", "")
        
        # Handle common pairs
        if pair.startswith("XAU"):
            return ["USD"]  # Gold is primarily affected by USD news
        elif pair.startswith("XAG"):
            return ["USD"]  # Silver is primarily affected by USD news
        elif len(pair) >= 6:
            # Standard forex pair like EURUSD
            base = pair[:3]
            quote = pair[3:6]
            return [base, quote]
        
        return []
    
    def delete_news_event(self, event_id: int) -> bool:
        """
        Delete a news event by ID.
        
        Args:
            event_id: ID of the event to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            data = self._load_data()
            
            # Find and remove the event
            original_count = len(data["events"])
            data["events"] = [event for event in data["events"] if event.get("id") != event_id]
            
            if len(data["events"]) < original_count:
                self._save_data(data)
                logger.info(f"Deleted news event with ID: {event_id}")
                return True
            else:
                logger.warning(f"News event with ID {event_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting news event: {e}")
            return False
    
    def update_settings(self, minutes_before: Optional[int] = None, 
                       minutes_after: Optional[int] = None,
                       minutes_before_close: Optional[int] = None,
                       enabled: Optional[bool] = None):
        """
        Update news avoidance settings.
        
        Args:
            minutes_before: Minutes before news to stop trading
            minutes_after: Minutes after news to resume trading
            minutes_before_close: Minutes before news to close positions
            enabled: Whether news avoidance is enabled
        """
        try:
            data = self._load_data()
            
            if "settings" not in data:
                data["settings"] = {}
            
            if minutes_before is not None:
                data["settings"]["minutes_before"] = minutes_before
                self.minutes_before = minutes_before
                
            if minutes_after is not None:
                data["settings"]["minutes_after"] = minutes_after
                self.minutes_after = minutes_after
                
            if minutes_before_close is not None:
                data["settings"]["minutes_before_close"] = minutes_before_close
                self.minutes_before_close = minutes_before_close
                
            if enabled is not None:
                data["settings"]["enabled"] = enabled
            
            self._save_data(data)
            logger.info("News avoidance settings updated")
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            raise

# Global instance for easy access
simple_news_avoidance = SimpleNewsAvoidanceService()

