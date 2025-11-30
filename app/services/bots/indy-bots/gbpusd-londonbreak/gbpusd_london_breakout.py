import json
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[import-not-found]


PIP = 0.0001  # for GBPUSD


@dataclass
class StrategyConfig:
    asset_pair: str
    timezone: str

    asian_start: time
    asian_end: time
    london_probe_start: time
    london_window_start: time
    london_window_end: time

    min_asian_range_pips: float
    max_asian_range_pips: float
    breakout_buffer_pips: float
    initial_stop_pips: float

    atr_period: int
    atr_tp_bands: List[Dict[str, float]]

    probe_max_count: int

    trail_step_1_pips: float
    trail_sl_1_pips: float
    trail_step_2_pips: float
    trail_sl_2_pips: float
    trail_step_3_pips: float
    trail_sl_3_pips: float

    max_spread_pips: float
    pip_value: float = PIP

    news_avoidance_enabled: bool = True


@dataclass
class PositionState:
    direction: Optional[str] = None  # "long" or "short"
    entry_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    max_favorable_pips: float = 0.0
    opened_at: Optional[datetime] = None
    trade_ids: List[str] = field(default_factory=list)  # Real OANDA trade IDs


@dataclass
class SessionState:
    session_date: Optional[datetime] = None
    asian_high: Optional[float] = None
    asian_low: Optional[float] = None
    asian_range_pips: Optional[float] = None
    range_locked: bool = False
    probes_used: int = 0
    session_done: bool = False
    last_failed_direction: Optional[str] = None  # Block same direction after SL
    last_failed_time: Optional[datetime] = None


