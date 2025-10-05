# API key and secret
import os

# API key and secret from environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Global strategy knobs (non-rebalancing)
STRATEGY = {
    # Horizons
    "short_hours": 72,          # ~3 days (kept from your logic)
    "medium_hours": 24 * 30,    # ~30 days
    # Dynamic multiplier sensitivity & caps
    # Multiplier = 1 + k * (avg_short - current)/avg_short, then combined with other factors
    "k_sensitivity": 1.0,
    "max_boost": 2.5,           # never buy > 2.5x baseline
    "min_shrink": 0.4,          # never buy < 0.4x baseline
    # Buy-window (percentile band over a longer lookback)
    "window_lookback_hours": 24 * 90,  # ~90 days
    "lower_percentile": 25,     # “cheap” window
    "upper_percentile": 75,     # “expensive” window
    "window_boost": 1.25,       # extra boost if below lower_percentile
    "window_cut": 0.85,         # extra cut if above upper_percentile
    # Reserve behavior (stateless simulation)
    "reserve_fraction": 0.20,   # keep 20% unspent during normal times
    # release reserve if deep dip vs MEDIAN horizon
    "deep_dip_release_threshold": 0.15, # release if current <= (1-0.20) * medium_avg
    "reserve_release_boost": 1.2,       # small extra when reserve is released
    # Safety
    "per_run_cap_usd": 50.0,    # max spend per coin per run
    "min_order_usd": 1.00       # skip tiny dust orders
}

# Coin configurations (baseline only; strategy above controls scaling)
COINS = [
    {
        "product_id": "BTC-USDC",
        "usd_to_buy": 12.0,      # baseline per run (your request)
        "price_adjustment_percentage": 0.01,
        "post_only": True,
    },
    {
        "product_id": "ETH-USDC",
        "usd_to_buy": 3.0,       # baseline per run (your request)
        "price_adjustment_percentage": 0.01,
        "post_only": True,
    }
]
