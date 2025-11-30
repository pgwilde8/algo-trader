"""
GBP/USD ML5 Ensemble Signal Engine
Generates BUY/SELL/NEUTRAL signals using 5-model XGBoost ensemble
Saves signals to database instead of JSON files
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging
import sys

logger = logging.getLogger(__name__)

# Paths for algo-trader
H1_DATA_DIR = Path("/home/myalgo/algo-trader/data/h1_data")
GBPUSD_CSV = H1_DATA_DIR / "GBP_USD_H1_20051202_to_20251127.csv"

# Model paths in algo-trader
MODEL_DIR = Path("/home/myalgo/algo-trader/ml_models/signal_generator/gbpusd-models")
MODEL_PATH = MODEL_DIR / "GBP_USD_xgboost.json"


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators (same as training)"""
    df = df.copy()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_fast = df['close'].ewm(span=12, adjust=False).mean()
    ema_slow = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # EMAs
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()
    
    # Price momentum
    df['momentum_1h'] = df['close'].pct_change(1)
    df['momentum_4h'] = df['close'].pct_change(4)
    df['momentum_24h'] = df['close'].pct_change(24)
    
    # Volatility
    df['volatility'] = df['close'].rolling(window=24).std()
    
    # Price position (relative to range)
    df['high_low_range'] = df['high'].rolling(window=24).max() - df['low'].rolling(window=24).min()
    df['price_position'] = (df['close'] - df['low'].rolling(window=24).min()) / (df['high_low_range'] + 1e-8)
    
    return df


def load_gbpusd_data(count: int = 250) -> pd.DataFrame:
    """Load most recent N candles of GBP/USD H1 data"""
    try:
        df = pd.read_csv(GBPUSD_CSV)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
        df = df.tail(count)  # Get most recent candles
        df = df.reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error loading GBP/USD data: {e}")
        raise


def load_model() -> Optional[xgb.Booster]:
    """Load trained XGBoost model (single model, for backward compatibility)"""
    if not MODEL_PATH.exists():
        logger.warning(f"Model not found: {MODEL_PATH}")
        return None
    
    try:
        model = xgb.Booster()
        model.load_model(str(MODEL_PATH))
        return model
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None


def load_ensemble_models() -> list:
    """Load all ensemble models (5 models with different seeds: 43-47)"""
    models = []
    
    # Try to load ensemble models (seed 43-47)
    for seed in range(43, 48):
        model_path = MODEL_DIR / f"GBP_USD_xgboost_seed{seed}.json"
        if model_path.exists():
            try:
                model = xgb.Booster()
                model.load_model(str(model_path))
                models.append(model)
                logger.debug(f"Loaded ensemble model: {model_path.name}")
            except Exception as e:
                logger.warning(f"Error loading model {model_path}: {e}")
    
    # Fallback to single model if ensemble not found
    if not models:
        logger.info("Ensemble models not found, using single model")
        single_model = load_model()
        if single_model:
            models = [single_model]
    
    logger.info(f"Loaded {len(models)} model(s) for ensemble prediction")
    return models


