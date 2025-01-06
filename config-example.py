# config.py

# API key and secret
API_KEY = "organizations/{org_id}/apiKeys/{key_id}"
API_SECRET = """-----BEGIN EC PRIVATE KEY-----
YOUR PRIVATE KEY
-----END EC PRIVATE KEY-----"""

# Coin configurations
COINS = [
    {
        "product_id": "BTC-USDC",
        "usd_to_buy": 3,  # Amount of USD to spend
        "price_adjustment_percentage": 0.01,
        "post_only": True
    },
    {
        "product_id": "ETH-USDC",
        "usd_to_buy": 1,
        "price_adjustment_percentage": 0.01,
        "post_only": True
    }
]
