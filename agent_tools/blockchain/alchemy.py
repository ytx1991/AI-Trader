import asyncio
import logging
import os
from typing import Dict, Any, Optional

import aiohttp

from .evm import ALCHEMY_API_KEYS

logger = logging.getLogger(__name__)

# Alchemy API base URL
ALCHEMY_DATA_API_BASE = "https://api.g.alchemy.com/data/v1"

# Network mapping configuration
NETWORK_MAPPING = {
    "ethereum": "eth-mainnet",
    "arbitrum": "arb-mainnet", 
    "base": "base-mainnet"
}



def _get_api_key_for_network(network: str) -> Optional[str]:
    """
    Get the corresponding API key based on the network
    
    Args:
        network: Alchemy network identifier (e.g.: eth-mainnet, arb-mainnet)
        
    Returns:
        API key or None if not found
    """
    if network.startswith("eth-"):
        return ALCHEMY_API_KEYS.get("ethereum")
    elif network.startswith("arb-"):
        return ALCHEMY_API_KEYS.get("arbitrum")
    elif network.startswith("base-"):
        return ALCHEMY_API_KEYS.get("base")
    else:
        logger.error(f"Unsupported network: {network}")
        return None


def _validate_network(network: str) -> bool:
    """
    Validate if the network name is supported
    
    Args:
        network: Network name
        
    Returns:
        Whether the network is supported
    """
    return network in NETWORK_MAPPING


def _get_alchemy_network(network: str) -> Optional[str]:
    """
    Convert user-friendly network name to Alchemy network identifier
    
    Args:
        network: User network name (ethereum, arbitrum, base, solana)
        
    Returns:
        Alchemy network identifier or None
    """
    return NETWORK_MAPPING.get(network)


def _get_cache_key(wallet_address: str, network: str) -> str:
    """
    Generate cache key
    
    Args:
        wallet_address: Wallet address
        network: Network name
        
    Returns:
        Cache key
    """
    return f"{wallet_address}_{network}"


async def get_tokens_balance(wallet_address: str, network: str = "ethereum") -> Optional[Dict[str, Any]]:
    """
    Get token balance for wallet address
    Uses Alchemy Portfolio API to get token balance information for specified wallet address and network
    
    Args:
        wallet_address: Wallet address
        network: Network name (ethereum, arbitrum, base, solana)
        
    Returns:
        Token data dictionary or None if failed
        
    Raises:
        ValueError: When network is not supported or wallet address is empty
        Exception: When API call fails
    """
    # Parameter validation
    if not wallet_address:
        raise ValueError("Wallet address cannot be empty")
    
    if not _validate_network(network):
        supported_networks = list(NETWORK_MAPPING.keys())
        raise ValueError(f"Unsupported network: {network}. Supported networks: {supported_networks}")
    
    # Get Alchemy network identifier
    alchemy_network = _get_alchemy_network(network)
    if not alchemy_network:
        raise ValueError(f"Cannot get Alchemy identifier for network {network}")
    
    # Check cache
    cache_key = _get_cache_key(wallet_address, network)
    
    try:
        # Call Alchemy Portfolio API
        tokens_data = await _fetch_tokens_from_alchemy_api(wallet_address, alchemy_network)
        
        if tokens_data is None:
            logger.error(f"Failed to get token balance for wallet {wallet_address} on network {network}")
            return None
        
        # Cache result (handled automatically by decorator)
        logger.info(f"Successfully retrieved {len(tokens_data.get('tokens', []))} tokens for wallet {wallet_address} on network {network}")
        return tokens_data
        
    except Exception as e:
        logger.error(f"Error occurred while getting token balance: {e}")
        raise


async def _fetch_tokens_from_alchemy_api(wallet_address: str, alchemy_network: str) -> Optional[Dict[str, Any]]:
    """
    Fetch token balance from Alchemy Portfolio API
    
    Args:
        wallet_address: Wallet address
        alchemy_network: Alchemy network identifier (e.g.: eth-mainnet, arb-mainnet)
        
    Returns:
        Token data dictionary or None if failed
    """
    try:
        # Get API key
        api_key = _get_api_key_for_network(alchemy_network)
        if not api_key:
            logger.error(f"API key not found for network {alchemy_network}")
            return None
        
        # Build API URL
        api_url = f"{ALCHEMY_DATA_API_BASE}/{api_key}/assets/tokens/by-address"
        
        # Build request data
        request_data = {
            "addresses": [
                {
                    "address": wallet_address,
                    "networks": [alchemy_network]
                }
            ],
            "withMetadata": True,
            "withPrices": True,
            "includeNativeTokens": True,
            "includeErc20Tokens": True
        }
        
        # Send POST request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                json=request_data,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as api_response:
                
                if api_response.status != 200:
                    error_text = await api_response.text()
                    logger.error(f"Alchemy API error: {api_response.status} - {error_text}")
                    return None
                
                result = await api_response.json()
                
                # Check response structure
                if "data" not in result:
                    logger.error(f"Invalid Alchemy API response format: {result}")
                    return None
                
                return result["data"]
                
    except asyncio.TimeoutError:
        logger.error(f"Alchemy API timeout - Wallet: {wallet_address}, Network: {alchemy_network}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"HTTP client error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error when calling Alchemy API: {e}")
        return None


def get_supported_networks() -> Dict[str, str]:
    """
    Get list of supported networks
    
    Returns:
        Mapping of network names to Alchemy network identifiers
    """
    return NETWORK_MAPPING.copy()

