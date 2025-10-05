from coinbase.rest import RESTClient
import math
import time
import datetime
import config
from typing import Optional, List
from send_to_discord import send_to_discord

# Initialize client
client = RESTClient(api_key=config.API_KEY, api_secret=config.API_SECRET)

def _fetch_hourly_closes(product_id: str, hours: int) -> Optional[List[float]]:
    """
    Fetch up to `hours` of hourly candles and return list of closes (oldest->newest).
    """
    if hours <= 0:
        return []

    end_time = datetime.datetime.now(datetime.UTC)
    start_time = end_time - datetime.timedelta(hours=hours)
    start_iso = int(start_time.timestamp())
    end_iso = int(end_time.timestamp())

    try:
        candles = client.get_candles(
            product_id=product_id,
            start=start_iso,
            end=end_iso,
            granularity="ONE_HOUR",
            limit=hours
        )
    except Exception as e:
        send_to_discord(f"Error fetching candles for {product_id}: {e}")
        return None

    if not candles or "candles" not in candles or not candles["candles"]:
        send_to_discord(f"No candle data for {product_id}")
        return None

    # Coinbase returns newest first sometimes; enforce oldest->newest
    raw = candles["candles"]
    raw_sorted = sorted(raw, key=lambda c: c["start"])
    closes = [float(c["close"]) for c in raw_sorted]
    return closes

def _avg(closes: List[float]) -> Optional[float]:
    return (sum(closes) / len(closes)) if closes else None

def _percentile(closes: List[float], p: float) -> Optional[float]:
    """
    p in [0,100]. Simple percentile without numpy.
    """
    if not closes:
        return None
    s = sorted(closes)
    if p <= 0:
        return s[0]
    if p >= 100:
        return s[-1]
    # Linear interpolation
    k = (len(s)-1) * (p/100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def get_average_close_price(product_id: str, hours: int = 72) -> Optional[float]:
    closes = _fetch_hourly_closes(product_id, hours)
    if closes is None:
        return None
    return _avg(closes)

def get_medium_average(product_id: str, hours: int) -> Optional[float]:
    return get_average_close_price(product_id, hours)

def get_price_percentiles(product_id: str, lookback_hours: int, lower_p: float, upper_p: float):
    closes = _fetch_hourly_closes(product_id, lookback_hours)
    if closes is None:
        return None, None, None
    lo = _percentile(closes, lower_p)
    hi = _percentile(closes, upper_p)
    last = closes[-1] if closes else None
    return last, lo, hi

def buy_coin(coin_config):
    """Enhanced DCA buy logic for a single coin based on configuration."""
    product_id = coin_config["product_id"]
    baseline_usd = float(coin_config["usd_to_buy"])
    post_only = coin_config["post_only"]
    price_adjustment_percentage = coin_config["price_adjustment_percentage"]

    # Strategy knobs
    S = config.STRATEGY
    short_hours = S["short_hours"]
    medium_hours = S["medium_hours"]

    # Get current price
    try:
        product = client.get_product(product_id)
        current_price = float(product["price"])
    except Exception as e:
        send_to_discord(f"Error fetching price for {product_id}: {e}")
        return

    # Get averages
    avg_short = get_average_close_price(product_id, hours=short_hours)
    avg_medium = get_medium_average(product_id, hours=medium_hours)

    if avg_short is None or avg_medium is None:
        send_to_discord(f"{product_id}: insufficient history; skipping.")
        return

    # --- Dynamic multiplier (step 1) ---
    # base on distance from short avg
    k = S["k_sensitivity"]
    dyn = 1.0 + k * (avg_short - current_price) / max(avg_short, 1e-9)

    # Only boost if BELOW both short & medium; only shrink if ABOVE both.
    if current_price < avg_short and current_price < avg_medium:
        dyn = max(dyn, 1.0)  # ensure ≥1 when clearly cheap
    elif current_price > avg_short and current_price > avg_medium:
        dyn = min(dyn, 1.0)  # ensure ≤1 when clearly expensive
    else:
        # ambiguous zone; lean mild
        dyn = (dyn * 0.5) + 0.5  # pull toward 1.0

    # --- Buy-window multiplier (step 2) ---
    lookback = S["window_lookback_hours"]
    lower_p = S["lower_percentile"]
    upper_p = S["upper_percentile"]
    last_px, low_win, high_win = get_price_percentiles(product_id, lookback, lower_p, upper_p)
    win_mult = 1.0
    if last_px is not None and low_win is not None and high_win is not None:
        if last_px <= low_win:
            win_mult *= S["window_boost"]
        elif last_px >= high_win:
            win_mult *= S["window_cut"]

    # --- Reserve behavior (step 3) ---
    # Normal times: scale by (1 - reserve_fraction); deep dip: release reserve
    res_frac = S["reserve_fraction"]
    reserve_mult = (1.0 - res_frac)
    deep_dip = (current_price <= (1.0 - S["deep_dip_release_threshold"]) * avg_medium)
    if deep_dip:
        # neutralize the reserve reduction and add a small extra boost
        reserve_mult = (1.0 / max(1e-9, 1.0 - res_frac)) * S["reserve_release_boost"]

    # Combine multipliers
    raw_mult = dyn * win_mult * reserve_mult

    # Guardrails
    raw_mult = _clip(raw_mult, S["min_shrink"], S["max_boost"])

    # Final USD to buy (before price-adjustment for limit)
    effective_usd = baseline_usd * raw_mult

    # Per-run cap and minimum
    if effective_usd > S["per_run_cap_usd"]:
        effective_usd = S["per_run_cap_usd"]
    if effective_usd < S["min_order_usd"]:
        send_to_discord(
            f"{product_id}: computed ${effective_usd:.2f} below min ${S['min_order_usd']:.2f}; skipping."
        )
        return

    # Price for post-only limit: improve by price_adjustment_percentage
    adjusted_price = current_price * (1.0 - price_adjustment_percentage)

    # Base size from effective_usd
    base_size = effective_usd / max(adjusted_price, 1e-9)
    base_size = round(base_size, 8)

    # Place order
    try:
        order = client.limit_order_gtc_buy(
            client_order_id=f"{product_id}_{int(time.time())}",
            product_id=product_id,
            base_size=str(base_size),
            limit_price=str(math.floor(adjusted_price)),
            post_only=post_only
        )

        # Log details to Discord for visibility
        msg = (
            f"[{product_id}] Current ${current_price:.2f} | "
            f"S-avg({short_hours}h) ${avg_short:.2f} | "
            f"M-avg({medium_hours}h) ${avg_medium:.2f} | "
            f"Win[{lower_p}/{upper_p}] ~ "
            f"{'N/A' if (low_win is None or high_win is None) else f'[{low_win:.2f},{high_win:.2f}]'}\n"
            f"Multipliers: dyn={dyn:.2f}, win={win_mult:.2f}, reserve={reserve_mult:.2f} "
            f"→ raw={raw_mult:.2f}\n"
            f"USD: baseline ${baseline_usd:.2f} → effective ${effective_usd:.2f}; "
            f"limit @ ${adjusted_price:.2f}; size={base_size}"
        )

        if order.get('success'):
            send_to_discord("✅ " + msg + " → Order placed.")
        else:
            send_to_discord("❌ " + msg + f" → Error: {order.get('error_response')}")
    except Exception as e:
        send_to_discord(f"Failed to place order for {product_id}: {e}")

# Execute purchases for all configured coins
if __name__ == "__main__":
    for coin in config.COINS:
        buy_coin(coin)
