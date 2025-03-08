# API key and secret
import os

# API key and secret from environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Coin configurations
COINS = [
    {
        "product_id": "BTC-USDC",
        "usd_to_buy": 10,  # Amount of USD to spend
        "price_adjustment_percentage": 0.01,
        "post_only": True,
        "price_threshold": 95000  # Price threshold to buy
    },
    {
        "product_id": "ETH-USDC",
        "usd_to_buy": 3,
        "price_adjustment_percentage": 0.01,
        "post_only": True,
        "price_threshold": 2500
    }
]