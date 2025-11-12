import os
import sys
from typing import Any, Dict, List, Optional
import asyncio
import json
import fcntl
from pathlib import Path

from fastmcp import FastMCP

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.general_tools import get_config_value, write_config_value
from tools.price_tools import (get_latest_position, get_open_prices,
                               get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit)
from agent_tools.blockchain.evm import ARBITRUM_CLIENT, USDC_DECIMAL
from agent_tools.blockchain.constants import STOCK_ADDRESS, TRADING_ADDRESS, USDC_ADDRESSES

mcp = FastMCP("TradeTools")

def _position_lock(signature: str):
    """Context manager for file-based lock to serialize position updates per signature."""
    class _Lock:
        def __init__(self, name: str):
            base_dir = Path(project_root) / "data" / "agent_data" / name
            base_dir.mkdir(parents=True, exist_ok=True)
            self.lock_path = base_dir / ".position.lock"
            # Ensure lock file exists
            self._fh = open(self.lock_path, "a+")
        def __enter__(self):
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            return self
        def __exit__(self, exc_type, exc, tb):
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
    return _Lock(signature)



@mcp.tool()
def buy(symbol: str, amount: int, expiry_days: int = 2) -> Dict[str, Any]:
    """
    Buy stock function

    This function simulates stock buying operations, including the following steps:
    1. Get current position and operation ID
    2. Get stock opening price for the day
    3. Validate buy conditions (sufficient cash, lot size for CN market)
    4. Update position (increase stock quantity, decrease cash)
    5. Record transaction to position.jsonl file (or execute blockchain transaction)

    Args:
        symbol: Stock symbol, such as "AAPL", "MSFT", etc.
        amount: Buy quantity, must be a positive integer, indicating how many shares to buy
                For Chinese A-shares (symbols ending with .SH or .SZ), must be multiples of 100
        expiry_days: Number of days until the limit order expires (default: 2)

    Returns:
        Dict[str, Any]:
          - Success: Returns new position dictionary (containing stock quantity and cash balance)
          - Failure: Returns {"error": error message, ...} dictionary

    Raises:
        ValueError: Raised when SIGNATURE environment variable is not set

    Example:
        >>> result = buy("AAPL", 10)
        >>> print(result)  # {"AAPL": 110, "MSFT": 5, "CASH": 5000.0, ...}
        >>> result = buy("600519.SH", 100)  # Chinese A-shares must be multiples of 100
        >>> print(result)  # {"600519.SH": 100, "CASH": 85000.0, ...}
        >>> result = buy("AAPL", 10, expiry_days=3)  # Limit order expires in 3 days
    """
    # Step 1: Get environment variables and basic information
    # Get signature (model name) from environment variable, used to determine data storage path
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")

    # Get current trading date from environment variable
    today_date = get_config_value("TODAY_DATE")

    # Auto-detect market type based on symbol format
    market = "cn" if symbol.endswith((".SH", ".SZ")) else "us"

    # 🇨🇳 Chinese A-shares trading rule: Must trade in lots of 100 shares (一手 = 100股)
    if market == "cn" and amount % 100 != 0:
        return {
            "error": f"Chinese A-shares must be traded in multiples of 100 shares (1 lot = 100 shares). You tried to buy {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
            "suggestion": f"Please use {(amount // 100) * 100} or {((amount // 100) + 1) * 100} shares instead.",
        }

    # Step 2: Get current latest position and operation ID
    # get_latest_position returns two values: position dictionary and current maximum operation ID
    # This ID is used to ensure each operation has a unique identifier
    # Acquire lock for atomic read-modify-write on positions
    with _position_lock(signature):
        try:
            current_position, current_action_id = get_latest_position(today_date, signature)
        except Exception as e:
            print(e)
            print(today_date, signature)
            return {"error": f"Failed to load latest position: {e}", "symbol": symbol, "date": today_date}
    # Step 3: Get stock opening price for the day
    # Use get_open_prices function to get the opening price of specified stock for the day
    # If stock symbol does not exist or price data is missing, KeyError exception will be raised
    try:
        this_symbol_price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        # Stock symbol does not exist or price data is missing, return error message
        return {
            "error": f"Symbol {symbol} not found! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Step 4: Validate buy conditions
    # Calculate cash required for purchase: stock price × buy quantity
    try:
        cash_left = current_position["CASH"] - this_symbol_price * amount
    except Exception as e:
        print(current_position, "CASH", this_symbol_price, amount)

    # Check if cash balance is sufficient for purchase
    if cash_left < 0:
        # Insufficient cash, return error message
        return {
            "error": "Insufficient cash! This action will not be allowed.",
            "required_cash": this_symbol_price * amount,
            "cash_available": current_position.get("CASH", 0),
            "symbol": symbol,
            "date": today_date,
        }
    else:
        # Step 5: Execute buy operation, update position
        # Create a copy of current position to avoid directly modifying original data
        new_position = current_position.copy()

        # Decrease cash balance
        new_position["CASH"] = cash_left

        # Increase stock position quantity
        new_position[symbol] += amount

        # Step 6: Record transaction to position.jsonl file
        # In blockchain mode (indicated by current_action_id == -1), skip writing to position.jsonl
        # Position data is maintained on-chain in blockchain mode
        use_blockchain = os.getenv("USE_BLOCKCHAIN_POSITION", "true").lower() in ("true", "1", "yes")
        
        if not use_blockchain:
            # File mode: write transaction to position.jsonl
            log_path = get_config_value("LOG_PATH", "./data/agent_data")
            if log_path.startswith("./data/"):
                log_path = log_path[7:]  # Remove "./data/" prefix
            position_file_path = os.path.join(project_root, "data", log_path, signature, "position", "position.jsonl")
            with open(position_file_path, "a") as f:
                # Write JSON format transaction record, containing date, operation ID, transaction details and updated position
                print(
                    f"Writing to position.jsonl: {json.dumps({'date': today_date, 'id': current_action_id + 1, 'this_action':{'action':'buy','symbol':symbol,'amount':amount},'positions': new_position})}"
                )
                f.write(
                    json.dumps(
                        {
                            "date": today_date,
                            "id": current_action_id + 1,
                            "this_action": {"action": "buy", "symbol": symbol, "amount": amount},
                            "positions": new_position,
                        }
                    )
                    + "\n"
                )
        else:
            # Blockchain mode: Execute limit buy order on-chain
            print(f"Blockchain mode: Placing limit BUY order for {amount} shares of {symbol} at ${this_symbol_price:.2f}")
            
            try:
                # Get wallet address and private key from environment
                wallet_address = os.getenv("ARB_WALLET_ADDRESS")
                private_key = os.getenv("ARB_PRIVATE_KEY")
                
                if not wallet_address or not private_key:
                    raise ValueError("ARB_WALLET_ADDRESS and ARB_PRIVATE_KEY must be set for blockchain trading")
                
                # Get stock token address
                if symbol not in STOCK_ADDRESS:
                    raise ValueError(f"Stock token address not found for {symbol}")
                
                stock_token_address = STOCK_ADDRESS[symbol].token_address
                
                # Calculate amounts in wei
                # For buy order: offer USDC, request stock tokens
                usdc_amount_wei = int(this_symbol_price * amount * (10 ** 6))  # USDC has 6 decimals
                stock_amount_wei = int(amount * (10 ** 18))  # Stock tokens typically have 18 decimals
                
                # Construct memo JSON
                memo = {
                    "did_id": wallet_address,
                    "request": str(stock_amount_wei),  # Request stock tokens
                    "offer": str(usdc_amount_wei),     # Offer USDC
                    "type": "LIMIT",
                    "token_address": stock_token_address,
                    "customer_id": "SVIM",
                    "expiry_days": expiry_days
                }
                memo_text = json.dumps(memo)
                
                # Recipient address for all trades
                recipient_address = TRADING_ADDRESS
                
                # USDC token address on Arbitrum
                usdc_address = USDC_ADDRESSES["arbitrum"]
                
                print(f"  Sending {usdc_amount_wei / (10**6):.6f} USDC to {recipient_address[:10]}...")
                print(f"  Memo: {memo_text[:100]}...")
                
                # Execute blockchain transaction
                tx_hash = asyncio.run(ARBITRUM_CLIENT.send_token_with_memo(
                    token_address=usdc_address,
                    recipient_address=recipient_address,
                    amount=usdc_amount_wei,
                    memo_text=memo_text,
                    private_key=private_key
                ))
                
                print(f"  ✓ Transaction submitted: {tx_hash}")
                print(f"  Expected new CASH: ${new_position['CASH']:.2f}, Expected new {symbol} position: {new_position.get(symbol, 0)}")
                
            except Exception as e:
                print(f"  ✗ Blockchain transaction failed: {e}")
                return {"error": f"Blockchain transaction failed: {e}", "symbol": symbol, "date": today_date}
        
        # Step 7: Return updated position
        write_config_value("IF_TRADE", True)
        print("IF_TRADE", get_config_value("IF_TRADE"))
        return new_position


def _get_today_buy_amount(symbol: str, today_date: str, signature: str) -> int:
    """
    Helper function to get the total amount bought today for T+1 restriction check

    Args:
        symbol: Stock symbol
        today_date: Trading date
        signature: Model signature

    Returns:
        Total shares bought today
    """
    log_path = get_config_value("LOG_PATH", "./data/agent_data")
    if log_path.startswith("./data/"):
        log_path = log_path[7:]  # Remove "./data/" prefix
    position_file_path = os.path.join(project_root, "data", log_path, signature, "position", "position.jsonl")

    if not os.path.exists(position_file_path):
        return 0

    total_bought_today = 0
    with open(position_file_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("date") == today_date:
                    this_action = record.get("this_action", {})
                    if this_action.get("action") == "buy" and this_action.get("symbol") == symbol:
                        total_bought_today += this_action.get("amount", 0)
            except Exception:
                continue

    return total_bought_today


@mcp.tool()
def sell(symbol: str, amount: int, expiry_days: int = 2) -> Dict[str, Any]:
    """
    Sell stock function

    This function simulates stock selling operations, including the following steps:
    1. Get current position and operation ID
    2. Get stock opening price for the day
    3. Validate sell conditions (position exists, sufficient quantity, lot size, T+1 for CN market)
    4. Update position (decrease stock quantity, increase cash)
    5. Record transaction to position.jsonl file (or execute blockchain transaction)

    Args:
        symbol: Stock symbol, such as "AAPL", "MSFT", etc.
        amount: Sell quantity, must be a positive integer, indicating how many shares to sell
                For Chinese A-shares (symbols ending with .SH or .SZ), must be multiples of 100
                and cannot sell shares bought on the same day (T+1 rule)
        expiry_days: Number of days until the limit order expires (default: 2)

    Returns:
        Dict[str, Any]:
          - Success: Returns new position dictionary (containing stock quantity and cash balance)
          - Failure: Returns {"error": error message, ...} dictionary

    Raises:
        ValueError: Raised when SIGNATURE environment variable is not set

    Example:
        >>> result = sell("AAPL", 10)
        >>> print(result)  # {"AAPL": 90, "MSFT": 5, "CASH": 15000.0, ...}
        >>> result = sell("600519.SH", 100)  # Chinese A-shares must be multiples of 100
        >>> print(result)  # {"600519.SH": 0, "CASH": 115000.0, ...}
        >>> result = sell("AAPL", 10, expiry_days=3)  # Limit order expires in 3 days
    """
    # Step 1: Get environment variables and basic information
    # Get signature (model name) from environment variable, used to determine data storage path
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")

    # Get current trading date from environment variable
    today_date = get_config_value("TODAY_DATE")

    # Auto-detect market type based on symbol format
    market = "cn" if symbol.endswith((".SH", ".SZ")) else "us"

    # 🇨🇳 Chinese A-shares trading rule: Must trade in lots of 100 shares (一手 = 100股)
    if market == "cn" and amount % 100 != 0:
        return {
            "error": f"Chinese A-shares must be traded in multiples of 100 shares (1 lot = 100 shares). You tried to sell {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
            "suggestion": f"Please use {(amount // 100) * 100} or {((amount // 100) + 1) * 100} shares instead.",
        }

    # Step 2: Get current latest position and operation ID
    # get_latest_position returns two values: position dictionary and current maximum operation ID
    # This ID is used to ensure each operation has a unique identifier
    current_position, current_action_id = get_latest_position(today_date, signature)

    # Step 3: Get stock opening price for the day
    # Use get_open_prices function to get the opening price of specified stock for the day
    # If stock symbol does not exist or price data is missing, KeyError exception will be raised
    try:
        this_symbol_price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        # Stock symbol does not exist or price data is missing, return error message
        return {
            "error": f"Symbol {symbol} not found! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Step 4: Validate sell conditions
    # Check if holding this stock
    if symbol not in current_position:
        return {
            "error": f"No position for {symbol}! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Check if position quantity is sufficient for selling
    if current_position[symbol] < amount:
        return {
            "error": "Insufficient shares! This action will not be allowed.",
            "have": current_position.get(symbol, 0),
            "want_to_sell": amount,
            "symbol": symbol,
            "date": today_date,
        }

    # 🇨🇳 Chinese A-shares T+1 trading rule: Cannot sell shares bought on the same day
    if market == "cn":
        bought_today = _get_today_buy_amount(symbol, today_date, signature)
        if bought_today > 0:
            # Calculate sellable quantity (total position - bought today)
            sellable_amount = current_position[symbol] - bought_today
            if amount > sellable_amount:
                return {
                    "error": f"T+1 restriction violated! You bought {bought_today} shares of {symbol} today and cannot sell them until tomorrow.",
                    "symbol": symbol,
                    "total_position": current_position[symbol],
                    "bought_today": bought_today,
                    "sellable_today": max(0, sellable_amount),
                    "want_to_sell": amount,
                    "date": today_date,
                }

    # Step 5: Execute sell operation, update position
    # Create a copy of current position to avoid directly modifying original data
    new_position = current_position.copy()

    # Decrease stock position quantity
    new_position[symbol] -= amount

    # Increase cash balance: sell price × sell quantity
    # Use get method to ensure CASH field exists, default to 0 if not present
    new_position["CASH"] = new_position.get("CASH", 0) + this_symbol_price * amount

    # Step 6: Record transaction to position.jsonl file
    # In blockchain mode, skip writing to position.jsonl
    # Position data is maintained on-chain in blockchain mode
    use_blockchain = os.getenv("USE_BLOCKCHAIN_POSITION", "true").lower() in ("true", "1", "yes")
    
    if not use_blockchain:
        # File mode: write transaction to position.jsonl
        log_path = get_config_value("LOG_PATH", "./data/agent_data")
        if log_path.startswith("./data/"):
            log_path = log_path[7:]  # Remove "./data/" prefix
        position_file_path = os.path.join(project_root, "data", log_path, signature, "position", "position.jsonl")
        with open(position_file_path, "a") as f:
            # Write JSON format transaction record, containing date, operation ID and updated position
            print(
                f"Writing to position.jsonl: {json.dumps({'date': today_date, 'id': current_action_id + 1, 'this_action':{'action':'sell','symbol':symbol,'amount':amount},'positions': new_position})}"
            )
            f.write(
                json.dumps(
                    {
                        "date": today_date,
                        "id": current_action_id + 1,
                        "this_action": {"action": "sell", "symbol": symbol, "amount": amount},
                        "positions": new_position,
                    }
                )
                + "\n"
            )
    else:
        # Blockchain mode: Execute limit sell order on-chain
        print(f"Blockchain mode: Placing limit SELL order for {amount} shares of {symbol} at ${this_symbol_price:.2f}")
        
        try:
            # Get wallet address and private key from environment
            wallet_address = os.getenv("ARB_WALLET_ADDRESS")
            private_key = os.getenv("ARB_PRIVATE_KEY")
            
            if not wallet_address or not private_key:
                raise ValueError("ARB_WALLET_ADDRESS and ARB_PRIVATE_KEY must be set for blockchain trading")
            
            # Get stock token address
            if symbol not in STOCK_ADDRESS:
                raise ValueError(f"Stock token address not found for {symbol}")
            
            stock_token_address = STOCK_ADDRESS[symbol].token_address
            
            # Calculate amounts in wei
            # For sell order: offer stock tokens, request USDC
            usdc_amount_wei = int(this_symbol_price * amount * (10 ** 6))  # USDC has 6 decimals
            stock_amount_wei = int(amount * (10 ** 18))  # Stock tokens typically have 18 decimals
            
            # Construct memo JSON
            memo = {
                "did_id": wallet_address,
                "request": str(usdc_amount_wei),    # Request USDC
                "offer": str(stock_amount_wei),     # Offer stock tokens
                "type": "LIMIT",
                "token_address": stock_token_address,
                "customer_id": "SVIM",
                "expiry_days": expiry_days
            }
            memo_text = json.dumps(memo)
            
            # Recipient address for all trades
            recipient_address = TRADING_ADDRESS
            
            print(f"  Sending {stock_amount_wei / (10**18):.6f} {symbol} tokens to {recipient_address[:10]}...")
            print(f"  Memo: {memo_text[:100]}...")
            
            # Execute blockchain transaction (send stock tokens)
            tx_hash = asyncio.run(ARBITRUM_CLIENT.send_token_with_memo(
                token_address=stock_token_address,
                recipient_address=recipient_address,
                amount=stock_amount_wei,
                memo_text=memo_text,
                private_key=private_key
            ))
            
            print(f"  ✓ Transaction submitted: {tx_hash}")
            print(f"  Expected new CASH: ${new_position['CASH']:.2f}, Expected new {symbol} position: {new_position.get(symbol, 0)}")
            
        except Exception as e:
            print(f"  ✗ Blockchain transaction failed: {e}")
            return {"error": f"Blockchain transaction failed: {e}", "symbol": symbol, "date": today_date}

    # Step 7: Return updated position
    write_config_value("IF_TRADE", True)
    return new_position


if __name__ == "__main__":
    # new_result = buy("AAPL", 1)
    # print(new_result)
    # new_result = sell("AAPL", 1)
    # print(new_result)
    port = int(os.getenv("TRADE_HTTP_PORT", "8002"))
    mcp.run(transport="streamable-http", port=port)
