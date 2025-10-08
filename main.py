# main.py — Enhanced DCA (simple version, no batching)
# - Short window: hourly (e.g., 72 hours)
# - Medium window: daily (e.g., 30 days)
# - Long window (percentiles): daily (e.g., 90 days)
# - No price_threshold logic

from coinbase.rest import RESTClient
import math
import time
import datetime
from typing import Optional, List

import config
from send_to_discord import send_to_discord

# Initialize client
client = RESTClient(api_key=config.API_KEY, api_secret=config.API_SECRET)

# ---------------------------------------------------------
# Helpers (single API call, no pagination/batching)
# ---------------------------------------------------------

_GRAN_SECS = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "THIRTY_MINUTE": 1800,
    "ONE_HOUR": 3600,
    "SIX_HOUR": 21600,
    "ONE_DAY": 86400,
}

def _fetch_closes(product_id: str, periods: int, granularity: str) -> Optional[List[float]]:
    """
    Fetch 'periods' candles at the given granularity in a single API call.
    NOTE: periods must be < 350 to avoid Coinbase's limit.
    Returns closes ordered oldest->newest.
    """
    if periods <= 0:
        return []

    secs = _GRAN_SECS[granularity]
    end_time = datetime.datetime.now(datetime.UTC)
    start_time = end_time - datetime.timedelta(seconds=secs * periods)

    start_iso = int(start_time.timestamp())
    end_iso = int(end_time.timestamp())

    try:
        candles = client.get_candles(
            product_id=product_id,
            start=start_iso,
            end=end_iso,
            granularity=granularity,
            limit=periods
        )
    except Exception as e:
        send_to_discord(f"Error fetching candles for {product_id}: {e}")
        return None

    

    arr = sorted(candles["candles"], key=lambda c: c["start"])  # oldest -> newest
    return [float(c["close"]) for c in arr]

def _avg(xs: List[float]) -> Optional[float]:
    return (sum(xs) / len(xs)) if xs else None

def _percentile(values: List[float], p: float) -> Optional[float]:
    """
    p in [0,100]. Simple percentile (linear interpolation).
    """
    if not values:
        return None
    s = sorted(values)
    if p <= 0:
        return s[0]
    if p >= 100:
        return s[-1]
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k); c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

# ---------------------------------------------------------
# Signals (short = hourly; medium/long = daily)
# ---------------------------------------------------------

def get_short_average(product_id: str, hours: int) -> Optional[float]:
    closes = _fetch_closes(product_id, periods=hours, granularity="ONE_HOUR")
    return _avg(closes) if closes else None

def get_medium_average(product_id: str, days: int = 30) -> Optional[float]:
    closes = _fetch_closes(product_id, periods=days, granularity="ONE_DAY")
    return _avg(closes) if closes else None

def get_long_percentiles(product_id: str, days: int, lower_p: float, upper_p: float):
    closes = _fetch_closes(product_id, periods=days, granularity="ONE_DAY")
    if not closes:
        return None, None, None
    return closes[-1], _percentile(closes, lower_p), _percentile(closes, upper_p)

# ---------------------------------------------------------
# Core buy logic
# ---------------------------------------------------------

