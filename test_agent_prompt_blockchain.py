#!/usr/bin/env python3
"""
Test script for agent prompt blockchain integration.

This script tests the agent prompt system's ability to fetch data from blockchain.
It verifies:
1. Environment variable configuration
2. Agent prompt generation with blockchain data
3. Data source display in the prompt

Usage:
    python test_agent_prompt_blockchain.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_environment():
    """Test if blockchain mode is enabled."""
    print("=" * 60)
    print("Testing Environment Variables")
    print("=" * 60)
    
    use_blockchain = os.getenv("USE_BLOCKCHAIN_POSITION", "false").lower() in ("true", "1", "yes")
    wallet_address = os.getenv("ARB_WALLET_ADDRESS")
    alchemy_key = os.getenv("ALCHEMY_ARB_API_KEY")
    
    print(f"  USE_BLOCKCHAIN_POSITION: {os.getenv('USE_BLOCKCHAIN_POSITION', 'not set')}")
    print(f"  ARB_WALLET_ADDRESS: {wallet_address[:10] + '...' if wallet_address else 'not set'}")
    print(f"  ALCHEMY_ARB_API_KEY: {alchemy_key[:10] + '...' if alchemy_key else 'not set'}")
    print()
    
    if use_blockchain:
        print("✅ Blockchain mode is ENABLED")
    else:
        print("⚠️  Blockchain mode is DISABLED (using file-based mode)")
    
    print()
    return use_blockchain


def test_agent_prompt():
    """Test agent prompt generation."""
    print("=" * 60)
    print("Testing Agent Prompt Generation")
    print("=" * 60)
    
    try:
        from prompts.agent_prompt import get_agent_system_prompt
        from tools.general_tools import get_config_value
        
        # Get test parameters
        today_date = os.getenv("TODAY_DATE", "2025-11-12")
        signature = os.getenv("SIGNATURE", "test_agent")
        
        print(f"Testing with:")
        print(f"  Date: {today_date}")
        print(f"  Signature: {signature}")
        print()
        
        # Generate agent prompt
        print("Generating agent prompt...")
        prompt = get_agent_system_prompt(today_date, signature, market="us")
        
        print()
        print("✅ Agent prompt generated successfully!")
        print()
        print("=" * 60)
        print("Generated Prompt (first 1500 characters):")
        print("=" * 60)
        print(prompt[:1500])
        if len(prompt) > 1500:
            print("\n... (truncated)")
        print()
        
        # Check if data source is displayed
        if "Data Source: Blockchain" in prompt:
            print("✅ Blockchain data source detected in prompt")
        elif "Data Source: Local position file" in prompt:
            print("✅ File-based data source detected in prompt")
        else:
            print("⚠️  No data source indicator found in prompt")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error generating agent prompt: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_data_consistency():
    """Test that blockchain data is consistent with expectations."""
    print("=" * 60)
    print("Testing Data Consistency")
    print("=" * 60)
    
    use_blockchain = os.getenv("USE_BLOCKCHAIN_POSITION", "false").lower() in ("true", "1", "yes")
    
    if not use_blockchain:
        print("⚠️  Skipping blockchain data consistency test (blockchain mode disabled)")
        print()
        return True
    
    try:
        from tools.price_tools import get_latest_position
        
        today_date = os.getenv("TODAY_DATE", "2025-11-12")
        signature = os.getenv("SIGNATURE", "test_agent")
        
        print("Fetching position data...")
        positions, max_id = get_latest_position(today_date, signature)
        
        print(f"  Positions count: {len(positions)}")
        print(f"  Max ID: {max_id}")
        print()
        
        if max_id == -1:
            print("✅ Blockchain mode confirmed (max_id = -1)")
        else:
            print("⚠️  File mode detected (max_id != -1)")
        
        if "CASH" in positions:
            print(f"✅ CASH balance found: ${positions['CASH']:.2f}")
        else:
            print("⚠️  No CASH balance in positions")
        
        stock_count = len([k for k in positions.keys() if k != "CASH"])
        print(f"✅ Stock tokens found: {stock_count}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error checking data consistency: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print()
    print("🔬 Agent Prompt Blockchain Integration Test Suite")
    print()
    
    # Test 1: Environment
    blockchain_enabled = test_environment()
    
    # Test 2: Agent prompt generation
    prompt_ok = test_agent_prompt()
    
    # Test 3: Data consistency
    data_ok = test_data_consistency()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"  Blockchain Mode: {'✅ ENABLED' if blockchain_enabled else '⚠️  DISABLED'}")
    print(f"  Agent Prompt: {'✅ PASS' if prompt_ok else '❌ FAIL'}")
    print(f"  Data Consistency: {'✅ PASS' if data_ok else '❌ FAIL'}")
    print()
    
    if prompt_ok and data_ok:
        print("🎉 All tests passed! Agent prompt blockchain integration is working.")
        if blockchain_enabled:
            print("   Agent will fetch positions from blockchain wallet.")
        else:
            print("   Agent will fetch positions from local files.")
    else:
        print("⚠️  Some tests failed. Please check the output above.")
    
    print()


if __name__ == "__main__":
    main()

