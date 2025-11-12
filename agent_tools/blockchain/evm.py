import asyncio
from enum import IntEnum
import logging
import os
import time
from typing import Tuple, Optional, Dict, Any

from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

# Import POA middleware with version compatibility
try:
    # For web3.py >= 7.0.0
    from web3.middleware import ExtraDataToPOAMiddleware
    POA_MIDDLEWARE = ExtraDataToPOAMiddleware
except ImportError:
    try:
        # For web3.py < 7.0.0
        from web3.middleware import geth_poa_middleware
        POA_MIDDLEWARE = geth_poa_middleware
    except ImportError:
        POA_MIDDLEWARE = None

# Alchemy API configuration
ALCHEMY_API_URLS = {
    "ethereum": {
        "mainnet": "https://eth-mainnet.g.alchemy.com/v2",
        "testnet": "https://eth-goerli.g.alchemy.com/v2"
    },
    "arbitrum": {
        "mainnet": "https://arb-mainnet.g.alchemy.com/v2", 
        "testnet": "https://arb-goerli.g.alchemy.com/v2"
    },
    "base": {
        "mainnet": "https://base-mainnet.g.alchemy.com/v2",
        "testnet": "https://base-goerli.g.alchemy.com/v2"
    },
    "bnb": {
        "mainnet": "https://bnb-mainnet.g.alchemy.com/v2",
        "testnet": "https://data-seed-prebsc-1-s1.binance.org:8545/"
    }
}

ALCHEMY_API_KEYS = {
    "ethereum": os.environ.get("ALCHEMY_ETH_API_KEY"),
    "arbitrum": os.environ.get("ALCHEMY_ARB_API_KEY"),
    "base": os.environ.get("ALCHEMY_BASE_API_KEY"),
    "bnb": os.environ.get("ALCHEMY_BNB_API_KEY")  # BNB Alchemy API key
}

# Decimal places for different EVM tokens
ETH_WEI = 10**18  # 18 decimal places for ETH
USDC_DECIMAL = 10**6  # 6 decimal places for USDC
USDT_DECIMAL = 10**6  # 6 decimal places for USDT
BNB_WEI = 10**18  # 18 decimal places for BNB
BUSD_DECIMAL = 10**18  # 18 decimal places for BUSD

# RPC URLs for different networks
ETH_RPC_URLS = {
    "mainnet": f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEYS['ethereum']}",
    "testnet": "https://eth-goerli.g.alchemy.com/v2/YOUR_API_KEY"
}

ARBITRUM_RPC_URLS = {
    "mainnet": f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEYS['arbitrum']}", 
    "testnet": "https://arb-goerli.g.alchemy.com/v2/YOUR_API_KEY"
}

BASE_RPC_URLS = {
    "mainnet": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEYS['base']}",
    "testnet": "https://base-goerli.g.alchemy.com/v2/YOUR_API_KEY"
}

BNB_RPC_URLS = {
    "mainnet": f"https://bnb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEYS['bnb']}",
    "testnet": "https://data-seed-prebsc-1-s1.binance.org:8545/"
}

# Chain IDs
CHAIN_IDS = {
    "ethereum": 1,
    "arbitrum": 42161,
    "base": 8453,
    "bnb": 56,
    "ethereum_testnet": 5,  # Goerli
    "arbitrum_testnet": 421613,  # Arbitrum Goerli
    "base_testnet": 84531,  # Base Goerli
    "bnb_testnet": 97  # BSC Testnet
}

# Contract addresses for common tokens
TOKEN_ADDRESSES = {
    "ethereum": {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    },
    "arbitrum": {
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC on Arbitrum
        "USDC.e": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",  # Bridged USDC (USDC.e)
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
    },
    "base": {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
    },
    "bnb": {
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
    }
}

