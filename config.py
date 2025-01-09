# API key and secret
import os

# API key and secret from environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Coin configurations
COINS = [
    {
        "product_id": "BTC-USDC",
        "usd_to_buy": 3,  # Amount of USD to spend
        "price_adjustment_percentage": 0.05,
        "post_only": True
    },
    {
        "product_id": "ETH-USDC",
        "usd_to_buy": 1,
        "price_adjustment_percentage": 0.05,
        "post_only": True
    }
]