def buy_coin(coin_config):
    product_id = coin_config["product_id"]
    baseline_usd = float(coin_config["usd_to_buy"])
    post_only = bool(coin_config["post_only"])
    price_adjustment_percentage = float(coin_config["price_adjustment_percentage"])

    # Strategy knobs (from config.STRATEGY)
    S = config.STRATEGY  # :contentReference[oaicite:3]{index=3}
    short_hours = int(S["short_hours"])              # e.g., 72
    medium_days = 30                                  # daily ~30
    long_days = max(1, int(S["window_lookback_hours"] // 24))  # daily ~90

    # 1) Current price
    try:
        product = client.get_product(product_id)
        current_price = float(product["price"])
    except Exception as e:
        send_to_discord(f"Error fetching price for {product_id}: {e}")
        return

    # 2) Averages
    avg_short = get_short_average(product_id, hours=short_hours)
    avg_medium = get_medium_average(product_id, days=medium_days)

    if avg_short is None or avg_medium is None:
        send_to_discord(f"{product_id}: insufficient history; skipping.")
        return

    # 3) Dynamic multiplier (short vs medium)
    k = float(S["k_sensitivity"])
    dyn = 1.0 + k * (avg_short - current_price) / max(avg_short, 1e-9)

    if current_price < avg_short and current_price < avg_medium:
        dyn = max(dyn, 1.0)  # boost when clearly cheap
    elif current_price > avg_short and current_price > avg_medium:
        dyn = min(dyn, 1.0)  # shrink when clearly expensive
    else:
        dyn = (dyn * 0.5) + 0.5  # ambiguous → soften toward 1.0

    # 4) Long-window percentiles → window multiplier
    lower_p = float(S["lower_percentile"])
    upper_p = float(S["upper_percentile"])
    last_px, low_win, high_win = get_long_percentiles(product_id, days=long_days, lower_p=lower_p, upper_p=upper_p)

    win_mult = 1.0
    if last_px is not None and low_win is not None and high_win is not None:
        if last_px <= low_win:
            win_mult *= float(S["window_boost"])
        elif last_px >= high_win:
            win_mult *= float(S["window_cut"])

    # 5) Reserve behavior
    res_frac = float(S["reserve_fraction"])
    reserve_mult = (1.0 - res_frac)
    deep_dip_threshold = 1.0 - float(S["deep_dip_release_threshold"])
    deep_dip = (current_price <= deep_dip_threshold * avg_medium)
    if deep_dip:
        reserve_mult = (1.0 / max(1e-9, 1.0 - res_frac)) * float(S["reserve_release_boost"])

    # 6) Combine multipliers + clamp
    raw_mult = dyn * win_mult * reserve_mult
    raw_mult = _clip(raw_mult, float(S["min_shrink"]), float(S["max_boost"]))

    # 7) Size order (caps & mins)
    effective_usd = baseline_usd * raw_mult
    if effective_usd > float(S["per_run_cap_usd"]):
        effective_usd = float(S["per_run_cap_usd"])
    if effective_usd < float(S["min_order_usd"]):
        send_to_discord(
            f"{product_id}: computed ${effective_usd:.2f} below min ${S['min_order_usd']:.2f}; skipping."
        )
        return

    # 8) Post-only limit slightly below current
    adjusted_price = current_price * (1.0 - price_adjustment_percentage)
    base_size = round(effective_usd / max(adjusted_price, 1e-9), 8)

    # 9) Place order
    # Place order
    try:
        order = client.limit_order_gtc_buy(
            client_order_id=f"{product_id}_{int(time.time())}",
            product_id=product_id,
            base_size=str(base_size),
            limit_price=str(math.floor(adjusted_price)),
            post_only=post_only
        )

        # Handle both dict-like responses and objects gracefully
        def _field(o, name, default=None):
            try:
                return o[name]            # dict-like (your original style)
            except Exception:
                return getattr(o, name, default)  # attribute on CreateOrderResponse

        success = _field(order, "success", False)
        err     = _field(order, "error_response", None)

        msg = (
            f"[{product_id}] Px ${current_price:.2f} | "
            f"S-avg({short_hours}h) ${avg_short:.2f} | "
            f"M-avg({medium_days}d) ${avg_medium:.2f} | "
            f"Win[{int(lower_p)}/{int(upper_p)}] "
            f"{'N/A' if (low_win is None or high_win is None) else f'[{low_win:.2f},{high_win:.2f}]'}\n"
            f"Multipliers → dyn={dyn:.2f}, win={win_mult:.2f}, reserve={reserve_mult:.2f} "
            f"→ raw={raw_mult:.2f}\n"
            f"USD: baseline ${baseline_usd:.2f} → effective ${effective_usd:.2f}; "
            f"limit @ ${adjusted_price:.2f}; size={base_size}"
        )

        if success:
            send_to_discord("✅ " + msg + " → Order placed.")
        else:
            send_to_discord("❌ " + msg + f" → Error: {err or repr(order)}")

    except Exception as e:
        send_to_discord(f"Failed to place order for {product_id}: {e}")


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    for coin in config.COINS:  # coins & strategy come from config.py
        buy_coin(coin)
