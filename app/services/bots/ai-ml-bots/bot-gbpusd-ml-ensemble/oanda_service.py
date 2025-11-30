import os
import logging
import json
from datetime import datetime
import requests
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class OANDAService:
    """Service to handle all OANDA API interactions for GBP/USD ML Ensemble Bot"""
    
    def __init__(self, account_id: str, api_key: str, mode: str = 'practice'):
        self.account_id = account_id
        self.api_key = api_key
        self.mode = mode
        self.base_url = "https://api-fxpractice.oanda.com/v3" if mode == 'practice' else "https://api-fxtrade.oanda.com/v3"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }
        logger.info(f"OANDA service initialized - Mode: {mode}, Account: {account_id}")

    def _make_request(self, method: str, endpoint: str, params: dict = None, data: dict = None, max_retries: int = 3) -> Optional[dict]:
        """Make request to OANDA API with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, headers=self.headers, params=params, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers, json=data, timeout=30)
                elif method == "PUT":
                    response = requests.put(url, headers=self.headers, json=data, timeout=30)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                error_msg = str(e)
                try:
                    if e.response is not None:
                        error_data = e.response.json()
                        error_msg = error_data.get('errorMessage', error_data.get('errorMessage', str(e)))
                except:
                    pass
                
                status_code = e.response.status_code if e.response else "unknown"
                if attempt == max_retries - 1:
                    logger.error(f"OANDA API request failed after {max_retries} attempts: {status_code} - {error_msg}")
                    return None
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {status_code} - {error_msg}, retrying...")
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"OANDA API request failed after {max_retries} attempts: {e}")
                    return None
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying...")
        
        return None

    def get_account_summary(self) -> Optional[dict]:
        """Get account summary including balance"""
        endpoint = f"accounts/{self.account_id}/summary"
        response = self._make_request("GET", endpoint)
        if response:
            return response.get("account")
        return None

    def get_current_price(self, instrument: str) -> Optional[dict]:
        """Get current price for an instrument"""
        endpoint = f"accounts/{self.account_id}/pricing"
        params = {
            "instruments": instrument,
            "includeHomeConversions": True
        }
        response = self._make_request("GET", endpoint, params=params)
        if response and response.get("prices"):
            return response["prices"][0]
        return None

    def place_market_order(self, instrument: str, units: float, stop_loss: float = None, take_profit: float = None, client_tag: str = None) -> Optional[dict]:
        """Place a market order with proper price formatting for GBP/USD (5 decimals)"""
        endpoint = f"accounts/{self.account_id}/orders"
        
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(int(units)),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT"
            }
        }
        
        # Add client extensions for tracking
        tag_value = client_tag or "GBPUSD-ML-Ensemble"
        client_extensions = {
            "tag": tag_value,
            "comment": f"GBP/USD ML Ensemble Bot - {tag_value}"
        }
        order_data["order"]["clientExtensions"] = client_extensions
        order_data["order"]["tradeClientExtensions"] = client_extensions.copy()
        logger.info(f"🏷️ Order tagged: {tag_value}")
        
        # Fixed stop loss and take profit with proper formatting (5 decimals for GBP/USD)
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}
        
        logger.info(f"📋 Order data: {json.dumps(order_data, indent=2)}")
        
        response = self._make_request("POST", endpoint, data=order_data)
        logger.info(f"📡 OANDA response: {response}")
        
        if response:
            return response.get("orderFillTransaction")
        return None

    def get_open_trades(self, instrument: str = "GBP_USD") -> Optional[List[dict]]:
        """Get all open trades for an instrument"""
        endpoint = f"accounts/{self.account_id}/openTrades"
        response = self._make_request("GET", endpoint)
        if response:
            trades = response.get("trades", [])
            # Filter by instrument if specified
            if instrument:
                trades = [t for t in trades if t.get("instrument") == instrument]
            return trades
        return None

    def close_trade(self, trade_id: str) -> Optional[dict]:
        """Close a specific trade"""
        endpoint = f"accounts/{self.account_id}/trades/{trade_id}/close"
        response = self._make_request("PUT", endpoint, data={})
        if response:
            logger.info(f"✅ Trade {trade_id} closed")
            return response.get("orderFillTransaction")
        return None

    def calculate_position_size(self, account_balance: float, risk_percentage: float, stop_loss_pips: float) -> float:
        """Calculate position size based on risk for GBP/USD"""
        try:
            # Risk amount in account currency
            risk_amount = account_balance * (risk_percentage / 100)
            
            # For GBP/USD, pip value is $10 per 100,000 units (standard lot)
            # Each pip move = $10 per 100k units = $0.0001 per unit
            dollar_risk_per_unit = stop_loss_pips * 0.0001
            
            units = risk_amount / dollar_risk_per_unit if dollar_risk_per_unit > 0 else 0
            
            # Round to nearest 1000 (OANDA minimum)
            units = round(units / 1000) * 1000
            
            # Safety limits
            units = max(1000, min(units, 500000))  # Between 1k and 500k units
            
            logger.debug(f"Position calc: Risk ${risk_amount:.2f}, SL {stop_loss_pips} pips → {units:.0f} units")
            
            return units
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

