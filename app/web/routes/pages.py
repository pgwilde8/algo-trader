from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db import get_db
from app.models.ml_signal_history import MLSignalHistory

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Asset URL to Database format mapping
ASSET_URL_TO_DB = {
    # Major Forex
    "eurusd": "EUR_USD",
    "gbpusd": "GBP_USD",
    "usdcad": "USD_CAD",
    "usdjpy": "USD_JPY",
    "gbpjpy": "GBP_JPY",
    "audusd": "AUD_USD",
    "nzdusd": "NZD_USD",
    "usdchf": "USD_CHF",
    # Commodities
    "xauusd": "XAU_USD",  # Gold
    "xagusd": "XAG_USD",  # Silver
    # Crypto (if added)
    "btcusd": "BTC_USD",
    "ethusd": "ETH_USD",
    # Indices (if added)
    "spx500usd": "SPX500_USD",
    "nas100usd": "NAS100_USD",
}

# Reverse mapping for display
ASSET_DB_TO_DISPLAY = {
    "EUR_USD": "EUR/USD",
    "GBP_USD": "GBP/USD",
    "USD_CAD": "USD/CAD",
    "USD_JPY": "USD/JPY",
    "GBP_JPY": "GBP/JPY",
    "AUD_USD": "AUD/USD",
    "NZD_USD": "NZD/USD",
    "USD_CHF": "USD/CHF",
    "XAU_USD": "XAU/USD",
    "XAG_USD": "XAG/USD",
    "BTC_USD": "BTC/USD",
    "ETH_USD": "ETH/USD",
    "SPX500_USD": "SPX500/USD",
    "NAS100_USD": "NAS100/USD",
}

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/offers/free-signals-trial", response_class=HTMLResponse)
@router.get("/free-signals", response_class=HTMLResponse)
async def free_signals_trial(request: Request):
    """Free signals trial landing page - for Reddit/marketing"""
    return templates.TemplateResponse("offers/free-signals-trial.html", {"request": request})


def _render_ml5_trader(request: Request, asset: str = None, asset_display: str = None, template_name: str = None):
    """Shared function to render ML5 Trader page"""
    context = {"request": request}
    if asset:
        context["asset"] = asset
        context["asset_display"] = asset_display or asset.replace("_", "/")
    
    # Use provided template or determine from asset
    if template_name:
        template_path = template_name
    elif asset:
        # Convert asset to URL format for template name (EUR_USD -> ml5-eurusd)
        asset_lower = asset.lower().replace("_", "")
        template_path = f"offers/ml5-{asset_lower}.html"
    else:
        # Default overview template (use eurusd as default for now)
        template_path = "offers/ml5-eurusd.html"
    
    return templates.TemplateResponse(template_path, context)


@router.get("/offers/ml5-{asset}", response_class=HTMLResponse)
async def offers_ml5_asset(request: Request, asset: str):
    """Offer page for specific asset (e.g., /offers/ml5-eurusd)"""
    # Convert URL format to database format
    asset_lower = asset.lower().replace("-", "").replace("_", "")
    asset_db = ASSET_URL_TO_DB.get(asset_lower)
    
    if not asset_db:
        # Try to construct from URL if not in mapping
        if "-" in asset or "_" in asset:
            parts = asset.upper().replace("-", "_").split("_")
            if len(parts) == 2:
                asset_db = "_".join(parts)
            else:
                raise HTTPException(status_code=404, detail=f"Asset '{asset}' not found")
        else:
            # Try to split eurusd into EUR_USD (assumes 6-7 char pairs)
            if len(asset_lower) == 6:
                asset_db = f"{asset_lower[:3].upper()}_{asset_lower[3:].upper()}"
            elif len(asset_lower) == 7:
                asset_db = f"{asset_lower[:3].upper()}_{asset_lower[3:].upper()}"
            else:
                raise HTTPException(status_code=404, detail=f"Asset '{asset}' not found")
    
    asset_display = ASSET_DB_TO_DISPLAY.get(asset_db, asset_db.replace("_", "/"))
    
    # Use offers template with ml5- prefix
    template_path = f"offers/ml5-{asset_lower}.html"
    
    return _render_ml5_trader(request, asset=asset_db, asset_display=asset_display, template_name=template_path)