class LondonBreakoutStrategy:
    """
    Core logic only:
    - you feed in one candle at a time (with UTC timestamp)
    - it returns a dict with action info (or None if no action)
    - you handle execution with OANDA and your infra.
    """

    def __init__(self, config: StrategyConfig, logger=None, news_avoidance=None):
        self.cfg = config
        self.tz = ZoneInfo(self.cfg.timezone)
        self.logger = logger
        self.news_avoidance = news_avoidance  # your simple_news_avoidance service

        self.session = SessionState()
        self.position = PositionState()

        # keep last N candles for ATR
        self.candle_history: List[Dict[str, Any]] = []

    # ------------- Helpers ------------- #

    def _log(self, msg: str):
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def _utc_to_local(self, dt_utc: datetime) -> datetime:
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
        return dt_utc.astimezone(self.tz)

    def _is_between(self, t: time, start: time, end: time) -> bool:
        # handles overnight windows (e.g. 19:00 -> 02:55)
        if start <= end:
            return start <= t <= end
        else:
            return t >= start or t <= end

    def _compute_atr(self) -> Optional[float]:
        if len(self.candle_history) < self.cfg.atr_period + 1:
            return None

        df = pd.DataFrame(self.candle_history[-(self.cfg.atr_period + 1):])
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr_list = []
        for i in range(1, len(df)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1])
            )
            tr_list.append(tr)

        atr = np.mean(tr_list)
        return atr

    def _choose_tp_pips(self, atr_pips: float) -> float:
        for band in self.cfg.atr_tp_bands:
            if atr_pips <= band["max_atr_pips"]:
                return band["tp_pips"]
        return self.cfg.atr_tp_bands[-1]["tp_pips"]

    def _pips_between(self, price1: float, price2: float, direction: str) -> float:
        if direction == "long":
            return (price2 - price1) / self.cfg.pip_value
        else:
            return (price1 - price2) / self.cfg.pip_value

    def _asian_range_valid(self) -> bool:
        if self.session.asian_high is None or self.session.asian_low is None:
            return False
        rng = (self.session.asian_high - self.session.asian_low) / self.cfg.pip_value
        self.session.asian_range_pips = rng
        return self.cfg.min_asian_range_pips <= rng <= self.cfg.max_asian_range_pips

    def _price_breakout_direction(self, close_price: float) -> Optional[str]:
        if not self.session.range_locked:
            return None
        if not self._asian_range_valid():
            return None

        buf = self.cfg.breakout_buffer_pips * self.cfg.pip_value
        if close_price > self.session.asian_high + buf:
            return "long"
        elif close_price < self.session.asian_low - buf:
            return "short"
        return None

    def _inside_london_window(self, t_local: time) -> bool:
        return self._is_between(t_local, self.cfg.london_probe_start, self.cfg.london_window_end)

    def _after_asian_end(self, t_local: time) -> bool:
        # Only true once the Asian window has fully finished
        if self._is_between(t_local, self.cfg.asian_start, self.cfg.asian_end):
            return False

        if self.cfg.asian_start <= self.cfg.asian_end:
            return t_local >= self.cfg.asian_end

        # Asian window crosses midnight (e.g., 19:00 -> 01:30)
        return self.cfg.asian_end < t_local < self.cfg.asian_start

    def _should_avoid_news(self) -> bool:
        if not self.cfg.news_avoidance_enabled:
            return False
        if not self.news_avoidance:
            return False
        try:
            res = self.news_avoidance.should_avoid_trading(self.cfg.asset_pair)
            if res.get("avoid_trading", False):
                self._log(f"⏸️ Avoiding trade due to news: {res.get('reason')}")
                return True
            return False
        except Exception as e:
            self._log(f"News avoidance check failed: {e}")
            return False

    # ------------- Main entrypoint ------------- #

    def on_candle(
        self,
        candle: Dict[str, Any],
        spread_pips: float,
    ) -> Optional[Dict[str, Any]]:
        """
        candle: {
          "time": datetime (UTC),
          "open": float,
          "high": float,
          "low": float,
          "close": float,
          "volume": int
        }
        spread_pips: current spread in pips (used to block trades above max_spread)
        Returns action dict or None.
        """
        self.candle_history.append(candle)
        max_hist = self.cfg.atr_period + 5
        if len(self.candle_history) > max_hist:
            self.candle_history = self.candle_history[-max_hist:]

        t_utc = candle["time"]
        t_local = self._utc_to_local(t_utc)
        local_time = t_local.time()
        
        # London close killer: Exit all positions at 12:00 PM EST
        # Convert candle time to EST
        if t_utc.tzinfo is None:
            t_utc = t_utc.replace(tzinfo=ZoneInfo("UTC"))
        est_time = t_utc.astimezone(ZoneInfo("America/New_York")).time()
        if est_time >= time(12, 0) and self.position.direction is not None:
            self._log("🕐 London close: Exiting position at 12:00 PM EST")
            return {
                "action": "EXIT",
                "exit_reason": "LONDON_CLOSE_FLAT",
                "exit_price": candle["close"],
                "timestamp": t_utc.isoformat() if isinstance(t_utc, datetime) else str(t_utc)
            }
        close = candle["close"]
        high = candle["high"]
        low = candle["low"]

        # new session date logic (we treat "session_date" as local calendar date)
        if self.session.session_date is None or t_local.date() != self.session.session_date.date():
            # new trading day: reset session state
            self.session = SessionState(
                session_date=t_local,
                asian_high=None,
                asian_low=None,
                asian_range_pips=None,
                range_locked=False,
                probes_used=0,
                session_done=False,
                last_failed_direction=None,
                last_failed_time=None
            )
            self.position = PositionState()
            self._log(f"🔄 New session day: {t_local.date()}")

        # 1) Build Asian range
        if self._is_between(local_time, self.cfg.asian_start, self.cfg.asian_end):
            if self.session.asian_high is None:
                self.session.asian_high = high
                self.session.asian_low = low
                self._log(f"🌅 Asian session started: Building range from {high:.5f} / {low:.5f}")
            else:
                self.session.asian_high = max(self.session.asian_high, high)
                self.session.asian_low = min(self.session.asian_low, low)
                # Log progress every hour during Asian session
                if not hasattr(self, '_asian_log_counter'):
                    self._asian_log_counter = 0
                self._asian_log_counter += 1
                if self._asian_log_counter % 60 == 0:  # Every 60 candles (1 hour)
                    current_range = (self.session.asian_high - self.session.asian_low) / self.cfg.pip_value
                    self._log(f"🌅 Asian range building: {self.session.asian_low:.5f} - {self.session.asian_high:.5f} ({current_range:.1f} pips)")

        # 2) Lock Asian range after Asian session, before London end
        if (not self.session.range_locked
                and self._after_asian_end(local_time)
                and local_time <= self.cfg.london_window_end):
            self.session.range_locked = True
            # Calculate range pips
            if self.session.asian_high is not None and self.session.asian_low is not None:
                self.session.asian_range_pips = (self.session.asian_high - self.session.asian_low) / self.cfg.pip_value
            if self._asian_range_valid():
                self._log(
                    f"🔒 Asian range locked: "
                    f"{self.session.asian_low:.5f} - {self.session.asian_high:.5f} "
                    f"({self.session.asian_range_pips:.1f} pips)"
                )
            else:
                range_pips = self.session.asian_range_pips if self.session.asian_range_pips else 0
                self._log(
                    f"⚠️ Asian range invalid: {range_pips:.1f} pips "
                    f"(need {self.cfg.min_asian_range_pips}-{self.cfg.max_asian_range_pips} pips)"
                )

        # 3) Manage open position if any (trailing, SL/TP check)
        if self.position.direction is not None:
            action = self._manage_open_position(close, high, low, t_utc)
            if action is not None:
                return action  # exit action returned

        # 4) Entry logic (new probe) within London window
        if self.position.direction is None and not self.session.session_done:
            # Debug logging every 5 minutes during London window
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1
            
            if self._inside_london_window(local_time):
                # Log every 5 minutes (20 candles) during London window
                if self._debug_counter % 20 == 0:
                    range_valid = self._asian_range_valid()
                    range_pips = self.session.asian_range_pips if self.session.asian_range_pips else 0
                    breakout_dir = self._price_breakout_direction(close)
                    news_blocking = self._should_avoid_news()
                    in_trade_window = self._is_between(local_time, self.cfg.london_window_start, self.cfg.london_window_end)
                    
                    self._log(
                        f"🔍 Entry check @ {local_time.strftime('%H:%M')}: "
                        f"Range={range_valid} ({range_pips:.1f}pips), "
                        f"Breakout={breakout_dir}, "
                        f"Spread={spread_pips:.1f}/{self.cfg.max_spread_pips:.1f}pips, "
                        f"News={news_blocking}, "
                        f"InWindow={in_trade_window}, "
                        f"Probes={self.session.probes_used}/{self.cfg.probe_max_count}"
                    )
                
                if self.session.probes_used < self.cfg.probe_max_count:
                    if self._asian_range_valid():
                        if spread_pips <= self.cfg.max_spread_pips:
                            if not self._should_avoid_news():
                                direction = self._price_breakout_direction(close)
                                if direction is not None:
                                    # 🚫 NEW RULE: BLOCK SAME-DIRECTION AFTER SL LOSS
                                    if self.session.last_failed_direction == direction:
                                        if self._debug_counter % 20 == 0:
                                            self._log(f"⛔ Same-direction retry blocked after SL: {direction.upper()}")
                                        return None
                                    
                                    if self._is_between(
                                        local_time,
                                        self.cfg.london_window_start,
                                        self.cfg.london_window_end,
                                    ):
                                        return self._enter_new_probe(direction, close, t_utc)
                                    else:
                                        if self._debug_counter % 20 == 0:
                                            self._log("ℹ️ Breakout detected before London trade window; waiting.")
                        else:
                            if self._debug_counter % 20 == 0:
                                self._log(f"⏸️ Spread too high ({spread_pips:.1f} pips), skip entry.")
                    else:
                        # no valid range
                        if self._debug_counter % 20 == 0:
                            range_pips = self.session.asian_range_pips if self.session.asian_range_pips else 0
                            self._log(f"⏸️ Asian range invalid: {range_pips:.1f} pips (need {self.cfg.min_asian_range_pips}-{self.cfg.max_asian_range_pips} pips)")
                else:
                    if self._debug_counter % 20 == 0:
                        self._log(f"⏸️ Max probes reached ({self.session.probes_used}/{self.cfg.probe_max_count})")
            elif self._debug_counter % 20 == 0 and local_time >= self.cfg.london_window_start:
                self._log(f"⏸️ Outside London window: {local_time.strftime('%H:%M')} (window: {self.cfg.london_window_start.strftime('%H:%M')}-{self.cfg.london_window_end.strftime('%H:%M')})")

        # nothing special on this candle
        return None

    # ------------- Position management ------------- #

    def _enter_new_probe(self, direction: str, price: float, t_utc: datetime) -> Dict[str, Any]:
        self.session.probes_used += 1

        atr = self._compute_atr()
        if atr is None:
            # very early in session, fallback to small TP
            atr_pips = 6.0
        else:
            atr_pips = atr / self.cfg.pip_value

        tp_pips = self._choose_tp_pips(atr_pips)

        if direction == "long":
            sl_price = price - self.cfg.initial_stop_pips * self.cfg.pip_value
            tp_price = price + tp_pips * self.cfg.pip_value
        else:
            sl_price = price + self.cfg.initial_stop_pips * self.cfg.pip_value
            tp_price = price - tp_pips * self.cfg.pip_value

        self.position = PositionState(
            direction=direction,
            entry_price=price,
            sl_price=sl_price,
            tp_price=tp_price,
            max_favorable_pips=0.0,
            opened_at=t_utc
        )

        self._log(
            f"🚀 Probe #{self.session.probes_used} ENTRY {direction.upper()} @ {price:.5f}, "
            f"SL={sl_price:.5f}, TP={tp_price:.5f} (ATR~{atr_pips:.1f} pips → TP={tp_pips} pips)"
        )

        return {
            "action": "ENTER",
            "direction": direction,
            "entry_price": price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "probe_number": self.session.probes_used,
            "timestamp": t_utc.isoformat()
        }

    def _manage_open_position(
        self,
        close: float,
        high: float,
        low: float,
        t_utc: datetime
    ) -> Optional[Dict[str, Any]]:
        pos = self.position
        if pos.direction is None:
            return None

        # update max favorable move
        if pos.direction == "long":
            current_fav_pips = self._pips_between(pos.entry_price, high, "long")
        else:
            current_fav_pips = self._pips_between(pos.entry_price, low, "short")

        if current_fav_pips > pos.max_favorable_pips:
            pos.max_favorable_pips = current_fav_pips

        # Trailing logic
        old_sl = pos.sl_price
        if pos.max_favorable_pips >= self.cfg.trail_step_1_pips:
            # move SL to entry -5 pips
            if pos.direction == "long":
                wanted_sl = pos.entry_price + self.cfg.trail_sl_1_pips * self.cfg.pip_value
            else:
                wanted_sl = pos.entry_price - self.cfg.trail_sl_1_pips * self.cfg.pip_value
            pos.sl_price = max(pos.sl_price, wanted_sl) if pos.direction == "long" else min(pos.sl_price, wanted_sl)

        if pos.max_favorable_pips >= self.cfg.trail_step_2_pips:
            # move SL to break-even (or near break-even based on trail_sl_2_pips)
            if pos.direction == "long":
                wanted_sl = pos.entry_price + self.cfg.trail_sl_2_pips * self.cfg.pip_value
            else:
                wanted_sl = pos.entry_price - self.cfg.trail_sl_2_pips * self.cfg.pip_value
            pos.sl_price = max(pos.sl_price, wanted_sl) if pos.direction == "long" else min(pos.sl_price, wanted_sl)

        if pos.max_favorable_pips >= self.cfg.trail_step_3_pips:
            # move SL to +2 pips
            if pos.direction == "long":
                wanted_sl = pos.entry_price + self.cfg.trail_sl_3_pips * self.cfg.pip_value
            else:
                wanted_sl = pos.entry_price - self.cfg.trail_sl_3_pips * self.cfg.pip_value
            pos.sl_price = max(pos.sl_price, wanted_sl) if pos.direction == "long" else min(pos.sl_price, wanted_sl)

        sl_updated = pos.sl_price != old_sl
        if sl_updated:
            self._log(
                f"🔧 Trailing SL adjusted to {pos.sl_price:.5f} "
                f"(max favorable {pos.max_favorable_pips:.1f} pips)"
            )

        # Check SL/TP hits using candle extremes (approximation)
        # Use the updated stop loss price for hit detection
        exit_reason = None
        exit_price = None

        if pos.direction == "long":
            if low <= pos.sl_price:
                exit_reason = "SL_HIT"
                exit_price = pos.sl_price
            elif high >= pos.tp_price:
                exit_reason = "TP_HIT"
                exit_price = pos.tp_price
        else:
            if high >= pos.sl_price:
                exit_reason = "SL_HIT"
                exit_price = pos.sl_price
            elif low <= pos.tp_price:
                exit_reason = "TP_HIT"
                exit_price = pos.tp_price

        if exit_reason is not None:
            pnl_pips = self._pips_between(pos.entry_price, exit_price, pos.direction)
            self._log(
                f"✅ EXIT {pos.direction.upper()} @ {exit_price:.5f} "
                f"({pnl_pips:.1f} pips, reason={exit_reason})"
            )

            # if TP hit → end session
            if exit_reason == "TP_HIT":
                self.session.session_done = True
            else:
                # SL hit → block same direction for rest of session
                self.session.last_failed_direction = pos.direction
                self.session.last_failed_time = t_utc
                self._log(f"⚠️ Recorded failed direction: {pos.direction.upper()} (blocked for rest of session)")

            self.position = PositionState()  # flat

            return {
                "action": "EXIT",
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "pnl_pips": pnl_pips,
                "timestamp": t_utc.isoformat()
            }

        # If stop loss was updated but no exit, return update action
        if sl_updated:
            return {
                "action": "UPDATE_SL",
                "sl_price": pos.sl_price,
                "max_favorable_pips": pos.max_favorable_pips,
                "timestamp": t_utc.isoformat()
            }

        return None


