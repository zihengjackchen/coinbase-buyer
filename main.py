# main.py

from coinbase.rest import RESTClient
import math
import time
import config

# Initialize client
client = RESTClient(api_key=config.API_KEY, api_secret=config.API_SECRET)

def buy_coin(coin_config):
    """Function to buy a single coin based on its configuration."""
    product_id = coin_config["product_id"]
    usd_to_buy = coin_config["usd_to_buy"]
    post_only = coin_config["post_only"]
    price_adjustment_percentage = coin_config["price_adjustment_percentage"]
    
    # Fetch product information
    product = client.get_product(product_id)
    current_price = float(product["price"])
    
    # Adjust price with the specified percentage
    adjusted_price = current_price - (current_price * price_adjustment_percentage)
    
    # Calculate base size based on USD to buy and adjusted price
    base_size = round(usd_to_buy / adjusted_price, 8)  # Limit to 8 decimal places for precision
    
    # Place a post-only buy order
    order = client.limit_order_gtc_buy(
        client_order_id=f"{product_id}_{int(time.time())}",  # Unique ID for each order
        product_id=product_id,
        base_size=str(base_size),  # Convert to string for the API
        limit_price=str(math.floor(adjusted_price)),  # Ensure limit price is a whole number
        post_only=post_only
    )
    
    # Handle order response
    if order['success']:
        order_id = order['success_response']['order_id']
        print(f"Order placed successfully for {product_id} with ID: {order_id}")
    else:
        error_response = order['error_response']
        print(f"Error placing order for {product_id}:", error_response)

# Execute purchases for all configured coins
if __name__ == "__main__":
    for coin in config.COINS:
        buy_coin(coin)