@router.get("/ml5-trader", response_class=HTMLResponse)
async def ml5_trader_overview(request: Request):
    """ML5 Trader overview page"""
    return _render_ml5_trader(request)


async def _render_ml5_dashboard(request: Request, asset: str, db: AsyncSession):
    """Shared function to render ML5 Trader dashboard"""
    try:
        # Clean asset name
        asset_clean = asset.lower().replace("-", "").replace("_", "")
        
        # Convert URL format to database format
        asset_db = ASSET_URL_TO_DB.get(asset_clean)
        
        if not asset_db:
            # Try to construct from URL if not in mapping
            if len(asset_clean) == 6:
                asset_db = f"{asset_clean[:3].upper()}_{asset_clean[3:].upper()}"
            elif len(asset_clean) == 7:
                asset_db = f"{asset_clean[:3].upper()}_{asset_clean[3:].upper()}"
            else:
                raise HTTPException(status_code=404, detail=f"Asset '{asset}' not found")
        
        asset_display = ASSET_DB_TO_DISPLAY.get(asset_db, asset_db.replace("_", "/"))
        
        # Get latest signal for this asset
        signal_data = None
        try:
            signal_query = select(MLSignalHistory).where(
                MLSignalHistory.instrument == asset_db
            ).order_by(MLSignalHistory.timestamp.desc()).limit(1)
            
            signal_result = await db.execute(signal_query)
            signal = signal_result.scalar_one_or_none()
            
            if signal:
                # Parse individual_models JSONB
                individual_models = []
                if signal.individual_models:
                    individual_models = signal.individual_models if isinstance(signal.individual_models, list) else []
                
                signal_data = {
                    "instrument": signal.instrument,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "confidence_score": float(signal.confidence_score) if signal.confidence_score else None,
                    "ml_probability": float(signal.ml_probability) if signal.ml_probability else 0.5,
                    "entry_price": float(signal.entry_price) if signal.entry_price else None,
                    "ensemble_size": int(signal.ensemble_size) if signal.ensemble_size else 5,
                    "individual_models": individual_models,
                    "indicators": signal.indicators if signal.indicators else {},
                    "timestamp": signal.timestamp,
                    "valid_until": signal.valid_until
                }
            
        except Exception as e:
            import logging
            logging.error(f"Error fetching signal for {asset_db}: {e}", exc_info=True)
        
        # Use dashboard template
        template_name = f"dashboard/ml5-{asset_clean}.html"
        
        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "signal": signal_data,
                "asset": asset_db,
                "asset_display": asset_display
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error in _render_ml5_dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/dashboard/ml5-{asset}", response_class=HTMLResponse)
async def dashboard_ml5_asset(request: Request, asset: str, db: AsyncSession = Depends(get_db)):
    """Dashboard route (simpler URL format: /dashboard/ml5-eurusd)"""
    return await _render_ml5_dashboard(request, asset, db)


@router.get("/ml5-trader/ml5-{asset}", response_class=HTMLResponse)
async def ml5_trader_dashboard_alt(request: Request, asset: str, db: AsyncSession = Depends(get_db)):
    """ML5 Trader dashboard (alternate URL format: /ml5-trader/ml5-eurusd)"""
    return await _render_ml5_dashboard(request, asset, db)


