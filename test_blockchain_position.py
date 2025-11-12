#!/usr/bin/env python3
"""
Test script for blockchain position tracking functionality

This script tests the blockchain position tracking feature by:
1. Checking environment variables
2. Fetching positions from blockchain
3. Displaying results
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.price_tools import get_latest_position


def check_environment():
    """Check if required environment variables are set"""
    print("=" * 60)
    print("Environment Variables Check")
    print("=" * 60)
    
    # Check blockchain mode
    use_blockchain = os.getenv("USE_BLOCKCHAIN_POSITION", "false")
    print(f"USE_BLOCKCHAIN_POSITION: {use_blockchain}")
    
    # Check Arbitrum wallet address
    arb_wallet = os.getenv("ARB_WALLET_ADDRESS")
    print(f"ARB_WALLET_ADDRESS: {'✓ Set' if arb_wallet else '✗ Not set'}")
    if arb_wallet:
        print(f"  Address: {arb_wallet[:10]}...{arb_wallet[-8:]}")
    
    # Check Alchemy Arbitrum API key
    arb_key = os.getenv("ALCHEMY_ARB_API_KEY")
    print(f"ALCHEMY_ARB_API_KEY: {'✓ Set' if arb_key else '✗ Not set'}")
    
    print()
    
    # Determine active configuration
    if arb_wallet and arb_key:
        print(f"Active Configuration:")
        print(f"  Network: Arbitrum")
        print(f"  Wallet: {arb_wallet[:10]}...{arb_wallet[-8:]}")
        print(f"  API Key: {arb_key[:10]}...{arb_key[-4:]}")
    else:
        print("⚠️  Arbitrum configuration incomplete")
        if not arb_wallet:
            print("    Missing: ARB_WALLET_ADDRESS")
        if not arb_key:
            print("    Missing: ALCHEMY_ARB_API_KEY")
    
    print()
    return bool(arb_wallet and arb_key and use_blockchain.lower() in ("true", "1", "yes"))


def test_blockchain_position():
    """Test fetching position from blockchain"""
    print("=" * 60)
    print("Testing Blockchain Position Fetch")
    print("=" * 60)
    print()
    
    # Test parameters
    today_date = "2025-11-11"
    signature = "test_blockchain"
    
    print(f"Test Parameters:")
    print(f"  Date: {today_date}")
    print(f"  Signature: {signature}")
    print()
    
    try:
        print("Fetching positions...")
        positions, max_id = get_latest_position(today_date, signature)
        
        print()
        print("Results:")
        print(f"  Max ID: {max_id}")
        print(f"  Number of positions: {len(positions)}")
        print()
        
        if positions:
            print("Position Details:")
            print("-" * 60)
            total_value = 0
            for symbol, amount in sorted(positions.items()):
                if symbol != "CASH":
                    print(f"  {symbol:10s}: {amount:>12.6f} tokens")
                else:
                    print(f"  {symbol:10s}: ${amount:>12.2f}")
            print("-" * 60)
        else:
            print("  No positions found")
        
        print()
        print("✓ Test completed successfully")
        return True
        
    except Exception as e:
        print()
        print(f"✗ Test failed with error:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("Blockchain Position Tracking - Test Script")
    print("=" * 60)
    print()
    
    # Check environment
    env_ok = check_environment()
    
    if not env_ok:
        print("⚠️  Warning: Arbitrum blockchain mode not properly configured")
        print("   The test will run in file-based mode (fallback)")
        print()
        print("To enable blockchain mode, set these environment variables:")
        print("  export USE_BLOCKCHAIN_POSITION=true")
        print("  export ARB_WALLET_ADDRESS=0x...")
        print("  export ALCHEMY_ARB_API_KEY=...")
        print()
        print("Note: Only Arbitrum network is supported for dShare tokens.")
        print()
    
    # Run test
    success = test_blockchain_position()
    
    # Summary
    print()
    print("=" * 60)
    if success:
        print("✓ All tests passed")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
    print()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

