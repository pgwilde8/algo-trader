"""
News Avoidance API Routes
Provides REST API endpoints for managing news events and checking trading avoidance.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.utils.simple_news_avoidance import simple_news_avoidance

router = APIRouter()


# Request/Response Models
class NewsEventCreate(BaseModel):
    title: str
    currency: str
    event_time: datetime
    impact: str = "high"


class NewsEventResponse(BaseModel):
    id: int
    title: str
    currency: str
    event_time: datetime
    impact: str
    created_at: datetime


class TradingAvoidanceResponse(BaseModel):
    avoid_trading: bool
    reason: str
    next_event: Optional[dict] = None
    safe_to_trade_at: Optional[datetime] = None


class PositionCloseResponse(BaseModel):
    close_positions: bool
    reason: str
    next_event: Optional[dict] = None


# Routes

@router.get("/news-events", response_model=List[NewsEventResponse])
async def get_upcoming_news(
    hours_ahead: int = 24,
    currency: Optional[str] = None
):
    """Get upcoming high-impact news events."""
    try:
        events = simple_news_avoidance.get_upcoming_news(
            hours_ahead=hours_ahead,
            currency=currency
        )
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/news-events", response_model=NewsEventResponse, status_code=201)
async def create_news_event(event: NewsEventCreate):
    """Add a new news event."""
    try:
        created_event = simple_news_avoidance.add_news_event(
            title=event.title,
            currency=event.currency,
            event_time=event.event_time,
            impact=event.impact
        )
        return created_event
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/news-events/{event_id}", status_code=204)
async def delete_news_event(event_id: int):
    """Delete a news event by ID."""
    try:
        success = simple_news_avoidance.delete_news_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Event with ID {event_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/should-avoid-trading/{currency_pair}", response_model=TradingAvoidanceResponse)
async def check_should_avoid_trading(currency_pair: str):
    """Check if trading should be avoided for a currency pair."""
    try:
        result = simple_news_avoidance.should_avoid_trading(currency_pair)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/should-close-positions/{currency_pair}", response_model=PositionCloseResponse)
async def check_should_close_positions(currency_pair: str):
    """Check if positions should be closed for a currency pair."""
    try:
        result = simple_news_avoidance.should_close_positions(currency_pair)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_settings():
    """Get current news avoidance settings."""
    try:
        data = simple_news_avoidance._load_data()
        return data.get("settings", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/settings")
async def update_settings(
    minutes_before: Optional[int] = None,
    minutes_after: Optional[int] = None,
    minutes_before_close: Optional[int] = None,
    enabled: Optional[bool] = None
):
    """Update news avoidance settings."""
    try:
        simple_news_avoidance.update_settings(
            minutes_before=minutes_before,
            minutes_after=minutes_after,
            minutes_before_close=minutes_before_close,
            enabled=enabled
        )
        data = simple_news_avoidance._load_data()
        return data.get("settings", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

