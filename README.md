# Crypto Buyer Bot

A Python-based cryptocurrency buyer bot that interacts with the [Coinbase Advanced Trade API](https://docs.cloud.coinbase.com/advanced-trade-api/docs/using-python). Automates recurring cryptocurrency purchases and supports Docker deployment.

## Quick Start with Docker Hub

The pre-built Docker image is available on [Docker Hub](https://hub.docker.com/repository/docker/zihengjackchen/crypto-buyer/). Use the following commands to get started:

1. **Pull the Image**:
   ```bash
   docker pull zihengjackchen/crypto-buyer:latest
   ```

2. **Run the Container**:
   You can pass API credentials either as environment variables or using a `.env` file.

   - **Option 1: Using Environment Variables**:
     Export the API credentials directly in your shell:
     ```bash
     export API_KEY=your_api_key_here
     export API_SECRET=your_api_secret_here
     ```
     Run the container:
     ```bash
     docker run -e API_KEY -e API_SECRET -d zihengjackchen/crypto-buyer:latest
     ```

   - **Option 2: Using a `.env` File**:
     Create a `.env` file with your credentials:
     ```env
     API_KEY=your_api_key_here
     API_SECRET=your_api_secret_here
     ```
     Run the container:
     ```bash
     docker run --env-file .env -d zihengjackchen/crypto-buyer:latest
     ```

---

## Features
- Automates cryptocurrency purchases via the Coinbase API.
- Configurable per-coin USD allocation and price adjustments.
- Supports **post-only limit buy orders**.
- Environment-based API credential management (no `.env` file needed if using exported variables).
- Dockerized for portability and ease of use.

---

## Setup and Usage (Building Locally)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/zihengjackchen/crypto-buyer-bot.git
   cd crypto-buyer-bot
   ```

2. **Set Up API Credentials**:
   - Use environment variables:
     ```bash
     export API_KEY=your_api_key_here
     export API_SECRET=your_api_secret_here
     ```
   - Alternatively, create a `.env` file:
     ```env
     API_KEY=your_api_key_here
     API_SECRET=your_api_secret_here
     ```

3. **Build and Run the Docker Image**:
   ```bash
   docker build -t crypto-buyer .
   docker run --env-file .env -d crypto-buyer
   ```

---

## Configuration

Customize your coin purchases in `config.py`:
```python
COINS = [
    {
        "product_id": "BTC-USDC",
        "usd_to_buy": 3,
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
```

---

## License
This project is licensed under the MIT License.