# ------------ Helper to load config.json into StrategyConfig ------------ #

def load_strategy_config(config_path: str) -> StrategyConfig:
    with open(config_path, "r") as f:
        raw = json.load(f)

    tz = raw["session_times"]["timezone"]

    def parse_hhmm(s: str) -> time:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))

    asian_start = parse_hhmm(raw["session_times"]["asian_start"])
    asian_end = parse_hhmm(raw["session_times"]["asian_end"])
    london_probe_start = parse_hhmm(raw["session_times"]["london_probe_start"])
    london_window_start = parse_hhmm(raw["session_times"]["london_window_start"])
    london_window_end = parse_hhmm(raw["session_times"]["london_window_end"])

    sp = raw["strategy_params"]
    mc = raw["market_conditions"]

    return StrategyConfig(
        asset_pair=raw["asset_pair"],
        timezone=tz,
        asian_start=asian_start,
        asian_end=asian_end,
        london_probe_start=london_probe_start,
        london_window_start=london_window_start,
        london_window_end=london_window_end,
        min_asian_range_pips=sp["min_asian_range_pips"],
        max_asian_range_pips=sp["max_asian_range_pips"],
        breakout_buffer_pips=sp["breakout_buffer_pips"],
        initial_stop_pips=sp["initial_stop_pips"],
        atr_period=sp["atr_period"],
        atr_tp_bands=sp["atr_tp_bands"],
        probe_max_count=sp["probe_max_count"],
        trail_step_1_pips=sp["trail_step_1_pips"],
        trail_sl_1_pips=sp["trail_sl_1_pips"],
        trail_step_2_pips=sp["trail_step_2_pips"],
        trail_sl_2_pips=sp["trail_sl_2_pips"],
        trail_step_3_pips=sp["trail_step_3_pips"],
        trail_sl_3_pips=sp["trail_sl_3_pips"],
        max_spread_pips=mc["max_spread_pips"],
        pip_value=mc.get("pip_value", PIP),
        news_avoidance_enabled=raw.get("news_avoidance", {}).get("enabled", True)
    )


# Optional: quick manual test harness (offline)
if __name__ == "__main__":
    from datetime import timedelta

    cfg = load_strategy_config("config.json")
    strat = LondonBreakoutStrategy(cfg)

    # Fake candles just to show it runs; replace with your own backtest or live driver.
    now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    price = 1.2600

    for i in range(300):
        t = now_utc + timedelta(minutes=i)
        candle = {
            "time": t,
            "open": price,
            "high": price + 0.0005,
            "low": price - 0.0005,
            "close": price + 0.0002,
            "volume": 100
        }
        spread_pips = 1.0
        action = strat.on_candle(candle, spread_pips)
        if action:
            print(action)
        price += 0.0001
    