from datetime import datetime, timedelta, timezone

import requests
from cachetools import TTLCache, cached

from agent_tools.blockchain.constants import TRADING_ADDRESS
from constants import STOCK_ADDRESS, USDC_ADDRESSES, ORDER_PROCESSOR
from evm import Blockchain
from evm import CHAIN_IDS

PRICE_BUFFER = 0.0005

cache = TTLCache(maxsize=100, ttl=86400)
price_cache = TTLCache(maxsize=100, ttl=10)
quote_cache = TTLCache(maxsize=200, ttl=600)
TIMEOUT = 20

# Blockchain to chain ID mapping for Dinari API
BLOCKCHAIN_TO_CHAIN_ID = {
    Blockchain.ETHEREUM: CHAIN_IDS["ethereum"],
    Blockchain.ARBITRUM: CHAIN_IDS["arbitrum"], 
    Blockchain.BASE: CHAIN_IDS["base"],
    Blockchain.BNB: CHAIN_IDS["bnb"]
}
def fetch_token_infos(blockchain: Blockchain=Blockchain.ARBITRUM):
    """
    Fetch token information from Dinari API for specified blockchain
    
    Args:
        blockchain: The blockchain to fetch token infos for (default: ARB)
        
    Returns:
        List of token information dictionaries
        
    Raises:
        ValueError: If blockchain is not supported
        requests.RequestException: If API request fails
    """
    # Get chain ID for the blockchain
    chain_id = BLOCKCHAIN_TO_CHAIN_ID.get(blockchain)
    if chain_id is None:
        raise ValueError(f"Unsupported blockchain: {blockchain}")
    
    all_token_infos = []
    page = 1
    
    while True:
        url = f"https://api.sbt.dinari.com/api/v1/chain/{chain_id}/token_infos?page={page}"
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if not data or len(data) == 0:
                break
            all_token_infos.extend(data)
            page += 1
        else:
            response.raise_for_status()
    
    return all_token_infos

def get_stock_id_by_symbol(symbol, blockchain: Blockchain=Blockchain.ARBITRUM):
    """
    Get stock ID by symbol from specified blockchain
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        blockchain: The blockchain to search in (default: ARB)
        
    Returns:
        Stock ID
        
    Raises:
        ValueError: If stock symbol not found
    """
    # Create cache key that includes blockchain to avoid conflicts
    cache_key = f"{symbol}_{blockchain.name}"
    if cache_key in cache:
        return cache[cache_key]
    
    token_infos = fetch_token_infos(blockchain)
    for token_info in token_infos:
        stock = token_info.get('stock', {})
        if stock.get('symbol') == symbol:
            stock_id = stock.get('id')
            # Cache with blockchain-specific key
            cache[cache_key] = stock_id
            return stock_id
    
    raise ValueError(f"Stock symbol '{symbol}' not found on {blockchain.name} blockchain.")

def get_stock_price_from_dinari(symbol, blockchain: Blockchain=Blockchain.ARBITRUM):
    """
    Get stock price from Dinari API for specified blockchain
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'TSLA')
        blockchain: The blockchain to get price for (default: ARB)
        
    Returns:
        Tuple of (bid_price, ask_price)
        
    Raises:
        ValueError: If stock not found or no price data available
        requests.RequestException: If API request fails
    """
    # Create cache key that includes blockchain
    cache_key = f"{symbol}_{blockchain.name}"
    
    # Check cache first
    if cache_key in price_cache:
        return price_cache[cache_key]
    
    stock_id = get_stock_id_by_symbol(symbol, blockchain)
    url = f"https://api.sbt.dinari.com/api/v1/stocks/price_summaries?stock_ids={stock_id}"
    response = requests.get(url, timeout=TIMEOUT)
    
    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            stock_info = data[0]
            bp_price = f'{stock_info.get("price")*(1-PRICE_BUFFER):.2f}'
            ap_price = f'{stock_info.get("price")*(1+PRICE_BUFFER):.2f}'
            return bp_price, ap_price
        else:
            raise ValueError("No data found for the given stock ID.")
    else:
        response.raise_for_status()

@cached(quote_cache)
def quote_order(symbol: str, sell: bool, qty: str):
    url = "https://api.sbt.dinari.com/api/v1/order/sponsored/fee_estimate"
    inputs = {
        "chain_id": 42161,
        "order_data": {"requestTimestamp": int(datetime.now(timezone.utc).timestamp()),
                       "recipient": TRADING_ADDRESS,
                       "assetToken": STOCK_ADDRESS[symbol].token_address,
                       "paymentToken": USDC_ADDRESSES["arbitrum"],
                       "paymentTokenQuantity": "0" if sell else qty,
                       "assetTokenQuantity": qty if sell else "0",
                       "price": "0",
                       "sell": sell,
                       "tif": 1,
                       "orderType": 0}, "is_sponsored": False,
        "contract_address": ORDER_PROCESSOR
    }
    response = requests.post(url, json=inputs, timeout=TIMEOUT)
    total_fee = 0.0
    for fee in response.json()["fees"]:
        total_fee += float(fee["fee_in_eth"])
    return total_fee
