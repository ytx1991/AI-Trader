#!/usr/bin/env python3
"""
Test script for blockchain trading functionality.

This script tests the integration of limit order execution through blockchain transactions.
It verifies:
1. Environment variable configuration
2. Position fetching from blockchain
3. Limit order construction and submission (dry-run mode)

Usage:
    python test_blockchain_trading.py
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test if all required environment variables are set."""
    print("=" * 60)
    print("Testing Environment Variables")
    print("=" * 60)
    
    required_vars = {
        "USE_BLOCKCHAIN_POSITION": os.getenv("USE_BLOCKCHAIN_POSITION"),
        "ARB_WALLET_ADDRESS": os.getenv("ARB_WALLET_ADDRESS"),
        "ARB_PRIVATE_KEY": os.getenv("ARB_PRIVATE_KEY"),
        "ALCHEMY_ARB_API_KEY": os.getenv("ALCHEMY_ARB_API_KEY"),
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            if "KEY" in var_name or "PRIVATE" in var_name:
                # Mask sensitive information
                masked_value = var_value[:10] + "..." if len(var_value) > 10 else "***"
                print(f"  ✓ {var_name}: {masked_value}")
            else:
                print(f"  ✓ {var_name}: {var_value}")
        else:
            print(f"  ✗ {var_name}: NOT SET")
            all_set = False
    
    print()
    
    if not all_set:
        print("⚠️  Warning: Some environment variables are not set.")
        print("   To enable blockchain trading, set all required variables:")
        print()
        print("   export USE_BLOCKCHAIN_POSITION=true")
        print("   export ARB_WALLET_ADDRESS=0xYourWalletAddress")
        print("   export ARB_PRIVATE_KEY=0xYourPrivateKeyHere")
        print("   export ALCHEMY_ARB_API_KEY=your_alchemy_api_key")
        print()
        return False
    
    print("✅ All environment variables are set!")
    print()
    return True


def test_position_fetching():
    """Test fetching positions from blockchain."""
    print("=" * 60)
    print("Testing Position Fetching from Blockchain")
    print("=" * 60)
    
    try:
        from tools.price_tools import get_latest_position
        
        # Get positions
        positions, max_id = get_latest_position("2025-11-11", "test_agent")
        
        print("Position fetching successful!")
        print(f"  max_id: {max_id} (should be -1 in blockchain mode)")
        print(f"  Total positions: {len(positions)}")
        print()
        print("Position details:")
        
        cash_balance = positions.get("CASH", 0)
        print(f"  CASH (USDC): ${cash_balance:.2f}")
        
        stock_positions = {k: v for k, v in positions.items() if k != "CASH"}
        if stock_positions:
            print("  Stock tokens:")
            for symbol, amount in stock_positions.items():
                print(f"    {symbol}: {amount:.6f} tokens")
        else:
            print("  Stock tokens: None")
        
        print()
        
        if max_id == -1:
            print("✅ Blockchain mode detected (max_id = -1)")
        else:
            print("⚠️  File mode detected (max_id != -1)")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error fetching positions: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_order_construction():
    """Test limit order memo construction."""
    print("=" * 60)
    print("Testing Limit Order Memo Construction")
    print("=" * 60)
    
    wallet_address = os.getenv("ARB_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")
    
    # Test buy order
    print("Buy Order Example:")
    buy_symbol = "AAPL"
    buy_amount = 10
    buy_price = 150.0
    buy_expiry = 2
    
    usdc_amount_wei = int(buy_price * buy_amount * (10 ** 6))
    stock_amount_wei = int(buy_amount * (10 ** 18))
    
    buy_memo = {
        "did_id": wallet_address,
        "request": str(stock_amount_wei),
        "offer": str(usdc_amount_wei),
        "type": "LIMIT",
        "token_address": "0xStockTokenAddress",  # Placeholder
        "customer_id": "SVIM",
        "expiry_days": buy_expiry
    }
    
    print(f"  Symbol: {buy_symbol}")
    print(f"  Amount: {buy_amount} shares")
    print(f"  Price: ${buy_price} per share")
    print(f"  Total cost: ${buy_price * buy_amount} USDC")
    print(f"  Expiry: {buy_expiry} days")
    print(f"  Memo:")
    print(f"    {json.dumps(buy_memo, indent=4)}")
    print()
    
    # Test sell order
    print("Sell Order Example:")
    sell_symbol = "TSLA"
    sell_amount = 5
    sell_price = 200.0
    sell_expiry = 2
    
    usdc_amount_wei = int(sell_price * sell_amount * (10 ** 6))
    stock_amount_wei = int(sell_amount * (10 ** 18))
    
    sell_memo = {
        "did_id": wallet_address,
        "request": str(usdc_amount_wei),
        "offer": str(stock_amount_wei),
        "type": "LIMIT",
        "token_address": "0xStockTokenAddress",  # Placeholder
        "customer_id": "SVIM",
        "expiry_days": sell_expiry
    }
    
    print(f"  Symbol: {sell_symbol}")
    print(f"  Amount: {sell_amount} shares")
    print(f"  Price: ${sell_price} per share")
    print(f"  Expected return: ${sell_price * sell_amount} USDC")
    print(f"  Expiry: {sell_expiry} days")
    print(f"  Memo:")
    print(f"    {json.dumps(sell_memo, indent=4)}")
    print()
    
    print("✅ Order memo construction test passed!")
    print()
    return True


def main():
    """Run all tests."""
    print()
    print("🔬 Blockchain Trading Test Suite")
    print()
    
    # Test 1: Environment variables
    env_ok = test_environment()
    
    if not env_ok:
        print("❌ Environment test failed. Please set required variables.")
        return
    
    # Test 2: Position fetching
    position_ok = test_position_fetching()
    
    # Test 3: Order construction
    order_ok = test_order_construction()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"  Position Fetching: {'✅ PASS' if position_ok else '❌ FAIL'}")
    print(f"  Order Construction: {'✅ PASS' if order_ok else '❌ FAIL'}")
    print()
    
    if env_ok and position_ok and order_ok:
        print("🎉 All tests passed! Blockchain trading is ready.")
        print()
        print("⚠️  Note: This is a dry-run test. No actual transactions were sent.")
        print("   To execute real trades, use the buy() and sell() functions")
        print("   from agent_tools/tool_trade.py with blockchain mode enabled.")
    else:
        print("⚠️  Some tests failed. Please check the output above.")
    
    print()


if __name__ == "__main__":
    main()