@router.get("/ml5-trader/{asset}", response_class=HTMLResponse)
async def ml5_trader_asset(request: Request, asset: str):
    """ML5 Trader page for specific asset (e.g., /ml5-trader/eurusd)"""
    # Convert URL format to database format
    asset_lower = asset.lower().replace("-", "").replace("_", "")
    asset_db = ASSET_URL_TO_DB.get(asset_lower)
    
    if not asset_db:
        # Try to construct from URL if not in mapping
        # Handle formats like "eur-usd", "eur_usd", "eurusd"
        if "-" in asset or "_" in asset:
            parts = asset.upper().replace("-", "_").split("_")
            if len(parts) == 2:
                asset_db = "_".join(parts)
            else:
                raise HTTPException(status_code=404, detail=f"Asset '{asset}' not found")
        else:
            # Try to split eurusd into EUR_USD (assumes 6-7 char pairs)
            if len(asset_lower) == 6:
                # eurusd -> EUR_USD (3+3)
                asset_db = f"{asset_lower[:3].upper()}_{asset_lower[3:].upper()}"
            elif len(asset_lower) == 7:
                # gbpusd -> GBP_USD (3+4) or usdjpy -> USD_JPY (3+4)
                # Try 3+4 split first (most common)
                asset_db = f"{asset_lower[:3].upper()}_{asset_lower[3:].upper()}"
            else:
                raise HTTPException(status_code=404, detail=f"Asset '{asset}' not found")
    
    asset_display = ASSET_DB_TO_DISPLAY.get(asset_db, asset_db.replace("_", "/"))
    
    # Check if template exists for this asset
    template_path = f"offers/ml5-{asset_lower}.html"
    
    return _render_ml5_trader(request, asset=asset_db, asset_display=asset_display, template_name=template_path)


@router.get("/ml5-trader/{asset}/dashboard", response_class=HTMLResponse)
async def ml5_trader_dashboard(request: Request, asset: str, db: AsyncSession = Depends(get_db)):
    """ML5 Trader dashboard showing detailed signal with all 5 model predictions"""
    return await _render_ml5_dashboard(request, asset, db)


@router.get("/dashboard/multisignals", response_class=HTMLResponse)
async def dashboard_multisignals(request: Request, db: AsyncSession = Depends(get_db)):
    """Multi-signals page showing latest signal from each instrument"""
    signals_data = []
    
    # Expected instruments that should always appear on the page
    expected_instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]
    
    try:
        # Get all unique instruments from database
        instruments_query = select(MLSignalHistory.instrument).distinct()
        instruments_result = await db.execute(instruments_query)
        db_instruments = [row[0] for row in instruments_result.all()]
        
        # Combine expected instruments with database instruments (no duplicates, maintain order)
        all_instruments = expected_instruments + [inst for inst in db_instruments if inst not in expected_instruments]
        
        # Get latest signal for each instrument
        for instrument in all_instruments:
            signal_query = select(MLSignalHistory).where(
                MLSignalHistory.instrument == instrument
            ).order_by(MLSignalHistory.timestamp.desc()).limit(1)
            
            signal_result = await db.execute(signal_query)
            signal = signal_result.scalar_one_or_none()
            
            if signal:
                signals_data.append({
                    "instrument": signal.instrument,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "ml_probability": float(signal.ml_probability) if signal.ml_probability else 0.5,
                    "entry_price": float(signal.entry_price) if signal.entry_price else None,
                    "timestamp": signal.timestamp,
                    "valid_until": signal.valid_until
                })
            else:
                # Add placeholder for expected instruments without signals
                if instrument in expected_instruments:
                    signals_data.append({
                        "instrument": instrument,
                        "direction": None,
                        "confidence": None,
                        "ml_probability": None,
                        "entry_price": None,
                        "timestamp": None,
                        "valid_until": None
                    })
        
        # Sort by instrument name
        signals_data.sort(key=lambda x: x["instrument"])
        
    except Exception as e:
        # Return empty list on error
        import logging
        logging.error(f"Error fetching signals: {e}", exc_info=True)
        signals_data = []
    
    return templates.TemplateResponse(
        "dashboard/multisignals.html",
        {"request": request, "signals": signals_data}
    )


@router.get("/multisignals", response_class=HTMLResponse)
async def multisignals(request: Request, db: AsyncSession = Depends(get_db)):
    """Multi-signals page showing latest signal from each instrument (legacy route)"""
    # Reuse the same logic as dashboard_multisignals
    return await dashboard_multisignals(request, db)

