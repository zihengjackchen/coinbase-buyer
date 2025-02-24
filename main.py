from coinbase.rest import RESTClient
import math
import time
import datetime
import config
from typing import Optional
from send_to_discord import send_to_discord

# Initialize client
client = RESTClient(api_key=config.API_KEY, api_secret=config.API_SECRET)

def get_average_close_price(product_id: str, hours: int = 72) -> Optional[float]:
    """
    Fetch the daily candles for the product and compute the average
    closing price for the last 'days' days.
    """
    # Calculate the start and end timestamps in ISO format
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
        send_to_discord(f"Error fetching historical candles for {product_id}: {e}")
        return None

    if not candles:
        send_to_discord(f"No historical data available for {product_id}")
        return None

    closes = [float(candle["close"]) for candle in candles["candles"]]

    return sum(closes) / len(closes) if closes else None

def buy_coin(coin_config):
    """Function to buy a single coin based on its configuration."""
    product_id = coin_config["product_id"]
    usd_to_buy = coin_config["usd_to_buy"]
    post_only = coin_config["post_only"]
    price_adjustment_percentage = coin_config["price_adjustment_percentage"]
    price_threshold = coin_config["price_threshold"]
    
    # Fetch product information (current price)
    try:
        product = client.get_product(product_id)
        current_price = float(product["price"])
    except Exception as e:
        send_to_discord(f"Error fetching price for {product_id}: {e}")
        return

    # Get average close price of the last 3 days
    average_3day_close = get_average_close_price(product_id)

    if average_3day_close is None:
        send_to_discord(f"Could not fetch historical data for {product_id}, skipping buy.")
        return

    # Check conditions to decide whether to buy
    if current_price > price_threshold and current_price > average_3day_close:
        send_to_discord(
            f"Skipping order for {product_id} because current price "
            f"(${current_price:.2f}) is not below threshold "
            f"(${price_threshold:.2f}) or below 3-day avg "
            f"(${average_3day_close:.2f})."
        )
        return
    
    # Adjust price for the order
    adjusted_price = current_price - (current_price * price_adjustment_percentage)

    # Calculate base size
    base_size = usd_to_buy / adjusted_price  # up to 8 decimal places
    scale = max(average_3day_close / current_price, price_threshold / current_price)
    base_size = round(base_size * scale, 8)

    try:
        # Place a post-only limit buy order
        order = client.limit_order_gtc_buy(
            client_order_id=f"{product_id}_{int(time.time())}",  # Unique ID for each order
            product_id=product_id,
            base_size=str(base_size),  # Convert to string for the API
            limit_price=str(math.floor(adjusted_price)),  # Round price down
            post_only=post_only
        )

        # Handle order response
        if order['success']:
            order_id = order['success_response']['order_id']
            send_to_discord(
                f"Order placed successfully for {product_id} with ID: {order_id}"
                f" at ${adjusted_price:.2f} for {base_size} units."
                f" Average 3-day close: ${average_3day_close:.2f}."
            )
        else:
            error_response = order['error_response']
            send_to_discord(f"Error placing order for {product_id}:", error_response)

    except Exception as e:
        send_to_discord(f"Failed to place order for {product_id}: {e}")

# Execute purchases for all configured coins
if __name__ == "__main__":
    for coin in config.COINS:
        buy_coin(coin)