def generate_signal(df: pd.DataFrame, models: list) -> Dict:
    """
    Generate BUY/SELL/NEUTRAL signal using XGBoost ensemble
    
    Model predicts probability of price going UP in next hour
    - prob > 0.6: BUY
    - prob < 0.4: SELL
    - 0.4 <= prob <= 0.6: NEUTRAL
    """
    if len(df) < 200:
        return {
            "direction": "NEUTRAL",
            "confidence": "LOW",
            "reason": "Insufficient data for indicators",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Get latest row for prediction
    latest = df.iloc[-1]
    
    # Feature columns (must match training exactly)
    feature_cols = [
        'rsi', 'macd', 'macd_signal', 'macd_histogram',
        'ema_20', 'ema_50', 'ema_200', 'atr',
        'momentum_1h', 'momentum_4h', 'momentum_24h',
        'volatility', 'high_low_range', 'price_position'
    ]
    
    # Prepare features - convert to numpy array and handle NaN
    feature_values = []
    for col in feature_cols:
        val = latest[col]
        # Handle NaN and convert to float
        if pd.isna(val):
            # Find last valid value in column
            valid_idx = df[col].last_valid_index()
            if valid_idx is not None:
                val = df.loc[valid_idx, col]
            else:
                val = 0.0
        feature_values.append(float(val))
    
    features = np.array(feature_values, dtype=np.float64).reshape(1, -1)
    
    # Final NaN check
    if np.isnan(features).any():
        logger.warning("Features still contain NaN after processing, filling with 0")
        features = np.nan_to_num(features, nan=0.0)
    
    # Ensemble prediction: average predictions from all models
    dtest = xgb.DMatrix(features, feature_names=feature_cols)
    individual_predictions = []
    
    for model in models:
        pred = model.predict(dtest)[0]
        individual_predictions.append(round(float(pred), 4))
    
    # Average predictions (ensemble)
    prob_up = np.mean(individual_predictions)
    
    # Log ensemble info if multiple models
    if len(models) > 1:
        logger.debug(f"Ensemble prediction: {[f'{p:.3f}' for p in individual_predictions]} → avg: {prob_up:.3f}")
    
    # Determine signal
    if prob_up > 0.6:
        direction = "BUY"
        confidence = "HIGH" if prob_up > 0.75 else "MEDIUM"
        confidence_score = prob_up
    elif prob_up < 0.4:
        direction = "SELL"
        confidence = "HIGH" if prob_up < 0.25 else "MEDIUM"
        confidence_score = 1.0 - prob_up
    else:
        direction = "NEUTRAL"
        confidence = "LOW"
        confidence_score = 0.5
    
    # Valid until next H1 candle
    now = datetime.now(timezone.utc)
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    valid_until = next_hour.isoformat()
    
    # Prepare individual model predictions for display
    individual_signals = []
    if len(models) > 1:
        for i, pred in enumerate(individual_predictions):
            seed = 43 + i  # Models are saved with seeds 43-47
            if pred > 0.6:
                model_direction = "BUY"
                model_confidence = "HIGH" if pred > 0.75 else "MEDIUM"
            elif pred < 0.4:
                model_direction = "SELL"
                model_confidence = "HIGH" if pred < 0.25 else "MEDIUM"
            else:
                model_direction = "NEUTRAL"
                model_confidence = "LOW"
            
            individual_signals.append({
                "model_num": i + 1,
                "seed": seed,
                "probability": pred,
                "direction": model_direction,
                "confidence": model_confidence
            })
    
    return {
        "instrument": "GBP_USD",
        "direction": direction,
        "entry_price": round(float(latest['close']), 5),  # GBP/USD uses 5 decimals (like EUR/USD)
        "confidence": confidence,
        "confidence_score": round(float(confidence_score), 3),
        "ml_probability": round(float(prob_up), 3),
        "ensemble_size": len(models),
        "individual_models": individual_signals,
        "timestamp": now.isoformat(),
        "valid_until": valid_until,
        "indicators": {
            "rsi": round(float(latest['rsi']), 2) if not pd.isna(latest['rsi']) else None,
            "macd": round(float(latest['macd']), 5) if not pd.isna(latest['macd']) else None,
            "macd_signal": round(float(latest['macd_signal']), 5) if not pd.isna(latest['macd_signal']) else None,
            "macd_histogram": round(float(latest['macd_histogram']), 5) if not pd.isna(latest['macd_histogram']) else None,
            "ema_20": round(float(latest['ema_20']), 5) if not pd.isna(latest['ema_20']) else None,
            "ema_50": round(float(latest['ema_50']), 5) if not pd.isna(latest['ema_50']) else None,
            "ema_200": round(float(latest['ema_200']), 5) if not pd.isna(latest['ema_200']) else None,
            "atr": round(float(latest['atr']), 5) if not pd.isna(latest['atr']) else None,
            "momentum_1h": round(float(latest['momentum_1h']), 6) if not pd.isna(latest['momentum_1h']) else None,
            "momentum_4h": round(float(latest['momentum_4h']), 6) if not pd.isna(latest['momentum_4h']) else None,
            "momentum_24h": round(float(latest['momentum_24h']), 6) if not pd.isna(latest['momentum_24h']) else None,
            "volatility": round(float(latest['volatility']), 6) if not pd.isna(latest['volatility']) else None,
            "price_position": round(float(latest['price_position']), 4) if not pd.isna(latest['price_position']) else None
        }
    }


def generate_and_save_signal() -> Optional[Dict]:
    """
    Load data, calculate indicators, generate signal using ML ensemble
    Returns signal dict ready to save to database
    """
    try:
        # Load ensemble models
        models = load_ensemble_models()
        if not models:
            logger.error("No models found. Please train the models first.")
            return None
        
        # Load most recent 250 candles
        df = load_gbpusd_data(count=250)
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Generate signal using ML ensemble
        signal = generate_signal(df, models)
        
        logger.info(f"GBP/USD signal generated: {signal['direction']} ({signal['confidence']}, prob={signal.get('ml_probability', 0):.3f})")
        return signal
        
    except Exception as e:
        logger.error(f"Error generating GBP/USD signal: {e}", exc_info=True)
        return None