# Gas limits for different operations
# Arbitrum requires higher gas limits due to L2 overhead
GAS_LIMITS = {
    "eth_transfer": 21000,
    "token_transfer": 65000,
    "contract_call": 100000,
    "arbitrum_token_transfer": 200000,  # Higher limit for Arbitrum
    "arbitrum_eth_transfer": 50000,     # Higher limit for Arbitrum ETH transfers
    "base_token_transfer": 150000,      # Higher limit for Base
    "base_eth_transfer": 40000,         # Higher limit for Base ETH transfers
    "bnb_token_transfer": 100000,        # Standard limit for BNB BEP-20 transfers
    "bnb_transfer": 21000               # Standard limit for BNB transfers
}

# Block confirmation requirements
CONFIRMATION_BLOCKS = {
    "ethereum": 12,
    "arbitrum": 10,
    "base": 10,
    "bnb": 15
}

MAX_RETRIES = 5
COOLDOWN = 10  # seconds


class Blockchain(IntEnum):
    NONE = 0
    CHIA = 1
    SOLANA = 2
    ARBITRUM = 3
    BASE = 4
    ETHEREUM = 5
    EVM = 6
    BNB = 7


class EVMClient:
    """
    EVM blockchain client that supports Ethereum, Arbitrum, Base, and BNB Smart Chain
    
    Simplified version that only supports send_token_with_memo functionality.
    """
    
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        logger.info(f"Initializing EVM client for {blockchain.name}")
        self.w3 = self._get_web3_client()
        self.chain_id = self._get_chain_id()
        
        # Alchemy configuration
        self.alchemy_url, self.alchemy_api_key = self._get_alchemy_config()
        
        # Cache for gas pricing to reduce API calls
        self._gas_price_cache = None
        self._gas_price_cache_time = 0
        self._gas_cache_timeout = 15  # Cache gas prices for 15 seconds
        
        logger.info(f"EVM client initialized for {blockchain.name}, chain ID: {self.chain_id}")
        
    def _get_web3_client(self) -> Web3:
        network = "mainnet" 
        
        if self.blockchain == Blockchain.ETHEREUM:
            rpc_url = ETH_RPC_URLS[network]
        elif self.blockchain == Blockchain.ARBITRUM:
            rpc_url = ARBITRUM_RPC_URLS[network]
        elif self.blockchain == Blockchain.BASE:
            rpc_url = BASE_RPC_URLS[network]
        elif self.blockchain == Blockchain.BNB:
            rpc_url = BNB_RPC_URLS[network]
        else:
            logger.error(f"Unsupported blockchain: {self.blockchain}")
            raise ValueError(f"Unsupported blockchain: {self.blockchain}")
        
        logger.info(f"Connecting to {self.blockchain.name} via RPC")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Add POA middleware for BNB Smart Chain (which is a POA chain)
        if self.blockchain == Blockchain.BNB and POA_MIDDLEWARE is not None:
            logger.info("Injecting POA middleware for BNB Smart Chain")
            w3.middleware_onion.inject(POA_MIDDLEWARE(), layer=0)
            
        return w3
    
    def _get_chain_id(self) -> int:
        """Get chain ID for the blockchain"""
        
        if self.blockchain == Blockchain.ETHEREUM:
            return CHAIN_IDS["ethereum"]
        elif self.blockchain == Blockchain.ARBITRUM:
            return CHAIN_IDS["arbitrum"]
        elif self.blockchain == Blockchain.BASE:
            return CHAIN_IDS["base"]
        elif self.blockchain == Blockchain.BNB:
            return CHAIN_IDS["bnb"]
        else:
            raise ValueError(f"Unsupported blockchain: {self.blockchain}")
    
    def _get_blockchain_name(self) -> str:
        """Get blockchain name for token addresses"""
        if self.blockchain == Blockchain.ETHEREUM:
            return "ethereum"
        elif self.blockchain == Blockchain.ARBITRUM:
            return "arbitrum"
        elif self.blockchain == Blockchain.BASE:
            return "base"
        elif self.blockchain == Blockchain.BNB:
            return "bnb"
        else:
            raise ValueError(f"Unsupported blockchain: {self.blockchain}")

    def _get_alchemy_config(self) -> Tuple[str, str]:
        """Get Alchemy API URL and key for the blockchain"""
        blockchain_name = self._get_blockchain_name()
        is_mainnet = True
        network = "mainnet" if is_mainnet else "testnet"
        
        api_key = ALCHEMY_API_KEYS[blockchain_name]
        if not api_key:
            logger.error(f"Missing Alchemy API key for {blockchain_name}")
            raise ValueError(f"Missing Alchemy API key for {blockchain_name}")
            
        base_url = ALCHEMY_API_URLS[blockchain_name][network]
        full_url = f"{base_url}/{api_key}"
        
        logger.info(f"Alchemy configured for {blockchain_name} {network}")
        return full_url, api_key

    def _get_raw_transaction(self, signed_txn) -> bytes:
        """
        Get raw transaction bytes, compatible across Web3.py versions
        """
        try:
            # Try newer Web3.py attribute (v6.0+)
            return signed_txn.raw_transaction
        except AttributeError:
            try:
                # Fall back to older attribute (v5.x)
                return signed_txn.rawTransaction
            except AttributeError:
                # Ultimate fallback - check if it's already bytes
                if isinstance(signed_txn, bytes):
                    return signed_txn
                
                # Log available attributes for debugging
                attrs = [attr for attr in dir(signed_txn) if not attr.startswith('_')]
                logger.error(f"Cannot extract raw transaction. Available attributes: {attrs}")
                raise ValueError(f"Cannot extract raw transaction from signed transaction object. Available attributes: {attrs}")

    async def get_gas_pricing_data(self) -> dict:
        """Get gas pricing data with caching to reduce API calls"""
        current_time = time.time()
        
        # Return cached value if still valid
        if (self._gas_price_cache is not None and 
            current_time - self._gas_price_cache_time < self._gas_cache_timeout):
            logger.debug("Using cached gas pricing data")
            return self._gas_price_cache
        
        # Fetch new gas pricing data
        for attempt in range(MAX_RETRIES):
            try:
                # Get all gas-related data in one batch to minimize API calls
                latest_block = self.w3.eth.get_block('latest')
                base_fee = latest_block.baseFeePerGas if hasattr(latest_block, 'baseFeePerGas') else None
                
                gas_data = {
                    'latest_block': latest_block,
                    'block_number': latest_block.number,
                    'base_fee': base_fee,
                    'use_eip1559': base_fee is not None,
                    'timestamp': current_time
                }
                
                if base_fee is not None:
                    # EIP-1559 network
                    priority_fee = self.w3.eth.max_priority_fee
                    gas_data.update({
                        'priority_fee': priority_fee,
                        'max_fee_per_gas': base_fee * 2 + priority_fee,
                        'max_priority_fee_per_gas': priority_fee
                    })
                else:
                    # Legacy network
                    gas_price = self.w3.eth.gas_price
                    gas_data.update({
                        'gas_price': gas_price
                    })
                
                # Update cache
                self._gas_price_cache = gas_data
                self._gas_price_cache_time = current_time
                
                logger.info(f"Gas pricing data fetched: block {gas_data['block_number']}, EIP-1559: {gas_data['use_eip1559']}")
                return gas_data
                
            except Exception as e:
                logger.warning(f"Gas pricing data fetch attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(COOLDOWN)
                else:
                    logger.error(f"Failed to fetch gas pricing data after {MAX_RETRIES} attempts")
                    raise

    async def get_account_data(self, address: str) -> dict:
        """Get account nonce and balance in a single optimized call"""
        try:
            # Use batch requests to get both nonce and balance in one call
            # Use "pending" to include pending transactions and avoid nonce collisions
            nonce = self.w3.eth.get_transaction_count(address, "pending")
            balance = self.w3.eth.get_balance(address)
            
            logger.info(f"Account data fetched for {address[:10]}...: nonce={nonce}, balance={balance/ETH_WEI:.6f} {self.blockchain.name}")
            return {
                'nonce': nonce,
                'balance': balance,
                'address': address
            }
        except Exception as e:
            logger.error(f"Failed to get account data for {address}: {e}")
            raise

    def _sign_transaction(
        self, 
        transaction: Dict[str, Any], 
        private_key: Optional[str] = None
    ) -> bytes:
        """
        Sign a transaction using either local private key or signing service
        
        Args:
            transaction: Transaction dictionary
            private_key: Optional private key for local signing
            
        Returns:
            bytes: Raw transaction bytes ready for sending
            
        Raises:
            ValueError: If signing fails
        """
        if private_key:
            # Local signing with Web3
            from eth_account import Account
            
            # Create account from private key
            if private_key.startswith('0x'):
                private_key_clean = private_key[2:]
            else:
                private_key_clean = private_key
            
            account = Account.from_key(private_key_clean)
            
            # Verify the address matches
            if account.address.lower() != transaction['from'].lower():
                logger.error(f"Address mismatch: {account.address} != {transaction['from']}")
                raise ValueError(f"Private key address {account.address} does not match transaction sender {transaction['from']}")
            
            # Sign the complete transaction
            logger.info(f"Signing transaction for {account.address[:10]}...")
            signed_txn_obj = account.sign_transaction(transaction)
            
            return self._get_raw_transaction(signed_txn_obj)

    async def get_token_balance(
        self,
        wallet_address: str,
        token_address: str
    ) -> int:
        """
        Get the balance of an ERC-20 token for a given wallet address.
        
        Args:
            wallet_address: Wallet address to check balance for
            token_address: Token contract address
            
        Returns:
            Token balance in smallest unit (e.g., for USDC with 6 decimals, 
            balance of 1 USDC would be returned as 1000000)
            
        Raises:
            ValueError: If addresses are invalid
            Exception: If balance query fails
        """
        try:
            # Convert addresses to checksum format
            wallet_address = self.w3.to_checksum_address(wallet_address)
            token_address = self.w3.to_checksum_address(token_address)
            
            # Standard ERC-20 ABI for balanceOf function
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            
            # Create contract instance
            contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            
            # Call balanceOf function
            balance = contract.functions.balanceOf(wallet_address).call()
            
            logger.info(f"Token balance fetched for {wallet_address[:10]}...: {balance}")
            return balance
            
        except Exception as e:
            error_msg = f"Error getting token balance for {wallet_address} on {self.blockchain.name}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def send_token_with_memo(
        self,
        token_address: str,
        recipient_address: str,
        amount: int,
        memo_text: str,
        private_key: str
    ) -> str:
        """
        Send ERC-20 tokens with memo.
        
        Args:
            token_address: Token contract address
            recipient_address: Recipient's address
            amount: Amount of tokens (in smallest unit)
            memo_text: Text to include as memo
            private_key: Private key for signing
            
        Returns:
            Transaction hash
        """
        try:
            logger.info(f"Starting token transfer with memo on {self.blockchain.name}")
            account = Account.from_key(private_key)
            
            # Convert recipient address to checksum format
            recipient_address = self.w3.to_checksum_address(recipient_address)
            logger.info(f"Sending {amount} tokens to {recipient_address[:10]}... with memo: {memo_text[:50]}...")
            
            # Get account data and gas pricing in optimized batch calls
            account_data = await self.get_account_data(account.address)
            gas_data = await self.get_gas_pricing_data()
            
            # Use cached data instead of multiple API calls
            nonce = account_data['nonce']
            balance = account_data['balance']
            
            # Check account balance for gas fees
            if balance == 0 and self.blockchain != Blockchain.BNB:
                logger.error(f"Insufficient balance for gas fees: {balance}")
                raise ValueError(f"Insufficient ETH balance for gas fees: {balance}")
            
            # Standard ERC-20 ABI for transfer function
            erc20_abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ]
            
            # Create contract instance
            contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            
            # Build the transfer transaction
            transaction = contract.functions.transfer(recipient_address, amount).build_transaction({
                'chainId': self.chain_id,
                'from': account.address,
                'nonce': nonce
            })
            
            # Encode memo data and append to transaction data
            memo_data = memo_text.encode('utf-8')
            memo_encoded = memo_data.hex()
            
            # Append memo as additional data after the standard transfer call
            transaction['data'] = transaction['data'].hex() + memo_encoded if isinstance(transaction['data'], bytes) else transaction['data'] + memo_encoded
            
            # Estimate gas dynamically for token transfer with memo
            try:
                estimated_gas = self.w3.eth.estimate_gas(transaction)
                # Add buffer based on blockchain type - L2s need higher buffers due to complexity
                if self.blockchain == Blockchain.ARBITRUM:
                    gas_limit = int(estimated_gas * 1.4)  # 40% buffer for Arbitrum
                elif self.blockchain == Blockchain.BASE:
                    gas_limit = int(estimated_gas * 1.35)  # 35% buffer for Base
                elif self.blockchain == Blockchain.BNB:
                    gas_limit = int(estimated_gas * 1.2)  # 20% buffer for BNB
                else:
                    gas_limit = int(estimated_gas * 1.25)  # 25% buffer for Ethereum
                logger.info(f"Gas estimated: {estimated_gas}, using limit: {gas_limit}")
            except Exception as e:
                # Fallback to minimum safe gas limits for L2s and mainnet
                gas_limit = 150000 if self.blockchain in [Blockchain.ARBITRUM, Blockchain.BASE] else 100000
                logger.warning(f"Gas estimation failed, using fallback limit: {gas_limit}. Error: {e}")
            
            transaction['gas'] = gas_limit
            
            # Add gas pricing based on EIP-1559 support
            if gas_data['use_eip1559']:
                transaction['maxFeePerGas'] = gas_data['max_fee_per_gas']
                transaction['maxPriorityFeePerGas'] = gas_data['max_priority_fee_per_gas']
                transaction['type'] = 2  # EIP-1559 transaction type
                if 'gasPrice' in transaction:
                    del transaction['gasPrice']  # Remove gasPrice for EIP-1559
            else:
                transaction['gasPrice'] = gas_data['gas_price']
            
            # Sign and send transaction using simplified method
            signed_tx_bytes = self._sign_transaction(transaction, private_key)
            logger.info("Transaction signed, sending to network...")
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx_bytes)
            
            blockchain_name = self.blockchain.name
            tx_hash_hex = tx_hash.hex()
            logger.info(f"Transaction sent successfully on {blockchain_name}: {tx_hash_hex}")
            return tx_hash_hex
            
        except Exception as e:
            error_msg = f"Error sending token transaction with memo: {e}"
            logger.error(error_msg)
            
            # Provide specific guidance based on error type
            error_str = str(e).lower()
            if "execution reverted" in error_str:
                additional_info = " The contract may not support memo data or there may be insufficient gas."
            elif "gas" in error_str:
                additional_info = " Try increasing the gas limit for L2 networks."
            elif "insufficient funds" in error_str:
                gas_currency = "BNB" if self.blockchain == Blockchain.BNB else "ETH"
                additional_info = f" Check token balance and {gas_currency} for gas fees."
            else:
                additional_info = ""
            
            logger.error(f"Transaction failed: {error_str}{additional_info}")
            raise Exception(f"{error_msg}.{additional_info} Memo is required for this transaction.")


# Global client instances
logger.info("Initializing global EVM client instances")
ETHEREUM_CLIENT = EVMClient(Blockchain.ETHEREUM)
ARBITRUM_CLIENT = EVMClient(Blockchain.ARBITRUM)
BASE_CLIENT = EVMClient(Blockchain.BASE)
BNB_CLIENT = EVMClient(Blockchain.BNB)
logger.info("All EVM client instances initialized successfully")
